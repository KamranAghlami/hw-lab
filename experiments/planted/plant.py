#!/usr/bin/env python3
"""Plant one known mistake into a copy of the project, then run the CI gates on it.

    plant.py <variant> <outdir>      (runs in the CI image: needs kicad-cli + pcbnew)

Variants (the brief's list) + a clean control:
  control        nothing changed
  swap_txrx      ESP32 TXD0/RXD0 nets swapped (UART_TX <-> UART_RX)
  missing_decap  IMU decoupling caps C5, C6 removed (schematic + PCB)
  wrong_pinout   AMS1117 symbol pin numbers for VI/VO swapped (lib error, as from a bad import)
  floating_pin   IMU CS (I2C/SPI mode select) left unconnected
  narrow_vbus    VBUS tracks routed at 0.15 mm
Writes <outdir>/result.json with what each gate said.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))


def sh(*cmd, cwd=None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def load_design(hw: Path):
    spec = importlib.util.spec_from_file_location("design_variant", hw / "design.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.d


def main() -> None:
    variant, out = sys.argv[1], Path(sys.argv[2]).resolve()
    hw = out / "hardware"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "hardware", hw, ignore=shutil.ignore_patterns(".cache"))
    (out / "firmware").mkdir()
    shutil.copytree(ROOT / "firmware/include", out / "firmware/include")

    if variant == "wrong_pinout":
        lib = hw / "lib/hwlab.kicad_sym"
        txt = lib.read_text()
        start = txt.index('(symbol "AMS1117-3.3"')
        end = txt.index('\n\t(symbol "', start + 10)
        block = txt[start:end]
        block = block.replace('(number "2"', '(number "@3"').replace('(number "3"', '(number "2"').replace('(number "@3"', '(number "3"')
        lib.write_text(txt[:start] + block + txt[end:])

    d = load_design(hw)
    if variant == "swap_txrx":
        u1 = d.parts["U1"]
        u1.nets["37"], u1.nets["36"] = "UART_RX", "UART_TX"
    elif variant == "missing_decap":
        del d.parts["C5"], d.parts["C6"]
    elif variant == "floating_pin":
        del d.parts["U3"].nets["12"]
    d.write(hw / "hwlab.kicad_sch")

    sch, pcb = hw / "hwlab.kicad_sch", hw / "hwlab.kicad_pcb"
    net = out / "hwlab.net"
    sh("kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", str(net), str(sch))
    rc, log = sh("python3", str(ROOT / "tools/pcb_sync.py"), str(net), str(pcb))
    print(log)
    if variant == "narrow_vbus":
        import pcbnew
        b = pcbnew.LoadBoard(str(pcb))
        n = 0
        for t in b.GetTracks():
            if t.GetNetname() == "VBUS" and t.GetClass() == "PCB_TRACK":
                t.SetWidth(pcbnew.FromMM(0.15))
                n += 1
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        pcbnew.SaveBoard(str(pcb), b)
        print(f"narrowed {n} VBUS track segments to 0.15 mm")

    res: dict = {"variant": variant}
    sh("kicad-cli", "sch", "erc", "--severity-all", "--format", "json", "-o", str(out / "erc.json"), str(sch))
    rc, log = sh("python3", str(ROOT / "tools/check_report.py"), "erc", str(out / "erc.json"),
                 "--waivers", str(hw / "waivers.toml"))
    res["erc"] = {"fail": rc != 0, "report": log.strip()}
    rc, log = sh("python3", str(ROOT / "tools/pinmap.py"), "check", str(net), str(out / "firmware/include/board_pins.h"))
    res["pinmap"] = {"fail": rc != 0, "report": log.strip()}
    rc, log = sh("python3", str(ROOT / "tools/intent_check.py"), str(net), "--parts", str(hw / "lib/parts.toml"),
                 "--lib", str(hw / "lib"))
    res["intent"] = {"fail": rc != 0, "report": log.strip()}
    sh("kicad-cli", "pcb", "drc", "--severity-all", "--schematic-parity", "--format", "json",
       "-o", str(out / "drc.json"), str(pcb))
    rc, log = sh("python3", str(ROOT / "tools/check_report.py"), "drc", str(out / "drc.json"),
                 "--waivers", str(hw / "waivers.toml"), "--allow-warnings")
    res["drc"] = {"fail": rc != 0, "report": log.strip()}
    # same DRC without the custom rules file: does the net class alone catch anything?
    (hw / "hwlab.kicad_dru").rename(hw / "hwlab.kicad_dru.off")
    sh("kicad-cli", "pcb", "drc", "--severity-all", "--schematic-parity", "--format", "json",
       "-o", str(out / "drc-norules.json"), str(pcb))
    (hw / "hwlab.kicad_dru.off").rename(hw / "hwlab.kicad_dru")
    rc, log = sh("python3", str(ROOT / "tools/check_report.py"), "drc", str(out / "drc-norules.json"),
                 "--waivers", str(hw / "waivers.toml"), "--allow-warnings")
    res["drc_without_custom_rules"] = {"fail": rc != 0, "report": log.strip()}
    (out / "result.json").write_text(json.dumps(res, indent=2))

    # review material (what the agent reviewer gets): PDF, netlist, renders
    rv = out / "review"
    rv.mkdir()
    shutil.copy(net, rv / "hwlab.net")
    sh("kicad-cli", "sch", "export", "pdf", "-o", str(rv / "schematic.pdf"), str(sch))
    for side in ("top", "bottom"):
        sh("kicad-cli", "pcb", "render", "--side", side, "-w", "1200", "-h", "1600", "-o", str(rv / f"render-{side}.png"), str(pcb))
    sh("kicad-cli", "pcb", "export", "svg", "--layers", "F.Cu,B.Cu,F.SilkS,Edge.Cuts", "--mode-single",
       "--fit-page-to-board", "-o", str(rv / "copper.svg"), str(pcb))
    print(json.dumps({k: (v["fail"] if isinstance(v, dict) else v) for k, v in res.items()}))


if __name__ == "__main__":
    main()
