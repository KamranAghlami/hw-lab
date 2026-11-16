#!/usr/bin/env python3
"""Measured layout checklist (runs in CI with pcbnew). Prints a scored table.

    layout_check.py hardware/hwlab.kicad_pcb [--decap-mm 3] [--json out.json]

Checks (each PASS/FAIL with the numbers behind it):
  decap      each cap required by parts.toml `decap` is bound to its IC pin; 100n/1u <= N mm, bulk <= 10 mm
  edges      USB-C (J1) and debug port (J2) touch the board edge (<= 1 mm)
  antenna    U1's antenna end is at the board edge (<= 0.5 mm)
  inside     every footprint's pads lie inside the outline
  rotations  all footprints at multiples of 90 degrees
  angles     all track segments at multiples of 45 degrees
  vias       via count (informational)
With --gate <checks...> it exits 1 if any named check fails (CI uses decap, edges, antenna).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tomllib
from pathlib import Path

import pcbnew

MM = pcbnew.ToMM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--decap-mm", type=float, default=3.0)
    ap.add_argument("--json")
    ap.add_argument("--parts", default=str(Path(__file__).resolve().parents[1] / "hardware/lib/parts.toml"))
    ap.add_argument("--gate", nargs="*", default=None,
                    help="fail (exit 1) if any of these checks fail, e.g. --gate decap edges antenna")
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    edge = b.GetBoardEdgesBoundingBox()
    ex1, ey1, ex2, ey2 = MM(edge.GetLeft()), MM(edge.GetTop()), MM(edge.GetRight()), MM(edge.GetBottom())
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    res = []

    def add(name, ok, detail):
        res.append({"check": name, "pass": bool(ok), "detail": detail})

    # decap distance: bind each required cap (parts.toml `decap`) to the pad it serves.
    # Greedy: per IC power pad, nearest unassigned cap of the required value on that net.
    parts = {p["name"]: p for p in tomllib.loads(Path(a.parts).read_text())["part"]}
    reqs = []  # (ref, pin name, pad, value)
    for r, fp in fps.items():
        part = next((p for p in parts.values() if p.get("mpn") == fp.GetFieldText("MPN")), None)
        if not part:
            continue
        for pin_name, values in part.get("decap", {}).items():
            pads = [p for p in fp.Pads() if p.GetPinFunction().upper() == pin_name.upper()]
            if not pads:
                continue
            for v in values:
                reqs.append((r, pin_name, pads[0], v))
    caps = {r: fp for r, fp in fps.items() if r.startswith("C")}
    used, bound = set(), []
    for r, pin_name, pad, v in sorted(reqs, key=lambda q: (q[3] not in ("100n", "1u"), q[0])):
        cand = []
        for cr, cfp in caps.items():
            if cr in used or cfp.GetValue() != v:
                continue
            cp = [p for p in cfp.Pads() if p.GetNetCode() == pad.GetNetCode()]
            if cp:
                cand.append((min(MM((p.GetPosition() - pad.GetPosition()).EuclideanNorm()) for p in cp), cr))
        if not cand:
            bound.append((f"{r}.{pin_name}", v, None, None))
            continue
        d, cr = min(cand)
        used.add(cr)
        bound.append((f"{r}.{pin_name}", v, cr, round(d, 2)))
    def limit(v):
        return a.decap_mm if v in ("100n", "1u") else 10.0
    bad = [x for x in bound if x[2] is None or x[3] > limit(x[1])]
    add("decap", not bad, "pin<-cap mm: " + ", ".join(f"{p}<-{c}({v}) {d}" for p, v, c, d in bound)
        + f"; limits {a.decap_mm} mm (<=1u) / 10 mm (bulk); violations: {bad}")

    # connectors / antenna at edges
    def edge_gap(fp):
        bb = fp.GetBoundingBox(False)
        return round(min(abs(MM(bb.GetLeft()) - ex1), abs(ex2 - MM(bb.GetRight())),
                         abs(MM(bb.GetTop()) - ey1), abs(ey2 - MM(bb.GetBottom()))), 2)
    gaps = {r: edge_gap(fps[r]) for r in ("J1", "J2") if r in fps}
    add("edges", all(g <= 1.0 for g in gaps.values()), f"edge gap mm {gaps}")
    if "U1" in fps:
        u1 = fps["U1"]
        # antenna end = module body edge on the side the antenna points to (local -y)
        ang = math.radians(u1.GetOrientationDegrees())
        c = u1.GetPosition()
        tip = (MM(c.x) - 12.75 * math.sin(ang), MM(c.y) - 12.75 * math.cos(ang))
        gap = round(min(abs(tip[0] - ex1), abs(ex2 - tip[0]), abs(tip[1] - ey1), abs(ey2 - tip[1])), 2)
        add("antenna", gap <= 0.5, f"antenna end {tuple(round(v, 2) for v in tip)}, gap to edge {gap} mm")
    # inside outline
    outside = [r for r, fp in fps.items() for p in fp.Pads()
               if not (ex1 <= MM(p.GetPosition().x) <= ex2 and ey1 <= MM(p.GetPosition().y) <= ey2)]
    add("inside", not outside, f"pads outside: {sorted(set(outside))}")
    rots = {r: fp.GetOrientationDegrees() for r, fp in fps.items() if round(fp.GetOrientationDegrees()) % 90}
    add("rotations", not rots, f"non-90 rotations: {rots}")
    bad = 0
    n = 0
    vias = 0
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias += 1
            continue
        if t.GetClass() != "PCB_TRACK":
            continue
        n += 1
        dx, dy = t.GetEnd().x - t.GetStart().x, t.GetEnd().y - t.GetStart().y
        if dx == 0 and dy == 0:
            continue
        deg = math.degrees(math.atan2(dy, dx)) % 45
        if min(deg, 45 - deg) > 0.5:
            bad += 1
    add("angles", bad == 0, f"{bad}/{n} segments not at 45-degree multiples")
    add("vias", True, f"{vias} vias")

    score = sum(r["pass"] for r in res if r["check"] != "vias")
    total = len([r for r in res if r["check"] != "vias"])
    for r in res:
        print(f"  {'PASS' if r['pass'] else 'FAIL'}  {r['check']:<10} {r['detail']}")
    print(f"layout checklist: {score}/{total}")
    if a.json:
        json.dump({"score": score, "total": total, "checks": res}, open(a.json, "w"), indent=2)
    if a.gate is not None:
        failed = [r["check"] for r in res if not r["pass"] and r["check"] in a.gate]
        if failed:
            print(f"layout gate FAILED: {failed}")
            sys.exit(1)


if __name__ == "__main__":
    main()
