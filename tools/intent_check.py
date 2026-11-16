#!/usr/bin/env python3
"""Design-intent checks on the netlist, before any layout exists.

    intent_check.py <netlist.net> [--parts hardware/lib/parts.toml] [--lib hardware/lib]

ERC only checks connectivity rules; these check what the designer meant, from
facts recorded per part in parts.toml:

  pinout   `datasheet_pins` (pad -> datasheet name, "|" for aliases) must agree
           with the symbol's pin names (netlist pinfunction) AND every pad must
           exist in the footprint. Catches borrowed symbols with the wrong
           pinout and symbol/footprint numbering mismatches.
  decap    `decap = { "<pin name>" = ["100n", ...] }`: for every instance, each
           listed value must be present as a capacitor on that pin's net. Caps
           are counted per net and shared requirements must all be met.
Exit 1 on any failure. Stdlib only.
"""
from __future__ import annotations

import argparse
import collections
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kisexpr as k  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def norm(s: str) -> str:
    return s.strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("netlist", type=Path)
    ap.add_argument("--parts", type=Path, default=ROOT / "hardware/lib/parts.toml")
    ap.add_argument("--lib", type=Path, default=ROOT / "hardware/lib")
    a = ap.parse_args()
    parts = {p["name"]: p for p in tomllib.loads(a.parts.read_text())["part"]}
    t = k.load(a.netlist)

    comps = {}
    for c in k.children(k.find(t, "components"), "comp"):
        ref = str(k.find(c, "ref")[1])
        src = k.find(c, "libsource")
        comps[ref] = {"part": str(k.find(src, "part")[1]) if src else "", "value": str(k.find(c, "value")[1]),
                      "footprint": str(k.find(c, "footprint")[1])}
    pin_net, pin_fn = {}, {}
    net_members = collections.defaultdict(list)
    for n in k.children(k.find(t, "nets"), "net"):
        name = str(k.find(n, "name")[1])
        for nd in k.children(n, "node"):
            ref, pin = str(k.find(nd, "ref")[1]), str(k.find(nd, "pin")[1])
            fn = k.find(nd, "pinfunction")
            fn = str(fn[1]) if fn else ""
            if fn.endswith("_" + pin):
                fn = fn[: -len(pin) - 1]
            pin_net[(ref, pin)] = name
            pin_fn[(ref, pin)] = fn
            net_members[name].append(ref)

    fails, oks = [], 0
    pads_cache: dict[str, set] = {}
    need = collections.defaultdict(collections.Counter)  # net -> value -> count required
    who = collections.defaultdict(list)
    for ref, c in sorted(comps.items()):
        p = parts.get(c["part"])
        if not p:
            continue
        table = p.get("datasheet_pins", {})
        if table:
            libnick, fp = c["footprint"].split(":")
            if fp not in pads_cache:
                tree = k.load(a.lib / f"{libnick}.pretty" / f"{fp}.kicad_mod")
                pads_cache[fp] = {str(pd[1]) for pd in k.children(tree, "pad")}
            for pad, names in table.items():
                ok_names = {norm(x) for x in names.split("|")}
                got = pin_fn.get((ref, pad))
                if pad not in pads_cache[fp]:
                    fails.append(f"pinout {ref} ({c['part']}): pad {pad} missing in footprint {fp}")
                elif got is None:
                    fails.append(f"pinout {ref} ({c['part']}): symbol has no pin {pad} (datasheet: {names})")
                elif norm(got) not in ok_names:
                    fails.append(f"pinout {ref} ({c['part']}): pin {pad} is '{got}' in the symbol, datasheet says '{names}'")
                else:
                    oks += 1
        for pin_name, values in p.get("decap", {}).items():
            pins = [pn for (r, pn), fn in pin_fn.items() if r == ref and norm(fn) == norm(pin_name)]
            if not pins:
                fails.append(f"decap {ref}: no pin named {pin_name}")
                continue
            net = pin_net[(ref, pins[0])]
            for v in values:
                need[net][v] += 1
                who[(net, v)].append(f"{ref}.{pin_name}")
    for net, req in need.items():
        have = collections.Counter(comps[r]["value"] for r in set(net_members[net]) if r.startswith("C"))
        for v, n in req.items():
            if have[v] < n:
                fails.append(f"decap net {net}: needs {n} x {v} for {who[(net, v)]}, found {have[v]}")
            else:
                oks += 1
    for f in fails:
        print("  FAIL " + f)
    print(f"intent check: {oks} ok, {len(fails)} failing")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
