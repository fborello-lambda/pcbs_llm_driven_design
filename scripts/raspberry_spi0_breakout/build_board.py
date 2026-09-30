#!/usr/bin/env python3
"""Generate the compact Raspberry Pi GPIO-to-SPI0 adapter PCB."""
from pathlib import Path
import copy
import csv
import importlib.util
import json
import math
import uuid
import pcbnew as p


ROOT = Path(__file__).resolve().parents[2] / "raspberry_spi0_breakout"
HELPERS_SPEC = importlib.util.spec_from_file_location(
    "kicad_helpers", ROOT.parent / "scripts/kicad_helpers.py"
)
HELPERS = importlib.util.module_from_spec(HELPERS_SPEC)
HELPERS_SPEC.loader.exec_module(HELPERS)
get, kids, dump, quote = HELPERS.get, HELPERS.kids, HELPERS.dump, HELPERS.q


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"raspberry-spi0-breakout-v1/{name}"))


PARTS = (
    {
        "ref": "J1",
        "lib": "Connector_Generic:Conn_02x20_Odd_Even",
        "value": "Raspberry Pi GPIO extender (2x20)",
        "footprint": "Breakout:T_Cobbler_2x20_P2.54_W15.24",
        "nets": {
            "19": "SPI0_MOSI_GPIO10",
            "21": "SPI0_MISO_GPIO9",
            "23": "SPI0_SCLK_GPIO11",
            "24": "SPI0_CE0_GPIO8",
            "25": "GND",
        },
        "position": (76.2, 88.9),
        "notes": "Receiving footprint for a 40-pin T-Cobbler-style extender; verify 15.24 mm row spacing before fabrication.",
    },
    {
        "ref": "J2",
        "lib": "Connector_Generic:Conn_01x05",
        "value": "SPI0 OUTPUT",
        "footprint": "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
        "nets": {
            "1": "SPI0_MOSI_GPIO10",
            "2": "SPI0_MISO_GPIO9",
            "3": "SPI0_SCLK_GPIO11",
            "4": "SPI0_CE0_GPIO8",
            "5": "GND",
        },
        "position": (152.4, 88.9),
        "notes": "Top-to-bottom SPI0 output: MOSI, MISO, SCLK, CE0, GND.",
    },
)


def mm(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def add_text(board, text, x, y, size=0.9):
    item = p.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(mm(x, y))
    item.SetTextSize(mm(size, size))
    item.SetTextThickness(p.FromMM(0.14))
    item.SetLayer(p.F_SilkS)
    board.Add(item)


def add_line(board, a, b):
    item = p.PCB_SHAPE()
    item.SetShape(p.SHAPE_T_SEGMENT)
    item.SetStart(mm(*a))
    item.SetEnd(mm(*b))
    item.SetLayer(p.Edge_Cuts)
    item.SetWidth(p.FromMM(0.05))
    board.Add(item)


def track(board, net, points, layer):
    for start, end in zip(points, points[1:]):
        item = p.PCB_TRACK(board)
        item.SetStart(mm(*start))
        item.SetEnd(mm(*end))
        item.SetWidth(p.FromMM(0.30))
        item.SetLayer(layer)
        item.SetNet(net)
        board.Add(item)


def generate_schematic():
    symbols = {}
    for part in PARTS:
        library, name = part["lib"].split(":")
        symbols[part["lib"]] = HELPERS.resolve(library, name)

    sheet_uuid = uid("sheet")
    embedded = []
    for library_id, symbol in symbols.items():
        item = copy.deepcopy(symbol)
        item[1] = library_id
        embedded.append(dump(item))

    output = [
        f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {sheet_uuid}) (paper "A4")',
        '(title_block (title "RASPBERRY PI SPI0 BREAKOUT") (rev "1"))',
        '(lib_symbols ' + " ".join(embedded) + ')',
    ]

    def label(net, x, y, justify_right=False):
        justify = "right bottom" if justify_right else "left bottom"
        output.append(
            f'(label {quote(net)} (at {x} {y} 0) '
            f'(effects (font (size 1 1)) (justify {justify})) '
            f'(uuid {uid(f"{net}-{x}-{y}")}))'
        )

    for part in PARTS:
        x, y = part["position"]
        symbol = symbols[part["lib"]]
        pins = [pin for sub in kids(symbol, "symbol") for pin in kids(sub, "pin")]
        output.append(
            f'(symbol (lib_id {quote(part["lib"])}) (at {x} {y} 0) (unit 1) '
            f'(in_bom yes) (on_board yes) (dnp no) (uuid {uid(part["ref"])})'
        )
        for name, value, dy, hidden in (
            ("Reference", part["ref"], -31, False),
            ("Value", part["value"], -28, False),
            ("Footprint", part["footprint"], 0, True),
        ):
            hide = " (hide yes)" if hidden else ""
            output.append(
                f'(property {quote(name)} {quote(value)} (at {x} {y + dy} 0) '
                f'(effects (font (size 1 1)){hide}))'
            )
        for pin in pins:
            number = get(pin, "number")[1]
            output.append(f'(pin {quote(number)} (uuid {uid(part["ref"] + number)}))')
        output.append(
            f'(instances (project "raspberry_spi0_breakout" '
            f'(path "/{sheet_uuid}" (reference {quote(part["ref"])}) (unit 1)))))'
        )
        for pin in pins:
            number = get(pin, "number")[1]
            px, py, angle = map(float, get(pin, "at")[1:])
            pin_x, pin_y = round(x + px, 5), round(y - py, 5)
            net = part["nets"].get(number)
            if net is None:
                output.append(
                    f'(no_connect (at {pin_x} {pin_y}) '
                    f'(uuid {uid(part["ref"] + number + "-nc")}))'
                )
                continue
            radians = math.radians(angle)
            end_x = round(pin_x - 5.08 * math.cos(radians), 5)
            end_y = round(pin_y + 5.08 * math.sin(radians), 5)
            output.append(
                f'(wire (pts (xy {pin_x} {pin_y}) (xy {end_x} {end_y})) '
                f'(stroke (width .254) (type default)) '
                f'(uuid {uid(part["ref"] + number + "-wire")}))'
            )
            label(net, end_x, end_y, angle == 0)

    output.append(
        f'(text "Only SPI0 and GND are routed. All other 40-pin header contacts are intentionally isolated." '
        f'(at 55.88 30.48 0) (effects (font (size 1.2 1.2)) (justify left)) '
        f'(uuid {uid("schematic-note")}))'
    )
    output.append('(embedded_fonts no))')
    (ROOT / "raspberry_spi0_breakout.kicad_sch").write_text("\n".join(output) + "\n")

    library_dir = ROOT / "libraries"
    library_dir.mkdir(exist_ok=True)
    library_symbols = []
    for library_id, symbol in symbols.items():
        item = copy.deepcopy(symbol)
        item[1] = library_id.split(":", 1)[1]
        library_symbols.append(dump(item))
    (library_dir / "Connector_Generic.kicad_sym").write_text(
        '(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '
        + " ".join(library_symbols)
        + ')\n'
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table (version 7) '
        '(lib (name "Connector_Generic") (type "KiCad") '
        '(uri "${KIPRJMOD}/libraries/Connector_Generic.kicad_sym") '
        '(options "") (descr "Project connector symbols")))\n'
    )


