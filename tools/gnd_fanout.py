#!/usr/bin/env python3
"""Connect stranded top-layer GND pour fragments to the bottom GND plane (runs with pcbnew).

    gnd_fanout.py board.kicad_pcb [--via 0.5 --drill 0.25 --width 0.25 --clearance 0.25]

A top-pour fragment that holds GND pads but no via and no through-hole pad is
an island that only *looks* connected: the pads on it reach nothing else. That
is a real open (DRC "unconnected items"), not a cosmetic sliver. For each such
fragment this adds a fan-out: a short F.Cu track from one of its GND pads to a
new via, at the nearest spot where the via and the track clear every other-net
item on both layers, keep the hole-to-hole gap, stay off other pads and stay
inside the board edge. Zones are refilled and the board is saved. Prints what it
did, and exits 1 if a fragment could not be fixed.
"""
import argparse
import math
import sys

import pcbnew

MM = pcbnew.FromMM


def shape_of(item, layer):
    try:
        return item.GetEffectiveShape(layer)
    except Exception:  # noqa: BLE001 - fall back to the bounding box
        bb = item.GetBoundingBox()
        return pcbnew.SHAPE_RECT(bb)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--via", type=float, default=0.5)
    ap.add_argument("--drill", type=float, default=0.25)
    ap.add_argument("--width", type=float, default=0.25)
    ap.add_argument("--clearance", type=float, default=0.25)
    ap.add_argument("--hole-gap", type=float, default=0.5)
    ap.add_argument("--edge", type=float, default=0.3)
    ap.add_argument("--max-reach", type=float, default=3.0)
    a = ap.parse_args()

    b = pcbnew.LoadBoard(a.board)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    gnd = b.FindNet("GND")
    top_zone = [z for z in b.Zones() if z.GetNetname() == "GND" and z.IsOnLayer(pcbnew.F_Cu) and not z.GetIsRuleArea()][0]
    top = top_zone.GetFilledPolysList(pcbnew.F_Cu)
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline)

    layers = (pcbnew.F_Cu, pcbnew.B_Cu)
    pads = list(b.GetPads())
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    tracks = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA"]
    holes = [(p.GetPosition(), p.GetDrillSize().x / 2) for p in pads if p.HasHole()] + \
            [(v.GetPosition(), v.GetDrill() / 2) for v in vias]
    anchors = [v.GetPosition() for v in vias] + [p.GetPosition() for p in pads if p.HasHole() and p.GetNetname() == "GND"]
    # every other-net copper item per layer, plus all pads (a via must not land in any pad)
    others = {ly: [(i, shape_of(i, ly)) for i in pads + vias + tracks
                   if i.IsOnLayer(ly) and i.GetNetname() != "GND"] for ly in layers}
    all_pads = {ly: [(p, shape_of(p, ly)) for p in pads if p.IsOnLayer(ly)] for ly in layers}

    r, drill, w, clr = MM(a.via / 2), MM(a.drill / 2), MM(a.width), MM(a.clearance)

    def via_ok(c, src_pad):
        circ = pcbnew.SHAPE_CIRCLE(c, r)
        for ly in layers:
            if any(s.Collide(circ, clr) for _, s in others[ly]):
                return False
            if any(p is not src_pad and s.Collide(circ, MM(0.1)) for p, s in all_pads[ly]):
                return False
        if any((c - hp).EuclideanNorm() - hr - drill < MM(a.hole_gap) for hp, hr in holes):
            return False
        ring = [pcbnew.VECTOR2I(int(c.x + (r + MM(a.edge)) * math.cos(t)), int(c.y + (r + MM(a.edge)) * math.sin(t)))
                for t in [k * math.pi / 8 for k in range(16)]]
        return all(outline.Contains(p) for p in ring)

    def track_ok(p0, c, src_pad):
        seg = pcbnew.SHAPE_SEGMENT(p0, c, w)
        return not any(s.Collide(seg, clr) for _, s in others[pcbnew.F_Cu])

    fixed, failed = 0, 0
    for i in range(top.OutlineCount()):
        frag = top.Outline(i)
        if any(frag.PointInside(p) for p in anchors):
            continue
        fpads = [p for p in pads if p.GetNetname() == "GND" and p.IsOnLayer(pcbnew.F_Cu) and frag.PointInside(p.GetPosition())]
        name = ", ".join(f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in fpads) or "no pads"
        if not fpads:
            print(f"fragment {i}: no pads, no via ({name}); left for island removal")
            continue
        best = None
        for p in fpads:
            p0 = p.GetPosition()
            steps = int(a.max_reach / 0.1)
            for k in range(4, steps + 1):
                rad = MM(k * 0.1)
                for j in range(24):
                    t = j * math.pi / 12
                    c = pcbnew.VECTOR2I(int(p0.x + rad * math.cos(t)), int(p0.y + rad * math.sin(t)))
                    if via_ok(c, p) and track_ok(p0, c, p):
                        best = (p, c)
                        break
                if best:
                    break
            if best:
                break
        if not best:
            print(f"fragment {i} ({name}): NO fan-out spot within {a.max_reach} mm")
            failed += 1
            continue
        p, c = best
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(p.GetPosition()); t.SetEnd(c); t.SetWidth(w); t.SetLayer(pcbnew.F_Cu); t.SetNet(gnd)
        b.Add(t)
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(c); v.SetWidth(MM(a.via)); v.SetDrill(MM(a.drill)); v.SetNet(gnd)
        b.Add(v)
        # later fan-outs must clear what was just added (it is GND, so only the hole matters)
        holes.append((c, drill))
        anchors.append(c)
        fixed += 1
        print(f"fragment {i} ({name}): fan-out from {p.GetParentFootprint().GetReference()}.{p.GetNumber()} "
              f"to via at ({pcbnew.ToMM(c.x):.2f}, {pcbnew.ToMM(c.y):.2f}), "
              f"{pcbnew.ToMM((c - p.GetPosition()).EuclideanNorm()):.2f} mm")
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(a.board, b)
    print(f"gnd fan-out: {fixed} fixed, {failed} not fixable")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
