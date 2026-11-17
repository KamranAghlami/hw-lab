#!/usr/bin/env bash
# Dump all copper within a window around the IMU (U3), both layers.
cd hardware
python3 - <<'PY'
import pcbnew
T = pcbnew.ToMM
b = pcbnew.LoadBoard('hwlab.kicad_pcb')
x0, y0, x1, y1 = 140.5, 122.5, 151.5, 131.5
def inwin(p): return x0 <= T(p.x) <= x1 and y0 <= T(p.y) <= y1
for p in b.GetPads():
    if inwin(p.GetPosition()):
        s = p.GetSize()
        print(f"PAD {p.GetParentFootprint().GetReference()}.{p.GetNumber():>3} {p.GetNetname():22s} at ({T(p.GetPosition().x):.3f},{T(p.GetPosition().y):.3f}) "
              f"size {T(s.x):.3f}x{T(s.y):.3f} rot {p.GetOrientation().AsDegrees():.0f} {'F' if p.IsOnLayer(pcbnew.F_Cu) else ''}{'B' if p.IsOnLayer(pcbnew.B_Cu) else ''}")
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        if inwin(t.GetPosition()):
            print(f"VIA {t.GetNetname():22s} at ({T(t.GetPosition().x):.3f},{T(t.GetPosition().y):.3f}) d {T(t.GetWidth(pcbnew.F_Cu)):.2f}/{T(t.GetDrill()):.2f}")
    elif inwin(t.GetStart()) or inwin(t.GetEnd()):
        print(f"TRK {b.GetLayerName(t.GetLayer())} {t.GetNetname():22s} ({T(t.GetStart().x):.3f},{T(t.GetStart().y):.3f})->({T(t.GetEnd().x):.3f},{T(t.GetEnd().y):.3f}) w {T(t.GetWidth()):.2f}")
PY
