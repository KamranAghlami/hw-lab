#!/usr/bin/env python3
"""Gate CI on a KiCad ERC/DRC JSON report, with semantic waivers.

    check_report.py erc out/erc.json --waivers hardware/waivers.toml
    check_report.py drc out/drc.json --waivers hardware/waivers.toml

Every violation (error *or* warning), unconnected item and schematic-parity
issue fails the gate unless a waiver matches it. A waiver matches on the rule
`type` plus substrings that must each appear in some item description, e.g.

    [[erc]]
    type = "pin_to_pin"
    items = ["Symbol U3 Pin 1 ", "#FLG02"]
    reason = "SA0 strapped to GND on purpose"

Unlike KiCad's own exclusions (which key on coordinates + UUIDs), these survive
moving things around and are readable in review. Unused waivers are reported
so they don't rot. Writes a Markdown summary to $GITHUB_STEP_SUMMARY if set.
Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path


def violations(kind: str, report: dict) -> list[dict]:
    out = []
    if kind == "erc":
        for sheet in report.get("sheets", []):
            for v in sheet.get("violations", []):
                out.append({**v, "_where": sheet.get("path", "")})
    else:
        for key in ("violations", "unconnected_items", "schematic_parity"):
            for v in report.get(key, []):
                out.append({**v, "_where": key})
    return out


def matches(w: dict, v: dict) -> bool:
    if w.get("type") not in (None, v.get("type")):
        return False
    descs = [i.get("description", "") for i in v.get("items", [])]
    return all(any(s in d for d in descs) for s in w.get("items", []))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["erc", "drc"])
    ap.add_argument("report", type=Path)
    ap.add_argument("--waivers", type=Path)
    ap.add_argument("--allow-warnings", action="store_true", help="only errors fail the gate")
    a = ap.parse_args()

    report = json.loads(a.report.read_text())
    waivers = tomllib.loads(a.waivers.read_text()).get(a.kind, []) if a.waivers and a.waivers.exists() else []
    used = [0] * len(waivers)
    failing, waived = [], []
    for v in violations(a.kind, report):
        hit = next((i for i, w in enumerate(waivers) if matches(w, v)), None)
        if hit is not None:
            used[hit] += 1
            waived.append((v, waivers[hit]))
        elif v.get("severity") == "error" or not a.allow_warnings:
            failing.append(v)

    lines = [f"### {a.kind.upper()}: {len(failing)} failing, {len(waived)} waived"]
    for v in failing:
        items = "; ".join(i.get("description", "") for i in v.get("items", []))
        lines.append(f"- **{v.get('severity')}** `{v.get('type')}` {v.get('description')} — {items}")
    for v, w in waived:
        lines.append(f"- waived `{v.get('type')}`: {w.get('reason', '(no reason)')}")
    for w, n in zip(waivers, used):
        if n == 0:
            lines.append(f"- WARNING: unused waiver `{w.get('type')}` {w.get('items')} — remove it?")
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text + "\n\n")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
