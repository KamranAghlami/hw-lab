#!/usr/bin/env bash
# Locate the top-pour GND fragments that DRC reports as unconnected, and what is on/under them.
cd hardware
python3 - <<'PY'
import pcbnew
MM = pcbnew.ToMM
b = pcbnew.LoadBoard('hwlab.kicad_pcb')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z = {l: [x for x in b.Zones() if x.GetNetname() == 'GND' and x.IsOnLayer(l)][0] for l in (pcbnew.F_Cu, pcbnew.B_Cu)}
for l, zz in z.items():
    print(b.GetLayerName(l), 'island mode', zz.GetIslandRemovalMode(), 'min area', zz.GetMinIslandArea(),
          'clearance', MM(zz.GetLocalClearance() or 0), 'min width', MM(zz.GetMinThickness()), 'pad conn', zz.GetPadConnection())
top, bot = z[pcbnew.F_Cu].GetFilledPolysList(pcbnew.F_Cu), z[pcbnew.B_Cu].GetFilledPolysList(pcbnew.B_Cu)
print('B.Cu fragments', bot.OutlineCount())
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
gpads = [p for p in b.GetPads() if p.GetNetname() == 'GND']
gtracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'GND' and t.GetLayer() == pcbnew.F_Cu]
for i in range(top.OutlineCount()):
    o = top.Outline(i); bb = o.BBox()
    inside = lambda p: o.PointInside(p)
    v = [x for x in vias if inside(x.GetPosition())]
    pads = [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}{'(THT)' if p.HasHole() else ''}" for p in gpads
            if p.IsOnLayer(pcbnew.F_Cu) and inside(p.GetPosition())]
    tr = [t for t in gtracks if inside(t.GetStart()) or inside(t.GetEnd())]
    area = abs(o.Area()) / 1e12
    print(f"frag {i}: area {area:.2f} mm2 bbox ({MM(bb.GetLeft()):.2f},{MM(bb.GetTop()):.2f})-({MM(bb.GetRight()):.2f},{MM(bb.GetBottom()):.2f})"
          f" vias {len(v)} pads {pads} F.Cu-GND-tracks {len(tr)}")
PY
kicad-cli pcb drc --severity-all --refill-zones --format json -o ../out/drc.json hwlab.kicad_pcb >/dev/null
kicad-cli pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet --layers F.Cu,Edge.Cuts -o ../out/fcu.svg hwlab.kicad_pcb
rsvg-convert -b '#2b2b2b' -w 2400 ../out/fcu.svg -o ../out/fcu.png
