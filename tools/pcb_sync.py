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
(rectangle or rounded card), GND pours and silkscreen texts. Footprint-to-symbol linking uses the symbol UUID,
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
    comps, pins, pinfo = {}, {}, {}
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
            key = (str(k.find(node, "ref")[1]), str(k.find(node, "pin")[1]))
            pins[key] = name
            fn = k.find(node, "pinfunction")
            fn = str(fn[1]) if fn else ""
            if fn.endswith("_" + key[1]):  # KiCad 10 netlists write NAME_NUMBER
                fn = fn[: -len(key[1]) - 1]
            ty = k.find(node, "pintype")
            pinfo[key] = (fn, str(ty[1]) if ty else "")
    return comps, pins, pinfo


def outline_of(bcfg: dict) -> tuple[float, float, float, float, float]:
    """[board] either `outline = [x1, y1, x2, y2]` or `origin` + `width`/`height`
    (+ optional `corner_radius`)."""
    if "outline" in bcfg:
        x1, y1, x2, y2 = bcfg["outline"]
    else:
        x1, y1 = bcfg["origin"]
        x2, y2 = x1 + bcfg["width"], y1 + bcfg["height"]
    return x1, y1, x2, y2, float(bcfg.get("corner_radius", 0))


def _edge(board, shape):
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(MM(0.05))
    board.Add(shape)


def new_board(bcfg: dict):
    board = pcbnew.BOARD()
    x1, y1, x2, y2, r = outline_of(bcfg)
    if r <= 0:
        rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
        rect.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        rect.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        _edge(board, rect)
        return board
    P = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))  # noqa: E731
    for (ax, ay), (bx, by) in (((x1 + r, y1), (x2 - r, y1)), ((x2, y1 + r), (x2, y2 - r)),
                               ((x2 - r, y2), (x1 + r, y2)), ((x1, y2 - r), (x1, y1 + r))):
        seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(P(ax, ay)); seg.SetEnd(P(bx, by))
        _edge(board, seg)
    k45 = r * (1 - 2 ** -0.5)
    for (sx, sy), (mx, my), (ex, ey) in (
            ((x1, y1 + r), (x1 + k45, y1 + k45), (x1 + r, y1)), ((x2 - r, y1), (x2 - k45, y1 + k45), (x2, y1 + r)),
            ((x2, y2 - r), (x2 - k45, y2 - k45), (x2 - r, y2)), ((x1 + r, y2), (x1 + k45, y2 - k45), (x1, y2 - r))):
        arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        arc.SetArcGeometry(P(sx, sy), P(mx, my), P(ex, ey))
        _edge(board, arc)
    return board


def add_gnd_pours(board, bcfg: dict, layers=("B.Cu",)):
    gnd = board.FindNet("GND")
    x1, y1, x2, y2, _ = outline_of(bcfg)
    for name in layers:
        layer = board.GetLayerID(name)
        if layer < 0:
            raise SystemExit(f"unknown layer {name!r} for GND pour")
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName(f"GND_{name}")
        z.SetLocalClearance(MM(0.25))
        z.SetMinThickness(MM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)  # SMD solid, THT thermal
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)  # no floating copper islands
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):  # clipped to Edge.Cuts by the filler
            ol.Append(MM(x), MM(y))
        z.SetAssignedPriority(0)
        board.Add(z)


def add_silk(board, items: list[dict]):
    for it in items:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(it["text"])
        t.SetPosition(pcbnew.VECTOR2I(MM(it["at"][0]), MM(it["at"][1])))
        lname = {"F.SilkS": "F.Silkscreen", "B.SilkS": "B.Silkscreen"}.get(it.get("layer"), it.get("layer", "F.Silkscreen"))
        lid = board.GetLayerID(lname)
        if lid < 0:
            raise SystemExit(f"unknown layer {lname!r} for silk text {it['text']!r}")
        t.SetLayer(lid)
        size = it.get("size", 1.0)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(size * 0.15))
        if lname.startswith("B."):
            t.SetMirrored(True)
        board.Add(t)


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
        try:
            fp.SetField(key, val)
        except Exception as e:  # API drift between versions: record, don't die
            print(f"  note: SetField({key}) failed: {e}")
    # like KiCad's own update: only Reference is on silk; everything else hidden on Fab
    fab = pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab
    for f in fp.GetFields():
        if f.GetName() not in ("Reference", "Value"):
            f.SetVisible(False)
            f.SetLayer(fab)
            if f.GetTextThickness() == 0:  # else the next GUI save adds (thickness 0.15): diff noise
                f.SetTextThickness(pcbnew.FromMM(0.15))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("netlist", type=Path)
    ap.add_argument("board", type=Path)
    ap.add_argument("--placement", type=Path)
    ap.add_argument("--lib", type=Path, default=Path(__file__).resolve().parents[1] / "hardware/lib")
    a = ap.parse_args()

    comps, pins, pinfo = read_netlist(a.netlist)
    place = tomllib.loads(a.placement.read_text()) if a.placement else {"parts": {}, "board": {}}
    created = not a.board.exists()
    board = new_board(place["board"]) if created else pcbnew.LoadBoard(str(a.board))

    # nets
    for name in sorted(set(pins.values())):
        if board.FindNet(name) is None:
            board.Add(pcbnew.NETINFO_ITEM(board, name))

    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    added, updated, removed = [], [], []
    park_x = (outline_of(place["board"])[2] if place["board"] else 0) + 10
    for ref, comp in sorted(comps.items()):
        fp = existing.get(ref)
        if fp is not None and str(fp.GetFPIDAsString()) != comp["footprint"]:
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
            fn, ty = pinfo.get((ref, pad.GetNumber()), ("", ""))
            pad.SetPinFunction(fn)  # as KiCad's Update PCB does; layout checks rely on it
            pad.SetPinType(ty)
            pad.SetNet(board.FindNet(net) if net else board.FindNet(""))
            if net is None and pad.GetNumber():
                pad.SetNetCode(0)
    for ref, fp in existing.items():
        if ref not in comps:
            board.Remove(fp)
            removed.append(ref)

    if created:
        add_gnd_pours(board, place["board"], place["board"].get("gnd_pour_layers", ["B.Cu"]))
        add_silk(board, place.get("silk", []))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(a.board), board)
    print(f"{'created' if created else 'synced'} {a.board}: +{len(added)} {added} "
          f"~{len(updated)} {updated} -{len(removed)} {removed}")


if __name__ == "__main__":
    main()
