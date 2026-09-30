#!/usr/bin/env python3
"""Run read-only KiCad checks for every board in the repository."""

from pathlib import Path
import subprocess
import tempfile

import pcbnew


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    ("dimmer", "esp32_dimmer", True),
    ("remote_controller", "esp32c3_remote", True),
    ("photodiode_lab", "photodiode_lab", True),
    ("raspberry_spi0_breakout", "raspberry_spi0_breakout", False),
)


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=REPOSITORY_ROOT, check=True)


def pad_geometry(footprint):
    return sorted(
        (
            pad.GetNumber(),
            pad.GetFPRelativePosition().x,
            pad.GetFPRelativePosition().y,
            pad.GetSize().x,
            pad.GetSize().y,
            pad.GetAttribute(),
        )
        for pad in footprint.Pads()
    )


def main() -> None:
    shared = pcbnew.FootprintLoad(
        str(REPOSITORY_ROOT / "shared/ESP32-C3-SuperMini.pretty"),
        "ESP32-C3-SuperMini",
    )
    expected_model = "${KIPRJMOD}/../shared/3d/ESP32-C3-SuperMini.step"

    with tempfile.TemporaryDirectory(prefix="esp32-c3-kicad-checks-") as output:
        output_dir = Path(output)
        for directory, stem, uses_shared_esp32 in PROJECTS:
            schematic = REPOSITORY_ROOT / directory / f"{stem}.kicad_sch"
            board_path = REPOSITORY_ROOT / directory / f"{stem}.kicad_pcb"
            run("kicad-cli", "sch", "erc", str(schematic), "-o", str(output_dir / f"{directory}-erc.rpt"), "--exit-code-violations")
            run("kicad-cli", "pcb", "drc", str(board_path), "-o", str(output_dir / f"{directory}-drc.rpt"), "--schematic-parity", "--exit-code-violations")

            if uses_shared_esp32:
                board = pcbnew.LoadBoard(str(board_path))
                esp32 = next(fp for fp in board.GetFootprints() if fp.GetReference() == "U1")
                assert pad_geometry(esp32) == pad_geometry(shared), directory
                assert [model.m_Filename for model in esp32.Models()] == [expected_model], directory

    print("All four projects passed ERC, DRC, and schematic parity checks.")
    print("All ESP32 projects also passed shared-footprint and shared-model checks.")


if __name__ == "__main__":
    main()
