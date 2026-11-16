---
name: kicad10-gotchas
description: Non-obvious KiCad 10.0.8 / KiBot / Freerouting behaviours that cost time in hw-lab
metadata:
  type: reference
---

- Netlist (`kicad-cli sch export netlist --format kicadsexpr`): `pinfunction` is `NAME_PINNUMBER` (e.g. `IO0_27`); nets from local labels are prefixed `/` (`/I2C_SDA`), power nets are not.
- `kicad-cli sch upgrade --force` is a usable headless "GUI save" for diffing, but it drops the trailing `(embedded_fonts no)`; the GUI keeps it (writer code path).
- KiCad saves schematic items sorted by type then UUID -> deterministic UUIDs = stable file order + stable PCB links.
- No CLI for "Update PCB from Schematic": use `tools/pcb_sync.py` (pcbnew API). New footprint fields must be hidden/moved to Fab explicitly or they print on silk.
- DRC never enforces net-class track width; a `.kicad_dru` rule with `(severity error)` is needed.
- Text edits to copper don't refill pours: run DRC with `--refill-zones` and KiBot `fill_zones` preflight.
- KiBot 1.9.1: `pip install --no-compile`, and add `lxml numpy svgwrite mistune` or plugins fail to import.
- Freerouting >= 2.5 needs Java 25; Debian 13 image has Java 21 -> pin v2.1.0.
- Upstream 10.0.8 3D library lacks `USB_C_Receptacle_HRO_TYPE-C-31-M-12.step` and `SW_Push_1P1T_XKB_TS-1187A.step`.
- ESP32-S3-WROOM-1 footprint courtyard is 48 mm wide (antenna clearance): nothing can sit beside the module.
- GHCR image names must be lowercase (`github.repository_owner` is not).
- kiutils 1.4.8 silently drops KiCad 8-10 tokens incl. `(hide yes)` -> do not use it to write KiCad 10 files.

**Why:** each of these broke a CI run or produced a wrong board in hw-lab.
**How to apply:** check this list before debugging similar failures in the tracker repo. Related: [[owner-decisions]], [[dev-machine]].
