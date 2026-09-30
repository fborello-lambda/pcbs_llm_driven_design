"""Shared grid-routing primitives loaded by each board-specific router.

This module expects the caller to define pcbnew as ``p`` plus ``b``, ``S``, ``N``,
``X``, ``Y``, ``fps``, ``nets``, and ``lv`` before executing it.
"""

def pos(v): return (p.ToMM(v.x),p.ToMM(v.y))
def mm(a): return p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1]))
def grid(a): return (round(a[0]/S),round(a[1]/S))
def pad(ref,num): return next(x for x in fps[ref].Pads() if x.GetNumber()==str(num))
def endpoint(ref,num):
    z=pad(ref,num); return (pos(z.GetPosition()),[0] if z.GetAttribute()==p.PAD_ATTRIB_SMD else [0,1])
features=[]
for f in b.GetFootprints():
    for z in f.Pads():
        a=pos(z.GetPosition()); size=pos(z.GetSize()); angle=z.GetOrientationDegrees()%180
        if abs(angle-90)<1: size=size[::-1]
        layers=[0] if z.GetAttribute()==p.PAD_ATTRIB_SMD else [0,1]
        features.append(('rect',z.GetNetname(),layers,a,size))
def segdist(a,c):
    dx=c[0]-a[0]; dy=c[1]-a[1]; ll=dx*dx+dy*dy
    t=np.clip(((X-a[0])*dx+(Y-a[1])*dy)/ll,0,1) if ll else 0
    return (X-(a[0]+t*dx))**2+(Y-(a[1]+t*dy))**2
def track(a,c,net,width,layer):
    if math.dist(a,c)<1e-5: return
    t=p.PCB_TRACK(b); t.SetStart(mm(a)); t.SetEnd(mm(c)); t.SetWidth(p.FromMM(width)); t.SetLayer(p.F_Cu if layer==0 else p.B_Cu); t.SetNet(nets[net]); b.Add(t)
    features.append(('seg',net,[layer],a,c,width))
def via(a,net):
    v=p.PCB_VIA(b); v.SetPosition(mm(a)); v.SetWidth(p.FromMM(.9)); v.SetDrill(p.FromMM(.45)); v.SetViaType(p.VIATYPE_THROUGH); v.SetLayerPair(p.F_Cu,p.B_Cu); v.SetNet(nets[net]); b.Add(v)
    features.append(('rect',net,[0,1],a,(.9,.9)))
def blocks(net,width):
    clear=.3 if net in lv else .8
    # Margin covers discretization and corners. Insulation belt is independent of net assignment.
    margin=width/2+clear+.16
    bad=np.zeros((2,N,N),dtype=bool)
    base=(X<2+width/2)|(X>98-width/2)|(Y<1+width/2)|(Y>98-width/2)|((Y>34-width/2)&(Y<42+width/2))
    base|=(X>43-width/2)&(X<57+width/2)&(Y>21-width/2)&(Y<30+width/2)
    for hx,hy in [(5,5),(95,5),(5,95),(95,95)]: base|=(X-hx)**2+(Y-hy)**2<(3.5+width/2)**2
    for l in [0,1]: bad[l]=base
    for f in features:
        typ,n,ls,a=f[:4]
        if n==net: continue
        margin=width/2+(.3 if net in lv and n in lv else .8)+.16
        if typ=='rect':
            sx,sy=f[4]; dx=np.maximum(np.abs(X-a[0])-sx/2,0); dy=np.maximum(np.abs(Y-a[1])-sy/2,0); mask=dx*dx+dy*dy<margin*margin
        else: mask=segdist(a,f[4])<(margin+f[5]/2)**2
        for l in ls: bad[l]|=mask
    return bad
