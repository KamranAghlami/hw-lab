#!/usr/bin/env python3
"""Build the project-local KiCad library from hardware/lib/parts.toml.

Upstream items (symbols, footprints, STEP models) are fetched from the official
KiCad libraries on GitLab at the pinned tag into hardware/lib/.cache/ (gitignored),
then turned into committed, project-local outputs:

  hardware/lib/hwlab.kicad_sym   atomic symbols with Value/Footprint/MPN/LCSC baked in
  hardware/lib/hwlab.pretty/     footprints, 3D model path -> ${KIPRJMOD}/lib/3dmodels
  hardware/lib/3dmodels/         STEP models

Usage: tools/build_lib.py [--offline]
"""
from __future__ import annotations

import argparse
import copy
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kisexpr as k  # noqa: E402
from kisexpr import S, Sym  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hardware" / "lib"
CACHE = LIB / ".cache"
LIBNAME = "hwlab"
MISSING_MODELS: list[str] = []
RAW = "https://gitlab.com/kicad/libraries/{repo}/-/raw/{tag}/{path}"


def fetch(repo: str, path: str, tag: str, offline: bool) -> Path:
    dst = CACHE / tag / repo / path
    if dst.exists():
        return dst
    if offline:
        raise SystemExit(f"missing in cache (offline): {repo}/{path}")
    url = RAW.format(repo=repo, tag=tag, path=urllib.request.quote(path))
    print(f"  fetch {repo}/{path}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r:
        dst.write_bytes(r.read())
    return dst


def upstream_symbol(lib_id: str, tag: str, offline: bool) -> list:
    """Return a flattened (no `extends`) copy of an upstream symbol."""
    lib, name = lib_id.split(":")
    tree = k.load(fetch("kicad-symbols", f"{lib}.kicad_symdir/{name}.kicad_sym", tag, offline))
    sym = k.find(tree, "symbol")
    ext = k.find(sym, "extends")
    if ext is None:
        return sym
    parent = copy.deepcopy(upstream_symbol(f"{lib}:{ext[1]}", tag, offline))
    rename(parent, name)
    # child overrides parent's properties; anything else in the child (flags) too
    for node in k.children(sym):
        h = k.head(node)
        if h == "extends":
            continue
        if h == "property":
            old = k.get_prop(parent, node[1])
            if old is not None:
                parent[parent.index(old)] = node
            else:
                insert_property(parent, node)
        else:
            old = k.find(parent, h)
            if old is not None and h not in ("symbol",):
                parent[parent.index(old)] = node
    return parent


def rename(sym: list, new: str) -> None:
    old = str(sym[1])
    sym[1] = new
    for sub in k.children(sym, "symbol"):
        if str(sub[1]).startswith(old + "_"):
            sub[1] = new + str(sub[1])[len(old):]


def insert_property(sym: list, prop: list) -> None:
    props = list(k.children(sym, "property"))
    idx = sym.index(props[-1]) + 1 if props else 2
    sym.insert(idx, prop)


def hidden_prop(key: str, value: str) -> list:
    return S("property", key, value,
             S("at", 0, 0, 0), S("show_name", Sym("no")), S("do_not_autoplace", Sym("no")),
             S("hide", Sym("yes")), S("effects", S("font", S("size", 1.27, 1.27))))


def set_prop(sym: list, key: str, value: str) -> None:
    p = k.get_prop(sym, key)
    if p is None:
        insert_property(sym, hidden_prop(key, value))
    else:
        p[2] = value


def build_part(part: dict, tag: str, offline: bool) -> list:
    sym = copy.deepcopy(upstream_symbol(part["symbol"], tag, offline))
    rename(sym, part["name"])
    fp_name = part["footprint"].split(":")[1]
    set_prop(sym, "Value", part.get("value", part["mpn"]))
    set_prop(sym, "Footprint", f"{LIBNAME}:{fp_name}")
    if "datasheet" in part:
        set_prop(sym, "Datasheet", part["datasheet"])
    if "description" in part:
        set_prop(sym, "Description", part["description"])
    for key, field in (("manufacturer", "Manufacturer"), ("mpn", "MPN"), ("lcsc", "LCSC")):
        set_prop(sym, field, part[key])
    k.remove(sym, lambda n: k.head(n) == "property" and n[1] == "ki_fp_filters")
    for num, newname in part.get("pin_names", {}).items():
        for pin in k.walk(sym):
            if k.head(pin) == "pin" and k.find(pin, "number")[1] == num:
                k.find(pin, "name")[1] = newname
    return sym


def build_footprint(lib_id: str, tag: str, offline: bool) -> tuple[str, list, list[Path]]:
    lib, name = lib_id.split(":")
    tree = k.load(fetch("kicad-footprints", f"{lib}.pretty/{name}.kicad_mod", tag, offline))
    models = []
    for m in k.find_all(tree, "model"):
        path = str(m[1])
        rel = path.split("}/", 1)[1]  # e.g. RF_Module.3dshapes/X.step
        rel = rel.rsplit(".", 1)[0] + ".step"
        local = LIB / "3dmodels-extra" / Path(rel).name  # hand-sourced models win
        if local.exists():
            models.append(local)
        else:
            try:
                models.append(fetch("kicad-packages3D", rel, tag, offline))
            except urllib.error.HTTPError as e:
                print(f"  WARNING: upstream 3D model missing ({e.code}): {rel}")
                MISSING_MODELS.append(rel)
        m[1] = "${KIPRJMOD}/lib/3dmodels/" + Path(rel).name
    return name, tree, models


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use cache only")
    args = ap.parse_args()
    cfg = tomllib.loads((LIB / "parts.toml").read_text())
    tag = cfg["upstream"]["tag"]

    symbols = []
    for pw in cfg.get("power", []):
        symbols.append(copy.deepcopy(upstream_symbol(pw["symbol"], tag, args.offline)))
    seen_fp: dict[str, str] = {}
    pretty = LIB / f"{LIBNAME}.pretty"
    models_dir = LIB / "3dmodels"
    pretty.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    for part in cfg["part"]:
        symbols.append(build_part(part, tag, args.offline))
        if part["footprint"] in seen_fp:
            continue
        name, tree, models = build_footprint(part["footprint"], tag, args.offline)
        seen_fp[part["footprint"]] = name
        k.dump(tree, pretty / f"{name}.kicad_mod")
        for mp in models:
            (models_dir / mp.name).write_bytes(mp.read_bytes())

    out = S("kicad_symbol_lib", S("version", 20251024), S("generator", "kicad_symbol_editor"),
            S("generator_version", "10.0"), *symbols)
    k.dump(out, LIB / f"{LIBNAME}.kicad_sym")
    if MISSING_MODELS:
        print("missing 3D models (put a STEP in lib/3dmodels-extra/):", *MISSING_MODELS, sep="\n  ")
    print(f"{len(symbols)} symbols, {len(seen_fp)} footprints -> {LIB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
