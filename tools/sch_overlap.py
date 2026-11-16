#!/usr/bin/env python3
"""Readability lint for a .kicad_sch: report overlapping text/graphics.

    sch_overlap.py hardware/hwlab.kicad_sch [--max N]

ERC checks connectivity, not legibility; the owner reviews the schematic PDF, so
overlapping labels, power symbols, field texts and symbol bodies are defects.
Boxes are approximations (stroke-font width ~0.85 x size per character), good
enough to catch collisions. Checked pairs: every label / visible field / symbol
body against every other, except a symbol's own fields against its own body.
Exit 1 if more than --max overlaps (default 0). Stdlib only.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kisexpr as k  # noqa: E402

CHAR = 0.85    # average advance per character, x font size
SHRINK = 0.15  # ignore touching edges


def text_box(text, x, y, angle, size, hj="center", vj="center", pad=0.0):
    w, h = len(text) * CHAR * size, size
    u = {"left": (0, w), "right": (-w, 0)}.get(hj, (-w / 2, w / 2))
    v = {"bottom": (0, h), "top": (-h, 0)}.get(vj, (-h / 2, h / 2))
    a = int(round(angle)) % 180
    if a == 0:   # reads left->right; v is "up" (screen -y)
        return (x + u[0] - pad, y - v[1] - pad, x + u[1] + pad, y - v[0] + pad)
    return (x - v[1] - pad, y - u[1] - pad, x - v[0] + pad, y - u[0] + pad)  # reads bottom->top


def effects(node):
    eff = k.find(node, "effects")
    size, hj, vj = 1.27, "center", "center"
    if eff is not None:
        font = k.find(eff, "font")
        if font is not None and k.find(font, "size") is not None:
            size = float(k.find(font, "size")[1])
        j = k.find(eff, "justify")
        if j is not None:
            for t in j[1:]:
                if t in ("left", "right"):
                    hj = str(t)
                elif t in ("top", "bottom"):
                    vj = str(t)
        if k.find(eff, "hide") is not None and str(k.find(eff, "hide")[-1]) != "no":
            return None
    return size, hj, vj


def lib_bbox(sym) -> tuple[float, float, float, float] | None:
    xs, ys = [], []
    for n in k.walk(sym):
        h = k.head(n)
        if h == "rectangle":
            for key in ("start", "end"):
                p = k.find(n, key); xs.append(float(p[1])); ys.append(float(p[2]))
        elif h in ("polyline", "bezier"):
            for p in k.walk(k.find(n, "pts")):
                if k.head(p) == "xy":
                    xs.append(float(p[1])); ys.append(float(p[2]))
        elif h == "circle":
            c, r = k.find(n, "center"), float(k.find(n, "radius")[1])
            xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
        elif h == "arc":
            for key in ("start", "mid", "end"):
                p = k.find(n, key); xs.append(float(p[1])); ys.append(float(p[2]))
        elif h == "pin":
            at, ln = k.find(n, "at"), float(k.find(n, "length")[1])
            px, py, a = float(at[1]), float(at[2]), math.radians(float(at[3]))
            xs += [px, px + ln * math.cos(a)]; ys += [py, py + ln * math.sin(a)]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def place_box(b, x, y, rot, mirror):
    pts = []
    for px in (b[0], b[2]):
        for py in (b[1], b[3]):
            if mirror == "x":
                py = -py
            elif mirror == "y":
                px = -px
            r = math.radians(rot)
            rx, ry = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
            pts.append((x + rx, y - ry))
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def collect(sch) -> list[tuple[str, str, tuple]]:
    libs = {str(s[1]): s for s in k.children(k.find(sch, "lib_symbols"), "symbol")}
    items = []
    for s in k.children(sch, "symbol"):
        lib_id = str(k.find(s, "lib_id")[1])
        at = k.find(s, "at")
        x, y, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0
        mir = k.find(s, "mirror")
        ref = next((str(p[2]) for p in k.children(s, "property") if p[1] == "Reference"), "?")
        bb = lib_bbox(libs[lib_id]) if lib_id in libs else None
        if bb:
            items.append(("body", ref, place_box(bb, x, y, rot, str(mir[1]) if mir else None)))
        for p in k.children(s, "property"):
            if k.find(p, "hide") is not None and str(k.find(p, "hide")[1]) == "yes":
                continue
            if not str(p[2]) or str(p[1]).startswith("ki_"):
                continue
            e = effects(p)
            if e is None:
                continue
            pat = k.find(p, "at")
            items.append((f"field {p[1]}", ref, text_box(str(p[2]), float(pat[1]), float(pat[2]), float(pat[3]), *e)))
    for kind in ("label", "global_label", "hierarchical_label"):
        for lb in k.children(sch, kind):
            at = k.find(lb, "at")
            size, hj, vj = effects(lb) or (1.27, "left", "bottom")
            pad = 0.3 if kind != "label" else 0.0
            items.append((kind, str(lb[1]), text_box(str(lb[1]), float(at[1]), float(at[2]), float(at[3]),
                                                    size, hj, vj if kind == "label" else "center", pad)))
    return items


def overlap(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0]) - SHRINK
    h = min(a[3], b[3]) - max(a[1], b[1]) - SHRINK
    return w * h if w > 0 and h > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("schematic", type=Path)
    ap.add_argument("--max", type=int, default=0)
    a = ap.parse_args()
    items = collect(k.load(a.schematic))
    hits = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (ka, oa, ba), (kb, ob, bb) = items[i], items[j]
            if oa == ob and "body" in (ka, kb):
                continue  # a symbol's own fields may sit on its body
            if overlap(ba, bb) > 0:
                hits.append(f"{ka} '{oa}' @({ba[0]:.1f},{ba[1]:.1f}) overlaps {kb} '{ob}' @({bb[0]:.1f},{bb[1]:.1f})")
    for h in hits:
        print("  " + h)
    print(f"{a.schematic}: {len(items)} items, {len(hits)} overlaps")
    return 1 if len(hits) > a.max else 0


if __name__ == "__main__":
    sys.exit(main())
