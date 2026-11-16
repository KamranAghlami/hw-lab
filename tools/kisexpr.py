"""Minimal KiCad S-expression toolkit (stdlib only).

- parse(text)  -> nested lists. Unquoted tokens become `Sym`, quoted strings `str`.
- dumps(tree)  -> text formatted exactly like KiCad 10 writes files
                  (port of KICAD_FORMAT::Prettify, common/io/kicad/kicad_io_utils.cpp @ 10.0.8).
- helpers to query/edit trees: find, find_all, get, set_prop ...

Numbers produced by Python code (int/float) are formatted the way KiCad does
(shortest representation, no trailing zeros, no "-0").
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Iterator


class Sym(str):
    """An unquoted token (keyword, number as written, yes/no...)."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Sym({str.__repr__(self)})"


# --------------------------------------------------------------------------- parse
_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)
_UNESC = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}


def _unescape(s: str) -> str:
    return re.sub(r"\\(.)", lambda m: _UNESC.get(m.group(1), m.group(1)), s)


def parse(text: str) -> list:
    stack: list[list] = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"bad sexpr at {pos}: {text[pos:pos+40]!r}")
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(_unescape(m.group(3)))
        elif m.group(4) is not None:
            stack[-1].append(Sym(m.group(4)))
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    root = stack[0]
    return root[0] if len(root) == 1 else root


def load(path) -> list:
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


# --------------------------------------------------------------------------- format
def fmt_num(v: float | int) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    if math.isnan(v) or math.isinf(v):
        raise ValueError(v)
    # KiCad writes up to 10 significant digits, then strips trailing zeros
    s = f"{round(v, 6):.6f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


def _quote(s: str) -> str:
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def _atom(a) -> str:
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, str):
        return _quote(a)
    if isinstance(a, (int, float)):
        return fmt_num(a)
    raise TypeError(f"cannot serialize {a!r}")


def compact(tree) -> str:
    if isinstance(tree, list):
        return "(" + " ".join(compact(x) for x in tree) + ")"
    return _atom(tree)


def prettify(src: str, compact_text_properties: bool = False) -> str:
    """Faithful port of KICAD_FORMAT::Prettify (KiCad 10.0.8)."""
    quote_char = '"'
    indent = "\t"
    xy_limit = 99
    wrap_threshold = 72

    out: list[str] = []
    out_len_nonempty = False
    list_depth = 0
    last_nws = ""
    in_quote = False
    has_space = False
    in_multiline = False
    in_xy = False
    in_short = False
    short_depth = 0
    column = 0
    backslashes = 0
    n = len(src)
    ws = " \t\n\r"

    def next_nws(i: int) -> str:
        while i < n and src[i] in ws:
            i += 1
        return src[i] if i < n else ""

    def is_xy(i: int) -> bool:
        return src[i + 1 : i + 4] == "xy "

    def is_short(i: int) -> bool:
        j = i + 1
        tok = []
        while j < n and src[j].isalpha():
            tok.append(src[j])
            j += 1
        return "".join(tok) in ("font", "stroke", "fill", "teardrop", "offset", "rotate", "scale")

    i = 0
    while i < n:
        c = src[i]
        nxt = next_nws(i)
        if c in ws and not in_quote:
            if not has_space and list_depth > 0 and last_nws != "(" and nxt != ")" and nxt != "(":
                if in_xy or column < wrap_threshold:
                    out.append(" ")
                    column += 1
                elif in_short:
                    out.append(" ")
                else:
                    out.append("\n" + indent * list_depth)
                    column = list_depth
                    in_multiline = True
                has_space = True
        else:
            has_space = False
            if c == "(" and not in_quote:
                cur_xy = is_xy(i)
                cur_short = compact_text_properties and is_short(i)
                if not out_len_nonempty:
                    out.append("(")
                    out_len_nonempty = True
                    column += 1
                elif in_xy and cur_xy and column < xy_limit:
                    out.append(" (")
                    column += 2
                elif in_short:
                    out.append(" (")
                    column += 2
                else:
                    out.append("\n" + indent * list_depth + "(")
                    column = list_depth + 1
                in_xy = cur_xy
                if cur_short:
                    in_short = True
                    short_depth = list_depth
                list_depth += 1
            elif c == ")" and not in_quote:
                if list_depth > 0:
                    list_depth -= 1
                if in_short:
                    out.append(")")
                    column += 1
                elif last_nws == ")" or in_multiline:
                    out.append("\n" + indent * list_depth + ")")
                    column = list_depth + 1
                    in_multiline = False
                else:
                    out.append(")")
                    column += 1
                if short_depth == list_depth:
                    in_short = False
                    short_depth = 0
            else:
                if c == "\\":
                    backslashes += 1
                elif c == quote_char and (backslashes & 1) == 0:
                    in_quote = not in_quote
                if c != "\\":
                    backslashes = 0
                out.append(c)
                column += 1
            last_nws = c
        i += 1
    out.append("\n")
    return "".join(out)


def dumps(tree, compact_text_properties: bool = False) -> str:
    return prettify(compact(tree), compact_text_properties)


def dump(tree, path, **kw) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(tree, **kw))


# --------------------------------------------------------------------------- query/edit
def head(node) -> str | None:
    return str(node[0]) if isinstance(node, list) and node and isinstance(node[0], Sym) else None


def children(node, name: str | None = None) -> Iterator[list]:
    for x in node[1:] if isinstance(node, list) else ():
        if isinstance(x, list) and (name is None or head(x) == name):
            yield x


def find(node, name: str):
    return next(children(node, name), None)


def find_all(node, name: str) -> list:
    return list(children(node, name))


def walk(node) -> Iterator[list]:
    if isinstance(node, list):
        yield node
        for x in node:
            yield from walk(x)


def get_prop(sym, key: str):
    for p in children(sym, "property"):
        if p[1] == key:
            return p
    return None


def remove(node, pred) -> int:
    before = len(node)
    node[:] = [x for x in node if not (isinstance(x, list) and pred(x))]
    return before - len(node)


def S(*items) -> list:
    """Build a node; first item (keyword) becomes a Sym, str stays quoted."""
    first, *rest = items
    return [Sym(first), *rest]


def yes(flag: bool) -> Sym:
    return Sym("yes" if flag else "no")


def iter_atoms(node) -> Iterable:
    for x in walk(node):
        for a in x:
            if not isinstance(a, list):
                yield a
