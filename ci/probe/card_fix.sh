#!/usr/bin/env bash
# Agent fix of the card board: fan out stranded top-pour GND pads, move colliding labels, DRC.
o=$PWD/out
cd hardware
kicad-cli pcb drc --severity-all --schematic-parity --format json -o $o/drc-before.json hwlab.kicad_pcb >/dev/null
python3 ../tools/gnd_fanout.py hwlab.kicad_pcb --width 0.2 --clearance 0.18; echo "fanout rc=$?"
python3 ../tools/fix_labels.py hwlab.kicad_pcb; echo "labels rc=$?"
kicad-cli pcb drc --severity-all --schematic-parity --refill-zones --format json -o $o/drc-after.json hwlab.kicad_pcb >/dev/null
for f in before after; do echo "== DRC $f"; python3 - $o/drc-$f.json <<'PY'
import json, sys, collections
d = json.load(open(sys.argv[1])); c = collections.Counter()
for sec in ("violations", "unconnected_items", "schematic_parity"):
    for v in d.get(sec, []): c[(sec, v["type"], v["severity"])] += 1
for k, n in sorted(c.items()): print(n, *k)
PY
done
python3 ../tools/check_report.py drc $o/drc-after.json --waivers waivers.toml --allow-warnings; echo "gate rc=$?"
python3 ../tools/layout_check.py hwlab.kicad_pcb --gate decap edges antenna | tail -5
cp hwlab.kicad_pcb $o/
