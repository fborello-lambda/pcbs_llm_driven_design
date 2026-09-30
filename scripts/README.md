# Automation

Run these tools from the repository root after creating the uv environment documented in the main README.

| Path | Purpose |
| --- | --- |
| `check_all.py` | Read-only ERC, DRC, shared footprint, and shared model validation for all boards |
| `kicad_helpers.py` | Shared KiCad S-expression helpers used by the project generators |
| `export_publishable_docs.py` | Regenerates the four committed 3D previews and schematic PDFs |
| `export_fabrication.py` | Creates deterministic release-ready Gerber/drill ZIPs under ignored `outputs/` directories |
| `grid_router.py` | Shared routing primitives loaded by each board-specific router |
| `dimmer/` | Dimmer generation, routing, BOM, artwork, and finishing tools |
| `remote_controller/` | Remote-control generation, routing, artwork, and finishing tools |
| `photodiode_lab/` | TIA laboratory generation, routing, theory artwork, and finishing tools |

The generators and routers modify KiCad source files. Commit or back up intentional manual edits before rebuilding a project. `check_all.py` is safe to run without modifying the projects.

The primary dimmer rebuild sequence is:

```sh
uv run --no-sync python scripts/dimmer/build_design.py
uv run --no-sync python scripts/dimmer/project_settings.py
uv run --no-sync python scripts/dimmer/route_board.py
kicad-cli sch export netlist dimmer/esp32_dimmer.kicad_sch --format kicadxml -o dimmer/outputs/netlist.xml
uv run --no-sync python scripts/dimmer/finish_board.py
uv run --no-sync python scripts/dimmer/refresh_bom.py
```

The remote-control and photodiode-laboratory rebuild sequences are documented in their project READMEs. Run `check_all.py` after any rebuild.
