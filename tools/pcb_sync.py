#!/usr/bin/env python3
"""Headless "Update PCB from Schematic" (runs in CI, needs KiCad's pcbnew module).

    pcb_sync.py <netlist.net> <board.kicad_pcb> [--placement placement.toml]

KiCad has no CLI for F8 / Update PCB from Schematic, so this script does the same
job with the pcbnew API:
  - footprints for new symbols are loaded from the project library and placed
    from placement.toml (or parked off-board if not listed);
  - existing footprints keep their position, rotation, side and routing; value,
    footprint fields and the symbol link (KIID path) are refreshed;
  - footprints whose symbol was removed are deleted;
  - every pad gets the net from the netlist.
If the board does not exist yet it is created with the outline from placement.toml
and a GND pour on both layers. Footprint-to-symbol linking uses the symbol UUID,
which tools/schgen.py keeps stable, so this is safe to re-run.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kisexpr as k  # noqa: E402

MM = pcbnew.FromMM


def read_netlist(path: Path):
    t = k.load(path)
    comps, pins = {}, {}
    for c in k.children(k.find(t, "components"), "comp"):
        ref = str(k.find(c, "ref")[1])
        fields = {}
        flds = k.find(c, "fields")
        if flds is not None:
            for f in k.children(flds, "field"):
                name = k.find(f, "name")[1]
                fields[str(name)] = str(f[2]) if len(f) > 2 else ""
        for key in ("datasheet", "description"):
            node = k.find(c, key)
            if node is not None:
                fields[key.capitalize()] = str(node[1])
        fields.pop("Footprint", None)
        comps[ref] = {
            "value": str(k.find(c, "value")[1]),
            "footprint": str(k.find(c, "footprint")[1]),
            "tstamp": str(k.find(c, "tstamps")[1]),
            "fields": fields,
        }
    for n in k.children(k.find(t, "nets"), "net"):
        name = str(k.find(n, "name")[1])
        for node in k.children(n, "node"):
            pins[(str(k.find(node, "ref")[1]), str(k.find(node, "pin")[1]))] = name
    return comps, pins


def new_board(outline):
    board = pcbnew.BOARD()
    x1, y1, x2, y2 = outline
    rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    rect.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    rect.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(MM(0.05))
    board.Add(rect)
    return board


def add_gnd_pours(board, outline):
    gnd = board.FindNet("GND")
    x1, y1, x2, y2 = outline
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName(f"GND_{board.GetLayerName(layer)}")
        z.SetLocalClearance(MM(0.25))
        z.SetMinThickness(MM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
            ol.Append(MM(x), MM(y))
        z.SetAssignedPriority(0)
        board.Add(z)


def load_fp(libdir: Path, fpid: str):
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(str(libdir / f"{lib}.pretty"), name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def set_fields(fp, comp):
    fp.SetValue(comp["value"])
    for key, val in comp["fields"].items():
        if True:
            try:
                fp.SetField(key, val)
                f = fp.GetFieldByName(key)
                if f is not None:  # like KiCad's own update: extra fields are hidden, on F.Fab
                    f.SetVisible(False)
                    f.SetLayer(pcbnew.F_Fab if not fp.IsFlipped() else pcbnew.B_Fab)
            except Exception as e:  # API drift between versions: record, don't die
                print(f"  note: SetField({key}) failed: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("netlist", type=Path)
    ap.add_argument("board", type=Path)
    ap.add_argument("--placement", type=Path)
    ap.add_argument("--lib", type=Path, default=Path(__file__).resolve().parents[1] / "hardware/lib")
    a = ap.parse_args()

    comps, pins = read_netlist(a.netlist)
    place = tomllib.loads(a.placement.read_text()) if a.placement else {"parts": {}, "board": {}}
    created = not a.board.exists()
    board = new_board(place["board"]["outline"]) if created else pcbnew.LoadBoard(str(a.board))

    # nets
    for name in sorted(set(pins.values())):
        if board.FindNet(name) is None:
            board.Add(pcbnew.NETINFO_ITEM(board, name))

    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    added, updated, removed = [], [], []
    park_x = place["board"].get("outline", [0, 0, 0, 0])[2] + 10
    for ref, comp in sorted(comps.items()):
        fp = existing.get(ref)
        if fp is not None and str(fp.GetFPID().Format()) != comp["footprint"]:
            # footprint changed: swap it in place, keep position/orientation/side
            pos, ori, flipped = fp.GetPosition(), fp.GetOrientationDegrees(), fp.IsFlipped()
            board.Remove(fp)
            fp = load_fp(a.lib, comp["footprint"])
            fp.SetPosition(pos)
            fp.SetOrientationDegrees(ori)
            if flipped:
                fp.Flip(pos, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            board.Add(fp)
            updated.append(f"{ref} (footprint)")
        elif fp is None:
            fp = load_fp(a.lib, comp["footprint"])
            x, y, rot = place["parts"].get(ref, [park_x, 100 + 5 * len(added), 0])
            fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            fp.SetOrientationDegrees(rot)
            board.Add(fp)
            added.append(ref)
        fp.SetReference(ref)
        fp.SetPath(pcbnew.KIID_PATH(f"/{comp['tstamp']}"))
        fp.SetSheetname("/")
        fp.SetSheetfile(a.board.with_suffix(".kicad_sch").name)
        set_fields(fp, comp)
        for pad in fp.Pads():
            net = pins.get((ref, pad.GetNumber()))
            pad.SetNet(board.FindNet(net) if net else board.FindNet(""))
            if net is None and pad.GetNumber():
                pad.SetNetCode(0)
    for ref, fp in existing.items():
        if ref not in comps:
            board.Remove(fp)
            removed.append(ref)

    if created:
        add_gnd_pours(board, place["board"]["outline"])
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(a.board), board)
    print(f"{'created' if created else 'synced'} {a.board}: +{len(added)} {added} "
          f"~{len(updated)} {updated} -{len(removed)} {removed}")


if __name__ == "__main__":
    main()
