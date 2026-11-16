#!/usr/bin/env python3
"""Approach B: same design, same placement, serialized with kiutils 1.4.8.

Reuses the design + geometry from hardware/design.py (so only the writer differs)
and builds kiutils objects. Output: experiments/kiutils/hwlab.kicad_sch
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "hardware")]

from kiutils.items.common import Effects, Font, Justify, Position, Property, Stroke  # noqa: E402
from kiutils.items.schitems import (Connection, LocalLabel, NoConnect, SchematicSymbol,  # noqa: E402
                                    SymbolProjectInstance, SymbolProjectPath)
from kiutils.schematic import Schematic  # noqa: E402
from kiutils.symbol import SymbolLib  # noqa: E402

import schgen  # noqa: E402
from design import d  # noqa: E402

lib = {s.entryName: s for s in SymbolLib.from_file(str(ROOT / "hardware/lib/hwlab.kicad_sym")).symbols}
sch = Schematic.create_new()
sch.uuid = d.root
sch.version = 20260306
sch.generator = "eeschema"


def inst(ref):
    return [SymbolProjectInstance(name=d.name, paths=[SymbolProjectPath(sheetInstancePath=f"/{d.root}", reference=ref, unit=1)])]


def place(libname, ref, x, y, angle, key, value=None):
    ls = lib[libname]
    s = SchematicSymbol(libraryNickname="hwlab", entryName=libname, position=Position(x, y, angle),
                        unit=1, inBom=True, onBoard=True, uuid=schgen.uid(*key))
    for p in ls.properties:
        if p.key.startswith("ki_"):
            continue
        v = ref if p.key == "Reference" else (value if (p.key == "Value" and value) else p.value)
        s.properties.append(Property(key=p.key, value=v, id=p.id,
                                     position=Position(x + p.position.X, y - p.position.Y, p.position.angle),
                                     effects=p.effects))
    s.instances = inst(ref)
    for u in ls.units:
        for pin in u.pins:
            s.pins[pin.number] = schgen.uid("pin", ref, pin.number)
    sch.schematicSymbols.append(s)


used = set()
for ref, part in sorted(d.parts.items()):
    used.add(part.sym.name)
    place(part.sym.name, ref, *part.at, part.rotation, ("sym", ref))
    seen = set()
    for pin in part.sym.pins:
        pt = d.pin_point(part, pin)
        if pt in seen:
            continue
        seen.add(pt)
        net = next((part.nets[q.number] for q in part.sym.pins if d.pin_point(part, q) == pt and q.number in part.nets), None)
        if net is None:
            if pin.etype != "no_connect" and not part.sym.power:
                sch.noConnects.append(NoConnect(position=Position(*pt), uuid=schgen.uid("nc", ref, pin.number)))
            continue
        ang = d.pin_out_angle(part, pin)
        dx, dy = schgen.DIRS[ang]
        end = (round(pt[0] + dx * schgen.STUB, 4), round(pt[1] + dy * schgen.STUB, 4))
        sch.graphicalItems.append(Connection(type="wire", points=[Position(*pt), Position(*end)],
                                             stroke=Stroke(width=0, type="default"), uuid=schgen.uid("wire", ref, pin.number)))
        if net in schgen.POWER_NETS:
            used.add(net)
            body = d.lib[net].pins[0].angle
            pref = f"#PWR{int(schgen.uid('pwrref', ref, pin.number).replace('-', ''), 16) % 10**5:05d}"
            place(net, pref, *end, (ang - body) % 360, ("pwr", ref, pin.number), value=net)
        else:
            just = "left" if ang in (0, 90) else "right"
            sch.labels.append(LocalLabel(text=net, position=Position(*end, ang),
                                         effects=Effects(font=Font(height=1.27, width=1.27), justify=Justify(horizontally=just, vertically="bottom")),
                                         uuid=schgen.uid("label", ref, pin.number)))

for name in sorted(used):
    s = lib[name]
    s.libId = f"hwlab:{name}"
    sch.libSymbols.append(s)

out = Path(__file__).with_name("hwlab.kicad_sch")
sch.to_file(str(out))
print("wrote", out.relative_to(ROOT), sum(1 for _ in open(out)), "lines")
