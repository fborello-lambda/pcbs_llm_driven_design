#!/usr/bin/env python3
"""Export repository-safe schematic PDFs and 3D README previews."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    ("dimmer", "esp32_dimmer"),
    ("remote_controller", "esp32c3_remote"),
    ("photodiode_lab", "photodiode_lab"),
    ("raspberry_spi0_breakout", "raspberry_spi0_breakout"),
)


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    for directory, stem in PROJECTS:
        project = ROOT / directory
        docs = project / "docs"
        docs.mkdir(exist_ok=True)
        run(
            "kicad-cli",
            "pcb",
            "render",
            str(project / f"{stem}.kicad_pcb"),
            "-o",
            str(docs / "board-3d.png"),
            "--width",
            "1200",
            "--height",
            "800",
            "--background",
            "opaque",
            "--quality",
            "high",
            "--floor",
            "--perspective",
            "--rotate",
            "-35,0,35",
        )
        run(
            "kicad-cli",
            "sch",
            "export",
            "pdf",
            str(project / f"{stem}.kicad_sch"),
            "-o",
            str(docs / "schematic.pdf"),
            "--black-and-white",
            "--exclude-pdf-property-popups",
            "--exclude-pdf-hierarchical-links",
            "--exclude-pdf-metadata",
        )


if __name__ == "__main__":
    main()
