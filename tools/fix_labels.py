#!/usr/bin/env python3
"""Move reference designators that sit on pads or collide with other silk (runs with pcbnew).

    fix_labels.py board.kicad_pcb [--dry-run]

Only labels that currently conflict are moved (minimal diff). A label conflicts
when its box (grown by --gap) touches any pad on its side, any other silk item
(footprint outlines are checked segment by segment, not as one big box), another
label or board text, or comes within --edge of the board edge. Candidate spots
are tried around the footprint at growing distances, horizontal first, then
vertical; the first free one wins. Unfixable labels are reported, never hidden.
"""
import argparse
import sys

import pcbnew

MM = pcbnew.FromMM


def box(item, grow=0):
    bb = item.GetBoundingBox()
    if grow:
        bb.Inflate(grow)  # in place: only on a copy
    return bb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--gap", type=float, default=0.15)
    ap.add_argument("--edge", type=float, default=0.5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    gap = MM(a.gap)
    edge = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(edge, True)
    edge.Deflate(MM(a.edge), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS if hasattr(pcbnew, "CORNER_STRATEGY_ROUND_ALL_CORNERS") else 0, 16)

    fps = list(b.GetFootprints())
    side_silk = {pcbnew.F_Cu: pcbnew.F_SilkS, pcbnew.B_Cu: pcbnew.B_SilkS}

    def obstacles(owner, silk_layer, cu_layer):
        obs = []
        for fp in fps:
            for p in fp.Pads():
                if p.IsOnLayer(cu_layer):
                    obs.append(box(p))
            for g in fp.GraphicalItems():
                if g.GetLayer() == silk_layer and g.GetClass() != "PCB_FIELD":
                    obs.append(box(g))
            if fp is not owner:
                r = fp.Reference()
                if r.IsVisible() and r.GetLayer() == silk_layer:
                    obs.append(box(r))
        for d in b.GetDrawings():
            if d.GetLayer() == silk_layer:
                obs.append(box(d))
        return obs

    def conflicts(lbl, obs):
        lb = box(lbl, gap)
        hits = [o for o in obs if lb.Intersects(o)]
        corners = [pcbnew.VECTOR2I(lb.GetLeft(), lb.GetTop()), pcbnew.VECTOR2I(lb.GetRight(), lb.GetTop()),
                   pcbnew.VECTOR2I(lb.GetLeft(), lb.GetBottom()), pcbnew.VECTOR2I(lb.GetRight(), lb.GetBottom())]
        out = not all(edge.Contains(c) for c in corners)
        return hits, out

    moved, stuck = 0, []
    for fp in sorted(fps, key=lambda f: f.GetReference()):
        lbl = fp.Reference()
        if not lbl.IsVisible():
            continue
        silk = lbl.GetLayer()
        cu = pcbnew.F_Cu if silk == pcbnew.F_SilkS else pcbnew.B_Cu
        obs = obstacles(fp, silk, cu)
        hits, out = conflicts(lbl, obs)
        if not hits and not out:
            continue
        orig_pos, orig_ang = lbl.GetPosition(), lbl.GetTextAngle()
        body = fp.GetBoundingBox(False)  # without texts
        cx, cy = body.GetCenter().x, body.GetCenter().y
        done = False
        for extra in [0.2 * k for k in range(0, 11)]:
            for ang in (0, 90):
                lbl.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
                lw, lh = lbl.GetBoundingBox().GetWidth(), lbl.GetBoundingBox().GetHeight()
                e = MM(extra) + gap
                cands = [(cx, body.GetTop() - lh // 2 - e), (cx, body.GetBottom() + lh // 2 + e),
                         (body.GetLeft() - lw // 2 - e, cy), (body.GetRight() + lw // 2 + e, cy)]
                for x, y in cands:
                    lbl.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
                    h, o = conflicts(lbl, obs)
                    if not h and not o:
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if done:
            moved += 1
            p = lbl.GetPosition()
            print(f"{fp.GetReference()}: label moved to ({pcbnew.ToMM(p.x):.2f}, {pcbnew.ToMM(p.y):.2f}) "
                  f"angle {lbl.GetTextAngle().AsDegrees():.0f} (was {len(hits)} overlaps{', off-board' if out else ''})")
        else:
            lbl.SetPosition(orig_pos); lbl.SetTextAngle(orig_ang)
            stuck.append(fp.GetReference())
            print(f"{fp.GetReference()}: NO free spot ({len(hits)} overlaps{', off-board' if out else ''}); left as is")
    if not a.dry_run:
        pcbnew.SaveBoard(a.board, b)
    print(f"labels: {moved} moved, {len(stuck)} stuck {stuck}")
    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
