#!/usr/bin/env bash
# Agent rework around the IMU: the autorouter walled in U3's GND pads (SDA/INT1 vias on the
# left, a +3V3 loop below). Rip up the local signal/supply routing, give the GND pads their
# own fan-out vias first, re-run Freerouting for the rest, then clean up and check.
o=$PWD/out
cd hardware
python3 - <<'PY'
import pcbnew
T = pcbnew.ToMM
b = pcbnew.LoadBoard('hwlab.kicad_pcb')
win = lambda p: 142.0 <= T(p.x) <= 148.5 and 125.0 <= T(p.y) <= 129.0
whole = {'/I2C_SDA', '/IMU_INT1', '/IMU_INT2'}
gone = [t for t in b.GetTracks() if t.GetNetname() in whole or
        (t.GetNetname() == '+3V3' and (win(t.GetPosition()) if t.GetClass() == 'PCB_VIA' else (win(t.GetStart()) or win(t.GetEnd()))))]
for t in gone: b.Remove(t)
pcbnew.SaveBoard('hwlab.kicad_pcb', b)
print('ripped up', len(gone), 'items')
PY
python3 ../tools/gnd_fanout.py hwlab.kicad_pcb --width 0.2 --clearance 0.18 --force U3.2,U3.6; echo "forced fanout rc=$?"
# --- re-route what is now unrouted
apt-get update -qq && apt-get install -y -qq openjdk-21-jre-headless curl >/dev/null 2>&1
curl -sL -o /tmp/fr.jar https://github.com/freerouting/freerouting/releases/download/v2.1.0/freerouting-2.1.0.jar
python3 -c "import pcbnew; b=pcbnew.LoadBoard('hwlab.kicad_pcb'); print('dsn', pcbnew.ExportSpecctraDSN(b, '/tmp/hwlab.dsn'))"
timeout 900 java -jar /tmp/fr.jar -de /tmp/hwlab.dsn -do /tmp/hwlab.ses -mp 100 --gui.enabled=false 2>&1 | tail -8
python3 - <<'PY'
import pcbnew
b = pcbnew.LoadBoard('hwlab.kicad_pcb')
print('ses', pcbnew.ImportSpecctraSES(b, '/tmp/hwlab.ses'))
# remove dangling track ends left by the rip-up (repeat until stable)
while True:
    tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    pads = list(b.GetPads())
    def joined(t, pt):
        n = t.GetNetCode()
        return (any(p.GetNetCode() == n and p.IsOnLayer(t.GetLayer()) and p.HitTest(pt) for p in pads)
                or any(v.GetNetCode() == n and v.HitTest(pt) for v in vias)
                or any(u is not u2 and u.GetNetCode() == n and u.GetLayer() == t.GetLayer() and u.HitTest(pt)
                       for u in tracks for u2 in [t]))
    dead = [t for t in tracks if not (joined(t, t.GetStart()) and joined(t, t.GetEnd()))]
    if not dead: break
    for t in dead: b.Remove(t)
    print('removed dangling', len(dead))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard('hwlab.kicad_pcb', b)
PY
python3 ../tools/gnd_fanout.py hwlab.kicad_pcb --width 0.2 --clearance 0.18; echo "fanout rc=$?"
python3 ../tools/fix_labels.py hwlab.kicad_pcb; echo "labels rc=$?"
kicad-cli pcb drc --severity-all --schematic-parity --refill-zones --format json -o $o/drc.json hwlab.kicad_pcb >/dev/null
python3 - $o/drc.json <<'PY'
import json, sys, collections
d = json.load(open(sys.argv[1])); c = collections.Counter()
for sec in ("violations", "unconnected_items", "schematic_parity"):
    for v in d.get(sec, []):
        c[(sec, v["type"], v["severity"])] += 1
        if v["severity"] == "error": print("  ", v["description"], "|", " / ".join(i["description"] for i in v["items"]))
for k, n in sorted(c.items()): print(n, *k)
PY
python3 ../tools/check_report.py drc $o/drc.json --allow-warnings; echo "gate (no waivers) rc=$?"
python3 ../tools/layout_check.py hwlab.kicad_pcb --gate decap edges antenna | tail -4
cp hwlab.kicad_pcb $o/
