#!/usr/bin/env python3
"""Add GND stitching vias between the F.Cu and B.Cu GND pours (runs with pcbnew).

    stitch_gnd.py board.kicad_pcb [--pitch 4] [--via 0.6 --drill 0.3]

A candidate via on a grid is placed only if a ring around it (via radius +
clearance) lies inside the *filled* GND copper on both layers, i.e. it can only
ever touch GND. Then zones are refilled and the board saved. This joins pour
islands that an autorouter leaves behind, without any clearance risk.
"""
import argparse
import math

import pcbnew

MM = pcbnew.FromMM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--pitch", type=float, default=6.0)
    ap.add_argument("--via", type=float, default=0.6)
    ap.add_argument("--drill", type=float, default=0.3)
    ap.add_argument("--clearance", type=float, default=0.3)
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    gnd_zones = [z for z in b.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()]
    # keep every island while stitching, so enclosed pour areas can be rescued by a via;
    # afterwards islands that are still unconnected are removed again
    modes = {id(z): z.GetIslandRemovalMode() for z in gnd_zones}
    for z in gnd_zones:
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    gnd = b.FindNet("GND")
    fills = {}
    for z in b.Zones():
        if z.GetNetname() == "GND" and not z.GetIsRuleArea():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if z.IsOnLayer(layer):
                    fills[layer] = z.GetFilledPolysList(layer)
    if len(fills) < 2:
        raise SystemExit("need GND pours on F.Cu and B.Cu")
    bb = b.GetBoardEdgesBoundingBox()
    r = a.via / 2 + a.clearance
    ring = [(r * math.cos(t), r * math.sin(t)) for t in [i * math.pi / 6 for i in range(12)]] + [(0, 0)]
    existing = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    holes = [p.GetPosition() for p in b.GetPads() if p.HasHole()]
    texts = []
    for d in b.GetDrawings():
        if d.GetClass() == "PCB_TEXT":
            box = d.GetBoundingBox()
            box.Inflate(MM(0.5))  # mutates in place: do it once
            texts.append(box)
    added = 0
    y = bb.GetTop() + MM(a.pitch / 2)
    while y < bb.GetBottom():
        x = bb.GetLeft() + MM(a.pitch / 2)
        while x < bb.GetRight():
            pts = [pcbnew.VECTOR2I(int(x + MM(dx)), int(y + MM(dy))) for dx, dy in ring]
            c = pcbnew.VECTOR2I(int(x), int(y))
            near = (any((p - c).EuclideanNorm() < MM(a.pitch / 2) for p in existing)
                    or any((p - c).EuclideanNorm() < MM(1.5) for p in holes)
                    or any(t.Contains(c) for t in texts))
            if not near and all(fills[layer].Contains(p) for layer in fills for p in pts):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
                v.SetWidth(MM(a.via))
                v.SetDrill(MM(a.drill))
                v.SetNet(gnd)
                b.Add(v)
                added += 1
            x += MM(a.pitch)
        y += MM(a.pitch)
    # pass 2: every top-pour island that still has no via/THT gets one, if one fits
    filler.Fill(b.Zones())
    fills = {layer: [z for z in b.Zones() if z.GetNetname() == "GND" and z.IsOnLayer(layer)][0].GetFilledPolysList(layer)
             for layer in (pcbnew.F_Cu, pcbnew.B_Cu)}
    anchors = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA"] + holes
    top = fills[pcbnew.F_Cu]
    island_fix = 0
    r2 = 0.25 + 0.2  # smaller via (0.5/0.25 mm, inside JLC limits) for narrow islands
    ring = [(r2 * math.cos(t), r2 * math.sin(t)) for t in [i * math.pi / 8 for i in range(16)]] + [(0, 0)]
    for i in range(top.OutlineCount()):
        outline = top.Outline(i)
        if any(outline.PointInside(p) for p in anchors):
            continue
        bbx = outline.BBox()
        placed = False
        yy = bbx.GetTop()
        while yy < bbx.GetBottom() and not placed:
            xx = bbx.GetLeft()
            while xx < bbx.GetRight() and not placed:
                pts = [pcbnew.VECTOR2I(int(xx + MM(dx)), int(yy + MM(dy))) for dx, dy in ring]
                if all(outline.PointInside(p) for p in pts) and all(fills[pcbnew.B_Cu].Contains(p) for p in pts) \
                        and not any((p - pts[-1]).EuclideanNorm() < MM(1.5) for p in holes) \
                        and not any((t.GetPosition() - pts[-1]).EuclideanNorm() < MM(1.2)
                                    for t in b.GetTracks() if t.GetClass() == "PCB_VIA"):
                    v = pcbnew.PCB_VIA(b)
                    v.SetPosition(pts[-1]); v.SetWidth(MM(0.5)); v.SetDrill(MM(0.25)); v.SetNet(gnd)
                    b.Add(v)
                    island_fix += 1
                    placed = True
                xx += MM(0.25)
            yy += MM(0.25)
    for z in gnd_zones:
        z.SetIslandRemovalMode(modes[id(z)])
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(a.board, b)
    print(f"stitching vias added: {added} grid + {island_fix} island")


if __name__ == "__main__":
    main()