def generate_bom():
    with (ROOT / "BOM.csv").open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("Reference", "Value", "Footprint", "Notes"))
        for part in PARTS:
            writer.writerow(
                (part["ref"], part["value"], part["footprint"], part["notes"])
            )


def main():
    ROOT.mkdir(exist_ok=True)
    generate_schematic()
    generate_bom()
    board = p.BOARD()
    board.SetCopperLayerCount(2)
    nets = {}
    for name in ("SPI0_MOSI_GPIO10", "SPI0_MISO_GPIO9", "SPI0_SCLK_GPIO11", "SPI0_CE0_GPIO8", "GND"):
        net = p.NETINFO_ITEM(board, "/" + name)
        board.Add(net)
        nets[name] = net
    unused_gpio_nets = {}
    for number in range(1, 41):
        if str(number) in PARTS[0]["nets"]:
            continue
        name = f"unconnected-(J1-Pin_{number}-Pad{number})"
        net = p.NETINFO_ITEM(board, name)
        board.Add(net)
        unused_gpio_nets[str(number)] = net

    gpio = p.FOOTPRINT(board)
    gpio.SetFPID(p.LIB_ID("Breakout", "T_Cobbler_2x20_P2.54_W15.24"))
    for row in range(20):
        for col in range(2):
            pad = p.PAD(gpio)
            pad.SetNumber(str(2 * row + col + 1))
            pad.SetAttribute(p.PAD_ATTRIB_PTH)
            pad.SetShape(p.PAD_SHAPE_RECT if row == col == 0 else p.PAD_SHAPE_CIRCLE)
            pad.SetSize(mm(1.7, 1.7))
            pad.SetDrillSize(mm(1, 1))
            pad.SetLayerSet(p.PAD.PTHMask())
            pad.SetPosition(mm(col * 15.24, row * 2.54))
            gpio.Add(pad)
    gpio.SetReference("J1")
    gpio.SetValue("Raspberry Pi GPIO extender (2x20)")
    gpio.SetPath(p.KIID_PATH('/' + uid('sheet') + '/' + uid('J1')))
    # Receiving footprint, top view: odd pins left, even pins right.
    lib = ROOT / "libraries/Breakout.pretty"
    lib.mkdir(parents=True, exist_ok=True)
    p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(lib), gpio)
    (ROOT / "fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "Breakout") (type "KiCad") (uri "${KIPRJMOD}/libraries/Breakout.pretty") (options "") (descr "T-Cobbler receiving footprint")))\n')
    gpio.SetPosition(mm(12, 2.5))
    board.Add(gpio)

    out = p.FootprintLoad(
        "/usr/share/kicad/footprints/Connector_PinHeader_2.54mm.pretty",
        "PinHeader_1x05_P2.54mm_Vertical",
    )
    out.SetReference("J2")
    out.SetValue("SPI0 OUTPUT")
    out.SetFPID(p.LIB_ID("Connector_PinHeader_2.54mm", "PinHeader_1x05_P2.54mm_Vertical"))
    out.SetPath(p.KIID_PATH('/' + uid('sheet') + '/' + uid('J2')))
    out.SetPosition(mm(3, 25.36))
    out.SetOrientationDegrees(0)
    board.Add(out)

    # Pins are the group printed on the pictured extender: 19/MOSI, 21/MISO,
    # 23/SCLK, 24/CE0 and the adjacent 25/GND.
    gpio_nets = {"19": "SPI0_MOSI_GPIO10", "21": "SPI0_MISO_GPIO9", "23": "SPI0_SCLK_GPIO11", "24": "SPI0_CE0_GPIO8", "25": "GND"}
    output_nets = {"1": "SPI0_MOSI_GPIO10", "2": "SPI0_MISO_GPIO9", "3": "SPI0_SCLK_GPIO11", "4": "SPI0_CE0_GPIO8", "5": "GND"}
    for pad in gpio.Pads():
        if pad.GetNumber() in gpio_nets:
            pad.SetNet(nets[gpio_nets[pad.GetNumber()]])
        else:
            pad.SetNet(unused_gpio_nets[pad.GetNumber()])
    for pad in out.Pads():
        pad.SetNet(nets[output_nets[pad.GetNumber()]])

    # CE0 crosses between rows on B.Cu; other signals fan out on F.Cu.
    for net, y in [("SPI0_MOSI_GPIO10",25.36),("SPI0_MISO_GPIO9",27.9),("SPI0_SCLK_GPIO11",30.44)]:
        track(board, nets[net], [(12,y),(3,y)], p.F_Cu)
    track(board, nets["SPI0_CE0_GPIO8"], [(27.24,30.44),(25.97,31.71),(7,31.71),(5.73,32.98),(3,32.98)], p.B_Cu)
    track(board, nets["GND"], [(12,32.98),(9.46,35.52),(3,35.52)], p.F_Cu)

    # 30 x 53 mm outline with four tangent R2 corners.
    for a, b in [((2, 0), (28, 0)), ((30, 2), (30, 51)), ((28, 53), (2, 53)), ((0, 51), (0, 2))]:
        add_line(board, a, b)
    offset = 2 / math.sqrt(2)
    for start, mid, end in [
        ((28, 0), (28 + offset, 2 - offset), (30, 2)),
        ((30, 51), (28 + offset, 51 + offset), (28, 53)),
        ((2, 53), (2 - offset, 51 + offset), (0, 51)),
        ((0, 2), (2 - offset, 2 - offset), (2, 0)),
    ]:
        arc = p.PCB_SHAPE()
        arc.SetShape(p.SHAPE_T_ARC)
        arc.SetArcGeometry(mm(*start), mm(*mid), mm(*end))
        arc.SetLayer(p.Edge_Cuts)
        arc.SetWidth(p.FromMM(0.05))
        board.Add(arc)
    add_text(board, "T-COBBLER", 19.5, 6, 1)
    add_text(board, "15.24 mm", 19.5, 9, 1)
    add_text(board, "SPI0", 5, 22.5, 1)
    for label, y in [("MOSI",25.36),("MISO",27.9),("SCLK",30.44),("CE0",32.98),("GND",35.52)]:
        add_text(board, label, 7, y, 0.8)
    add_text(board, "1", 14.5, 2.5, 0.8)
    add_text(board, "2", 24.7, 2.5, 0.8)
    gpio.Reference().SetVisible(False)
    gpio.Value().SetVisible(False)
    out.Reference().SetVisible(False)
    out.Value().SetVisible(False)

    p.SaveBoard(str(ROOT / "raspberry_spi0_breakout.kicad_pcb"), board)
    project = {"board": {"design_settings": {"rules": {"min_clearance": 0.2, "min_track_width": 0.2, "min_copper_edge_clearance": 0.5, "min_hole_clearance": 0.25, "min_silk_clearance": 0.1, "min_silk_text_height": 0.8, "min_silk_text_thickness": 0.1}}}, "meta": {"filename": "raspberry_spi0_breakout.kicad_pro", "version": 1}}
    (ROOT / "raspberry_spi0_breakout.kicad_pro").write_text(json.dumps(project, indent=2) + "\n")


if __name__ == "__main__":
    main()