def route(net,aa,zz,width=.6,vias=True):
    a,al=aa; z,zl=zz; ax,ay=grid(a); zx,zy=grid(z)
    bad=blocks(net,width)
    if not vias:
        common=[l for l in al if l in zl]
        if not common: raise RuntimeError('Incompatible layers')
        al=zl=common
    for l in al:
        if bad[l,ay,ax]: print('Blocked start',net,a,l,flush=True)
    for l in zl:
        if bad[l,zy,zx]: print('Blocked end',net,z,l,flush=True)
    best={}; prev={}; heap=[]
    def heur(x,y):
        dx=abs(x-zx); dy=abs(y-zy); return max(dx,dy)+.4142*min(dx,dy)
    for l in al:
        if not bad[l,ay,ax]: best[(ax,ay,l)]=0; heapq.heappush(heap,(heur(ax,ay),0,ax,ay,l))
    moves=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.4142),(-1,1,1.4142),(1,-1,1.4142),(-1,-1,1.4142)]
    end=None
    while heap:
        _,cost,x,y,l=heapq.heappop(heap); state=x,y,l
        if cost>best[state]+1e-7: continue
        if x==zx and y==zy and l in zl: end=state; break
        opts=[(x+dx,y+dy,l,dd) for dx,dy,dd in moves]
        if vias: opts.append((x,y,1-l,35))
        for nx,ny,nl,dd in opts:
            if nx<0 or ny<0 or nx>=N or ny>=N or bad[nl,ny,nx]: continue
            if nl!=l:
                # Vias need 0.9mm diameter regardless of trace width.
                r=2
                if bad[:,max(0,ny-r):ny+r+1,max(0,nx-r):nx+r+1].any(): continue
            elif nx!=x and ny!=y and (bad[l,y,nx] or bad[l,ny,x]): continue
            ns=nx,ny,nl; nc=cost+dd
            if nc+1e-7<best.get(ns,1e20): best[ns]=nc; prev[ns]=state; heapq.heappush(heap,(nc+heur(nx,ny),nc,nx,ny,nl))
    if end is None: print('FAILED',net,a,z,width,flush=True); return False
    path=[end]
    while path[-1] in prev: path.append(prev[path[-1]])
    path.reverse()
    # Straight 45-degree runs replace equivalent tiny staircases.
    smooth=[path[0]]; i=0
    while i<len(path)-1:
        chosen=i+1
        for j in range(len(path)-1,i+1,-1):
            x0,y0,l0=path[i]; x1,y1,l1=path[j]
            if l0!=l1 or any(v[2]!=l0 for v in path[i:j+1]): continue
            dx=x1-x0; dy=y1-y0
            if dx and dy and abs(dx)!=abs(dy): continue
            steps=max(abs(dx),abs(dy))
            if not steps: continue
            xs=np.rint(np.linspace(x0,x1,steps+1)).astype(int); ys=np.rint(np.linspace(y0,y1,steps+1)).astype(int)
            if bad[l0,ys,xs].any(): continue
            if dx and dy and (bad[l0,ys[:-1],xs[1:]].any() or bad[l0,ys[1:],xs[:-1]].any()): continue
            chosen=j; break
        smooth.append(path[chosen]); i=chosen
    path=smooth
    # Collapse runs in the same direction to keep the PCB editable.
    points=[path[0]]
    for i in range(1,len(path)-1):
        prevdir=tuple(path[i][j]-path[i-1][j] for j in range(3)); nextdir=tuple(path[i+1][j]-path[i][j] for j in range(3))
        if (prevdir[2]!=0 or nextdir[2]!=0 or prevdir[0]*nextdir[1]!=prevdir[1]*nextdir[0] or prevdir[0]*nextdir[0]+prevdir[1]*nextdir[1]<=0): points.append(path[i])
    points.append(path[-1])
    track(a,(points[0][0]*S,points[0][1]*S),net,width,points[0][2])
    for v,w in zip(points,points[1:]):
        pa=(v[0]*S,v[1]*S); pz=(w[0]*S,w[1]*S)
        if v[2]!=w[2]: via(pa,net)
        else: track(pa,pz,net,width,v[2])
    track((points[-1][0]*S,points[-1][1]*S),z,net,width,points[-1][2])
    print('OK',net,a,z,width,'segments',len(points),flush=True); return True
