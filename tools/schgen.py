"""Approach A: generate a KiCad 10 schematic from a netlist-level Python design,
writing S-expressions directly (via tools/kisexpr.py).

Design model: parts placed at grid coordinates, pins assigned to nets by pin
name or number. Each connected pin gets a short wire stub ending in a net
label (signals) or a power symbol (power nets); unconnected pins get a
no-connect flag. No wires between parts, so placement never causes shorts.

Everything is deterministic: UUIDs are uuid5 of stable keys (reference, pin),
so regenerating an unchanged design produces a byte-identical file, and the
PCB's links to schematic symbols (by UUID path) survive regeneration.
"""
from __future__ import annotations

import copy
import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import kisexpr as k
from kisexpr import S, Sym

GRID = 1.27
STUB = 2.54
POWER_NETS = {"GND", "+3V3", "VBUS"}
NS = uuid.UUID("6f1c3c52-1d3e-4a4e-9a51-6b8f0e7c2a11")


def uid(*key) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, key))))


def snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


def rot(px: float, py: float, deg: int) -> tuple[float, float]:
    r = math.radians(deg)
    return (round(px * math.cos(r) - py * math.sin(r), 4), round(px * math.sin(r) + py * math.cos(r), 4))


DIRS = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}  # visual angle -> sheet (dx, dy)


@dataclass
class Pin:
    number: str
    name: str
    etype: str
    x: float  # lib coords (y up)
    y: float
    angle: int
    hidden: bool


@dataclass
class LibSym:
    name: str
    node: list
    pins: list[Pin]
    power: bool

    @classmethod
    def from_node(cls, node: list) -> "LibSym":
        pins = []
        for p in k.walk(node):
            if k.head(p) == "pin":
                at = k.find(p, "at")
                pins.append(Pin(str(k.find(p, "number")[1]), str(k.find(p, "name")[1]), str(p[1]),
                                float(at[1]), float(at[2]), int(float(at[3])), k.find(p, "hide") is not None))
        return cls(str(node[1]), node, pins, k.find(node, "power") is not None)


class Library:
    def __init__(self, path: Path, nickname: str):
        self.nickname = nickname
        tree = k.load(path)
        self.syms = {str(s[1]): LibSym.from_node(s) for s in k.children(tree, "symbol")}

    def __getitem__(self, name: str) -> LibSym:
        return self.syms[name]


@dataclass
class Part:
    ref: str
    sym: LibSym
    at: tuple[float, float]
    nets: dict[str, str] = field(default_factory=dict)  # pin number -> net
    rotation: int = 0

    def pins_named(self, key: str) -> list[Pin]:
        hit = [p for p in self.sym.pins if p.number == key]
        return hit or [p for p in self.sym.pins if p.name == key]


