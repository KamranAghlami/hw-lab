#!/usr/bin/env bash
# Agent-side fix: stitch dangling GND track ends to the bottom plane with a via.
cd hardware
python3 - <<'PY'
import pcbnew
b = pcbnew.LoadBoard('hwlab.kicad_pcb')
gnd = b.FindNet('GND')
ends = {}
for t in b.GetTracks():
    if t.GetNetname() == 'GND' and t.GetClass() == 'PCB_TRACK':
        for p in (t.GetStart(), t.GetEnd()):
            ends[(p.x, p.y)] = ends.get((p.x, p.y), 0) + 1
pads = [p for p in b.GetPads() if p.GetNetname() == 'GND']
added = 0
for (x, y), n in ends.items():
    if n != 1:
        continue
    pt = pcbnew.VECTOR2I(x, y)
    if any(p.HitTest(pt) for p in pads):
        continue
    v = pcbnew.PCB_VIA(b); v.SetPosition(pt); v.SetNet(gnd)
    v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); b.Add(v); added += 1
    print('via at', pcbnew.ToMM(x), pcbnew.ToMM(y))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard('hwlab.kicad_pcb', b)
print('vias added', added)
PY
kicad-cli pcb drc --severity-all --schematic-parity -o ../out/drc.rpt hwlab.kicad_pcb; grep -E "^\[|Found" ../out/drc.rpt | sort | uniq -c
cp hwlab.kicad_pcb ../out/
