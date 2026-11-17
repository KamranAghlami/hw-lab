# hw-lab — project guide for agents

Test bed for agentic hardware development: the agent writes the design as text,
GitHub Actions builds and checks everything, the owner places and routes in the
KiCad GUI. Findings go to `docs/findings.md`; the real target (a vehicle tracker)
is built later in another repo using what is learned here.

## Hard rules

- **No KiCad or Docker on the dev machine.** It is 1 vCPU / 2 GB and runs live
  services. All KiCad work runs in CI (`kicad/kicad:10.0.8`). For ad-hoc KiCad
  experiments use the probe workflow (below).
- **Python only in `./venv`** (`python3 -m venv venv`). Never touch system Python.
- **KiCad version is pinned to 10.0.8** to match the owner's desktop. Change it
  only with the owner's say-so, and change image tag + library tag together.
- **All libraries are project-local** (`lib/`). Every BOM part carries `MPN` and
  `LCSC` fields.
- Project docs and memory live in `docs/` (memory index: `docs/memory/MEMORY.md`).

## Layout and workflow

See `docs/findings.md` (§ "Recommended repo layout") for the annotated tree. In short:

- Schematic: edit `hardware/design.py`, run `./venv/bin/python hardware/design.py`, commit the
  generated `hardware/hwlab.kicad_sch` (CI fails if it is stale). Never hand-edit the `.kicad_sch`.
- Parts: add to `hardware/lib/parts.toml` (MPN, LCSC verified, datasheet_pins, decap), then
  `./venv/bin/python tools/build_lib.py`.
- PCB: human-owned (KiCad GUI). Agent edits go through `tools/kisexpr.py` and are always followed
  by DRC in CI. `tools/pcb_sync.py` = headless "Update PCB from Schematic" (runs in CI only).
- PCB fixers (pcbnew, CI only): `gnd_fanout.py` (stranded top-pour GND pads → track/via),
  `fix_labels.py` (designators off pads), `stitch_gnd.py`. Never waive `unconnected_items` on a
  pour without listing the pads on the fragment: it may be a real open.
- Part requirements live in `parts.toml` (`datasheet_pins`, `decap`, `pull`, `forbid_net`) and are
  checked by `intent_check.py`. When a review catches something no gate did, add a rule there.
- Gates (hardware.yml): regen, `sch_overlap.py`, ERC + `waivers.toml`, `pinmap.py`,
  `intent_check.py`, DRC + `hwlab.kicad_dru`, `layout_check.py --gate`.
- Release: push a `hw-vX.Y` tag.

## Common commands

```sh
# remote KiCad sandbox: runs ci/probe/<name>.sh in the KiCad image, uploads ./out
gh workflow run probe.yml -f script=<name>
gh run watch <id>; gh run download <id> -D build/<name>
```
