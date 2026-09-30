"""Export the current (not regenerated) PCB to a fabrication-only ZIP."""
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2] / 'raspberry_spi0_breakout'
BOARD = ROOT / 'raspberry_spi0_breakout.kicad_pcb'
OUT = ROOT / 'outputs'


def main():
    OUT.mkdir(exist_ok=True)
    subprocess.run(['kicad-cli', 'pcb', 'drc', str(BOARD), '-o',
                    str(OUT / 'fabrication-drc.rpt'), '--exit-code-violations'], check=True)
    with tempfile.TemporaryDirectory(prefix='cobbler-gerbers-') as temp:
        subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', str(BOARD),
                        '-o', temp + '/', '--layers',
                        'F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts',
                        '--subtract-soldermask'], check=True)
        subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', str(BOARD),
                        '-o', temp + '/', '--format', 'excellon',
                        '--excellon-units', 'mm', '--excellon-separate-th'], check=True)
        files = sorted(p for p in Path(temp).iterdir()
                       if p.suffix.lower() in {'.gtl', '.gbl', '.gts', '.gbs',
                                              '.gto', '.gbo', '.gm1', '.gbr', '.drl'})
        assert {'.gtl', '.gbl', '.gts', '.gbs', '.gto', '.gm1', '.drl'} <= {p.suffix.lower() for p in files}
        target = OUT / 'raspberry_spi0_30x53_R2_JLCPCB.zip'
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.name)
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
        print(target)


if __name__ == '__main__':
    main()