class Design:
    def __init__(self, name: str, lib: Library, title: str = "", rev: str = "", company: str = "",
                 paper: str = "A4"):
        self.name, self.lib, self.title, self.rev, self.company, self.paper = name, lib, title, rev, company, paper
        self.parts: dict[str, Part] = {}
        self.root = uid("root", name)
        self._pwr = 0

    # -- authoring API ---------------------------------------------------------
    def part(self, ref: str, symbol: str, at: tuple[float, float], **conn: str) -> Part:
        """Place `symbol` as `ref` at (x, y) mm; kwargs map pin name/number -> net."""
        if ref in self.parts:
            raise ValueError(f"duplicate reference {ref}")
        p = Part(ref, self.lib[symbol], (snap(at[0]), snap(at[1])))
        self.parts[ref] = p
        self.connect(ref, **conn)
        return p

    def connect(self, ref: str, mapping: dict[str, str] | None = None, **conn: str) -> None:
        part = self.parts[ref]
        for key, net in {**(mapping or {}), **conn}.items():
            key = key.replace("__", "+") if key.endswith("__") else key
            pins = part.pins_named(key)
            if not pins:
                raise KeyError(f"{ref}: no pin {key!r} in {part.sym.name}")
            for p in pins:
                part.nets[p.number] = net

    def nets(self) -> dict[str, list[tuple[str, str]]]:
        out: dict[str, list[tuple[str, str]]] = {}
        for ref, part in self.parts.items():
            for num, net in part.nets.items():
                out.setdefault(net, []).append((ref, num))
        return out

    # -- geometry ---------------------------------------------------------------
    @staticmethod
    def pin_point(part: Part, pin: Pin) -> tuple[float, float]:
        rx, ry = rot(pin.x, pin.y, part.rotation)
        return (round(part.at[0] + rx, 4), round(part.at[1] - ry, 4))

    @staticmethod
    def pin_out_angle(part: Part, pin: Pin) -> int:
        return (pin.angle + 180 + part.rotation) % 360

    # -- emit -------------------------------------------------------------------
    def build(self) -> list:
        items: list[tuple[int, str, list]] = []  # (type order, uuid, node)
        used: dict[str, LibSym] = {}
        for ref, part in sorted(self.parts.items()):
            used[part.sym.name] = part.sym
            items.append((ORDER["symbol"], uid("sym", ref), self._symbol(part, ref)))
            # 1) one entry per distinct connection point (stacked pins collapse)
            points: dict[tuple[float, float], tuple[Pin, str | None]] = {}
            for pin in part.sym.pins:
                pt = self.pin_point(part, pin)
                net = part.nets.get(pin.number)
                if pt not in points or (points[pt][1] is None and net):
                    points[pt] = (pin, net)
            # 2) runs of adjacent pins (same side, 2.54 pitch) on the same power net
            runs: dict[tuple[float, float], list] = {}
            by_side: dict[tuple, list] = {}
            for pt, (pin, net) in points.items():
                if net in POWER_NETS:
                    d = self.pin_out_angle(part, pin)
                    line = pt[0] if d in (0, 180) else pt[1]
                    by_side.setdefault((d, line, net), []).append(pt)
            for (d, _, net), pts in by_side.items():
                along = 1 if d in (0, 180) else 0
                pts.sort(key=lambda p: p[along])
                run = [pts[0]]
                for p in pts[1:]:
                    if abs(p[along] - run[-1][along] - STUB) < 1e-6:
                        run.append(p)
                    else:
                        runs[run[0]] = run
                        run = [p]
                runs[run[0]] = run
            members = {p: r for r in runs.values() for p in r}
            # 3) emit
            for pt, (pin, net) in sorted(points.items()):
                key = (ref, pin.number)
                if net is None:
                    if pin.etype != "no_connect" and not part.sym.power:
                        items.append((ORDER["no_connect"], uid("nc", *key),
                                      S("no_connect", S("at", *pt), S("uuid", uid("nc", *key)))))
                    continue
                d = self.pin_out_angle(part, pin)
                dx, dy = DIRS[d]
                stub = STUB
                run = members.get(pt)
                if net in POWER_NETS and d in (0, 180) and run and len(run) == 1:
                    # stagger lone sideways power symbols so neighbours don't overlap
                    stub = STUB if round(pt[1] / STUB) % 2 == 0 else 3 * STUB
                end = (round(pt[0] + dx * stub, 4), round(pt[1] + dy * stub, 4))
                items.append(self._wire(pt, end, ("wire", *key)))
                if net not in POWER_NETS:
                    items.append((ORDER["label"], uid("label", *key), self._label(net, end, d, key)))
                    continue
                used[net] = self.lib[net]
                if len(run) == 1:
                    items.append((ORDER["symbol"], uid("pwr", *key), self._power(net, end, d, key)))
                    continue
                if pt != run[0]:
                    continue  # the run is drawn once, from its first pin
                ends = [(round(p[0] + dx * STUB, 4), round(p[1] + dy * STUB, 4)) for p in run]
                for a, b in zip(ends, ends[1:]):
                    items.append(self._wire(a, b, ("join", ref, *a)))
                for e in ends[1:-1]:
                    items.append((ORDER["junction"], uid("junction", ref, *e), S(
                        "junction", S("at", *e), S("diameter", 0), S("color", 0, 0, 0, 0),
                        S("uuid", uid("junction", ref, *e)))))
                if d in (0, 180):  # vertical bar: hang the symbol off its top/bottom, upright
                    body = self.lib[net].pins[0].angle
                    tip = ends[-1] if body == 270 else ends[0]
                    sgn = 1 if body == 270 else -1
                    p2 = (tip[0], round(tip[1] + sgn * STUB, 4))
                    items.append(self._wire(tip, p2, ("tail", ref, *tip)))
                    items.append((ORDER["symbol"], uid("pwr", *key), self._power(net, p2, body, key)))
                else:
                    items.append((ORDER["symbol"], uid("pwr", *key), self._power(net, ends[0], d, key)))
        items.sort(key=lambda t: (t[0], t[1]))
        lib_symbols = [self._lib_symbol(s) for _, s in sorted(used.items())]
        title = S("title_block")
        if self.title:
            title.append(S("title", self.title))
        if self.rev:
            title.append(S("rev", self.rev))
        if self.company:
            title.append(S("company", self.company))
        return S("kicad_sch", S("version", 20260306), S("generator", "eeschema"),
                 S("generator_version", "10.0"), S("uuid", self.root), S("paper", self.paper), title,
                 S("lib_symbols", *lib_symbols), *[n for _, _, n in items],
                 S("sheet_instances", S("path", "/", S("page", "1"))), S("embedded_fonts", Sym("no")))

    def write(self, path: Path) -> None:
        k.dump(self.build(), path)

    # -- node builders ------------------------------------------------------------
    def _lib_symbol(self, sym: LibSym) -> list:
        node = copy.deepcopy(sym.node)
        node[1] = f"{self.lib.nickname}:{sym.name}"
        return node

    def _fields(self, sym: LibSym, at: tuple[float, float], values: dict[str, str], vertical_2pin: bool) -> list:
        out = []
        for prop in k.children(sym.node, "property"):
            key = str(prop[1])
            if key.startswith("ki_"):
                continue
            pat = k.find(prop, "at")
            px, py, pa = float(pat[1]), float(pat[2]), float(pat[3])
            fx, fy, fa = at[0] + px, at[1] - py, pa
            eff = copy.deepcopy(k.find(prop, "effects"))
            if vertical_2pin and key in ("Reference", "Value"):
                fx, fy, fa = at[0] + 2.54, at[1] + (-1.27 if key == "Reference" else 1.27), 0
                eff = S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Sym("left")))
            node = S("property", values.get(key, prop[2]), S("at", round(fx, 4), round(fy, 4), fa))
            node.insert(1, key)
            if k.find(prop, "hide") is not None:
                node.append(S("hide", Sym("yes")))
            node += [S("show_name", Sym("no")), S("do_not_autoplace", Sym("no")), eff]
            out.append(node)
        return out

    def _instances(self, ref: str) -> list:
        return S("instances", S("project", self.name, S("path", f"/{self.root}", S("reference", ref), S("unit", 1))))

    def _symbol(self, part: Part, ref: str) -> list:
        sym = part.sym
        vertical = len(sym.pins) == 2 and all(p.x == 0 for p in sym.pins)
        node = S("symbol", S("lib_id", f"{self.lib.nickname}:{sym.name}"), S("at", *part.at, part.rotation),
                 S("unit", 1), S("body_style", 1), S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")),
                 S("on_board", Sym("yes")), S("in_pos_files", Sym("yes")), S("dnp", Sym("no")),
                 S("uuid", uid("sym", ref)))
        node += self._fields(sym, part.at, {"Reference": ref}, vertical)
        for p in sym.pins:
            node.append(S("pin", p.number, S("uuid", uid("pin", ref, p.number))))
        node.append(self._instances(ref))
        return node

    def _power(self, net: str, at: tuple[float, float], out_angle: int, key) -> list:
        sym = self.lib[net]
        body = sym.pins[0].angle  # direction the body extends from the pin
        r = (out_angle - body) % 360
        self._pwr += 1
        ref = f"#PWR{int(uid('pwrref', *key).replace('-', ''), 16) % 10**5:05d}"
        node = S("symbol", S("lib_id", f"{self.lib.nickname}:{net}"), S("at", *at, r),
                 S("unit", 1), S("body_style", 1), S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")),
                 S("on_board", Sym("yes")), S("in_pos_files", Sym("yes")), S("dnp", Sym("no")),
                 S("uuid", uid("pwr", *key)))
        node += self._fields(sym, at, {"Reference": ref, "Value": net}, False)
        node.append(S("pin", "1", S("uuid", uid("pwrpin", *key))))
        node.append(self._instances(ref))
        return node

    @staticmethod
    def _wire(a, b, key) -> tuple[int, str, list]:
        u = uid(*key)
        return (ORDER["wire"], u, S("wire", S("pts", S("xy", *a), S("xy", *b)),
                                    S("stroke", S("width", 0), S("type", Sym("default"))), S("uuid", u)))

    @staticmethod
    def _label(net: str, at: tuple[float, float], out_angle: int, key) -> list:
        just = "left" if out_angle in (0, 90) else "right"
        return S("label", net, S("at", *at, out_angle),
                 S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Sym(just), Sym("bottom"))),
                 S("uuid", uid("label", *key)))


# KiCad saves items sorted by KICAD_T type, then UUID (typeinfo.h order)
ORDER = {"junction": 1, "no_connect": 2, "wire": 5, "label": 12, "symbol": 17}
