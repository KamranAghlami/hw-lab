# hw-lab findings

Test bed for agentic hardware development: the agent writes the design as text, GitHub
Actions builds and checks everything, the owner places and routes in the KiCad GUI.
KiCad **10.0.8** everywhere (CI image `kicad/kicad:10.0.8`, owner's desktop, library tag).
All numbers below come from runs in this repo (`gh run view <id>`) unless stated.

## TL;DR

- **Schematic:** write it with a small Python generator that emits KiCad S-expressions directly
  (`tools/schgen.py` + `tools/kisexpr.py`). It opens cleanly, passes ERC, and KiCad re-saves it with
  a 1-line diff. kiutils corrupts KiCad 10 files; SKiDL's schematic drawing is not usable; atopile
  doesn't make schematics.
- **Gates that work (layered):** regen check → overlap lint → ERC → pin map → design-intent check →
  DRC with custom rules. Each layer catches something the others can't (table in §4).
- **The planted mistakes:** every one was caught by some automated gate *before layout*, except the
  narrow power trace, which DRC catches at layout time **only** with a custom rule. Agent
  review of PDF/netlist/renders matched all 6 coded variants, but that review was not truly blind.
- **Round trip:** KiCad's own serializers and the agent's text tool are both canonical, so diffs
  stay readable (moving a part is a 1-line diff). Rule: the schematic is generated (humans don't
  edit it in the GUI); the PCB is human-owned (the agent edits it surgically and DRC checks the result).
- **CI:** ~1 min for checks + ~1.5 min for outputs, in parallel. The prebuilt image on GHCR is the
  cache; pulling it (~40–60 s per job) is now the dominant cost.
- **Agent layout (Q7):** a credit-card board (ID-1, rounded corners) from agent placement +
  Freerouting passes all gates; it misses USB pair routing and silk polish (§7).
- **Release:** `hw-v0.1` published with the full fab package (§6).
- **Not yet done:** a real GUI round trip by the owner (§2.3), a truly blind review (§4.2).

---

## 1. Writing the schematic

Same board, same placement, four ways (`experiments/`, probe runs 43861673306, 43863205799,
43862475783):

| | **A: raw S-expr generator** | **B: kiutils 1.4.8** | **C: SKiDL 3.0 + schematizer 0.2** | **D: atopile 0.15.9** |
|---|---|---|---|---|
| Opens in KiCad 10 | yes | yes | yes (writes KiCad 9 format `20250114`) | **no `.kicad_sch` at all**, only `.kicad_pcb` + per-part libs |
| ERC | 0 errors, 2 warnings (both reviewed and waived) | 0 errors, 2 warnings | **31 errors, 100 warnings** (29 pins without NC, 26 off-grid, 2 power pins not driven) | n/a |
| Diff after KiCad re-save | **1 line** (`kicad-cli` drops `(embedded_fonts no)`) | 15,281 lines | whole file (format upgrade) | n/a |
| Overlap lint (`tools/sch_overlap.py`) | 12 → **0** after layout fixes | 575 | 91 | n/a |
| Faithful to KiCad 10 | byte-identical parse→dump of KiCad's own files | **silently drops** `hide`, `do_not_autoplace`, `exclude_from_sim`, `in_pos_files`, `embedded_fonts`, `pin_numbers`, `body_style`, … → hidden Footprint/MPN/LCSC fields show on the sheet; reads `(show_name no)` as true | default mode fails (`RoutingFailure: UART_RX`); `auto_stub=True` works in 19 s on a CI runner; on the 1-vCPU dev box it was still running after 4 min of CPU when killed | CLI is in maintenance mode, replaced by the hosted app (0.16+); example build fails: package registry not resolvable |
| Netlist | KiCad | KiCad | **SKiDL's own netlist is good** | own |

**Recommendation: A.** The design is a netlist-level Python file (`hardware/design.py`: place
part, map pin → net). `schgen` draws a pin stub plus a net label (or power symbol) per pin.
Wires between parts never exist, so placement can't short anything. Things that made it work:

- **Atomic parts** (`hardware/lib/parts.toml` → `tools/build_lib.py`): one symbol per orderable
  part with Value, Footprint, MPN, Manufacturer and LCSC baked in, built from the official KiCad
  libraries at the pinned tag. The agent picks parts by name and never types a footprint or an
  LCSC number. Every LCSC number was checked against the JLCPCB parts API.
- **Deterministic UUIDs** (uuid5 of reference/pin) → regenerating gives a byte-identical file,
  KiCad's save order (type, then UUID) stays stable, and PCB footprints stay linked to their symbols.
- **A port of KiCad's prettifier** (`KICAD_FORMAT::Prettify`) → output formatted exactly as
  KiCad writes it.
- **Explicit no-connects** (`d.no_connect(ref, pins…)`). The first version auto-flagged every
  unused pin, which would have hidden a forgotten connection from ERC.
- **Collision guard**: generation fails if one part's stub/label lands on another part's
  connection point. KiCad would silently merge the two nets; it happened once in testing (R6/R7).
- **Overlap lint** as a CI gate: ERC checks connectivity, not legibility, and the owner reviews
  the PDF.

Known gap: the schematic is readable but plain (label-per-pin style, no hand-drawn wiring between
functional blocks). Fine for a 23-part board; a 60-part tracker will want hierarchical sheets.
`schgen` would need sheet support (not done).

## 2. Round trip (GUI ↔ text)

### 2.1 Measured, with KiCad's own serializer standing in for the GUI (probe `roundtrip`, runs 43868703463 / 43868909816)

| step | result |
|---|---|
| Re-save schematic (`kicad-cli sch upgrade --force`) | 1-line diff (trailing `(embedded_fonts no)`; the GUI writer keeps it) |
| Re-save PCB (`kicad-cli pcb upgrade --force`, `pcbnew` Load/Save) | **0-line diff** |
| Re-save project file | hand-written `.kicad_pcb`/`.kicad_pro` → KiCad expands the `.kicad_pro` once (+307/−42). Commit KiCad's version. |
| Agent's text tool (`kisexpr` parse → dump) on `.kicad_sch` and `.kicad_pcb` | byte-identical |
| Agent adds 2 parts via `design.py` + `tools/pcb_sync.py` | sch +404/−4, pcb +425/−1. The only removed line is the old `unconnected-(U1-IO39-Pad32)` net name; **existing placement and routing untouched**. New parts are parked off-board for the human to place. |
| Agent moves a footprint by text edit | 1-line diff, canonical (pcbnew re-save identical); DRC flags the now-dangling tracks |
| Agent widens all +3V3 tracks by text edit | 42-line diff; DRC: 16 clearance errors |
| Agent adds a GND via by text edit, blind | DRC failed the build: via on a +3V3 track (run 43867353102). Reverted. |
| Agent renames a routed net | inconclusive (ran on top of a corrupted step; not repeated) |

### 2.2 What breaks, and the rules that follow

1. **Schematic GUI edits are overwritten** by regeneration. Rule: `design.py` owns the schematic;
   CI fails if the committed `.kicad_sch` differs from the generator's output. If the owner
   wants to move symbols for readability, `schgen` would need to read positions back (not done).
2. **No CLI for "Update PCB from Schematic".** `tools/pcb_sync.py` does it with the pcbnew API:
   it adds/removes/swaps footprints, keeps positions, assigns nets, copies fields. The human path
   stays F8 in the GUI. Linking is by symbol UUID, which the generator keeps stable.
3. **pcbnew `SetField` isn't idempotent**: fields created through the API get a
   `(thickness 0.15)` line on the next save. Fixed by setting it explicitly.
4. **Text edits to copper don't refill pours.** DRC runs with `--refill-zones`; KiBot uses the
   `fill_zones` preflight.
5. **Agent edits to the PCB must be followed by DRC**, which catches all four text-edit
   breakages above. The PCB is the human's; the agent should prefer generating changes (schematic,
   rules) and leave copper to the GUI.

### 2.3 Still to do: the real GUI round trip
The owner opens the board in KiCad 10.0.8, moves parts, reroutes, saves, and pushes. Then the agent
edits text (adds a part, changes a rule), and we check the diffs and DRC again. Expected from
§2.1: GUI save diffs limited to what was edited.

## 3. CI

`.github/workflows/hardware.yml` (checks + outputs, path-filtered), `release.yml` (tags),
`ci-image.yml` (image), `planted.yml` (experiment), `probe.yml` (remote KiCad sandbox, because the
dev box can't run KiCad).

**checks job** (fails the build): schematic == generator output → overlap lint → ERC (errors
**and** warnings, semantic waivers in `hardware/waivers.toml`) → netlist → pin map → design
intent → DRC with `--schematic-parity --refill-zones` (errors; the important rules are raised to
error in `.kicad_pro`; custom rules in `hwlab.kicad_dru`).

**outputs job** (KiBot 1.9.1): schematic PDF, netlist, JLCPCB gerbers + drill zip, JLC BOM, JLC
CPL, interactive HTML BOM (with LCSC/MPN), orthographic top/bottom 3D PNGs, STEP, visual PCB and
schematic diffs against the previous commit (PDF), 2D top/bottom layout PNGs (`kicad-cli` SVG →
`rsvg-convert`).

**Timings** (public-repo runner, card board, run 43875965287): checks 37 s, outputs 80 s, in
parallel. Container init (image pull) 26–44 s per job; all gates together ~6 s; KiBot ~43 s.
On the private repo the pull took ~61 s (run 43868081556: checks 72 s, outputs 121 s). Release
run (tag → GitHub release): ~4 min including the full pipeline.

**Cache strategy:** a derived image `ghcr.io/kamranaghlami/hw-lab-ci:10.0.8` (KiCad + KiBot +
iBOM + KiDiff + ImageMagick + rsvg + Java/Freerouting), rebuilt only when `ci/Dockerfile`
changes (2 min 35 s cold). The alternative, stock `kicad/kicad` plus apt/pip each run, adds
~30–60 s per job and depends on PyPI and Debian mirrors at run time. Further saving still open:
merging the two jobs pulls the image once (~40–60 s less per run) at the cost of serialising.
Path filters skip docs-only pushes; `concurrency` cancels superseded runs.

**Minutes budget:** on GitHub Free each job is rounded up to whole minutes, so a pipeline run
bills ~3–4 private minutes and the planted matrix ~14. hw-lab was made public on
2026-11-16 (owner's call) so its runs are free; the private tracker repo needs this frugality.

**CI/tool gotchas hit** (also in `docs/memory/kicad10-gotchas.md`): KiBot must be installed with
`pip --no-compile`, needs `lxml numpy svgwrite mistune`, and must be given
`generate_interactive_bom.py` or it downloads iBOM at run time; GHCR image names must be lowercase;
Freerouting ≥2.5 needs Java 25 (pin 2.1.0 on Debian 13); the official 3D library at 10.0.8 lacks
the HRO USB-C and XKB button models; KiBot's `step` output → use `export_3d`; 3D renders with
`zoom: 1` crop the board → use `orthographic` + `auto_crop`.

## 4. Agent review vs automated gates (planted mistakes)

`experiments/planted/plant.py`, workflow `planted.yml`, run 43868914900. Each variant = the
real project with one mistake, gated exactly like CI. Review material uploaded under random
codes; verdicts committed before unblinding (`docs/experiments/planted-review-predictions.md`).

| mistake | ERC | pin map | intent check | DRC | agent review |
|---|---|---|---|---|---|
| UART TX/RX swapped at the MCU | – | **caught** (`PIN_UART_TX` header 43 vs schematic 44) | – | only as shorts against copper routed before the mistake | **caught** (net `UART_TX` on pin `RXD0`) |
| missing IMU decoupling (C5, C6 removed) | – | – | **caught** (`+3V3 needs 3×100n, found 1`) | – | **caught** (2 ICs, 1 small cap) |
| wrong pinout (AMS1117 VI/VO numbers swapped in the symbol) | – | – | **caught** (pin 2 is 'VI', datasheet says 'VO') | only as shorts against old copper | **caught** (datasheet table) |
| floating pin (IMU CS unconnected) | **caught** (`pin_not_connected`, error) | – | – | only as shorts against old copper | **caught** |
| VBUS trace 0.15 mm | n/a | n/a | n/a | **caught only with the custom `.kicad_dru` rule**; net-class width alone: **not caught** | spotted only by comparing renders side by side |

(The intent check was added after this run; its column comes from re-running it on the same
netlists.)

### 4.1 The layered model
- **ERC: connectivity.** Missed 4 of 5: anything electrically "legal".
- **Pin map: firmware ↔ hardware agreement.** Catches swaps on MCU pins only if the header was
  written independently.
- **Intent check (`tools/intent_check.py`): what the parts need.** Datasheet pin tables (pad →
  name) and required decoupling per power pin, recorded in `parts.toml`. Catches borrowed or
  wrong symbols (the LSM6DSO here *is* a borrowed LSM6DSL symbol) and missing caps.
  Missed: layout-time issues.
- **DRC: geometry, but only what a rule states.** Net-class widths are router defaults, not
  constraints. After layout, DRC "catches" schematic mistakes only by accident (copper that no
  longer matches). If the mistake predates layout, the router routes it faithfully and DRC passes.
- **Agent review: whatever is left.** Good on netlist semantics. Weak on geometry from images
  alone (a 0.15 mm vs 0.5 mm trace isn't obvious in a render).

### 4.2 Caveat
The review was **not truly blind**: the reviewer (me) knew the five categories and wrote the
checklist knowing them. A fair number needs a fresh reviewer that doesn't know the categories,
N variants with 0–3 mistakes each (clean ones included), and categories not on the list (D+/D−
swap, missing EN pull-up, wrong CC resistor value, I²C address clash, LED polarity), scored for
misses **and** false alarms. Not done; needs a subagent run with the owner's OK.

## 5. Pin-map check

`tools/pinmap.py gen|check <netlist> [header]`. It maps the MCU's `IOn`/`TXD0`/`RXD0`/`USB_D±` pins
to GPIO numbers and writes or verifies `firmware/include/board_pins.h` semantically (`#define
PIN_<NET> <gpio>`; comments and order are ignored). CI fails on missing, extra or different pins,
with a readable diff and the regenerate command. Verified: a swapped TX/RX header fails with
`MISMATCH PIN_UART_TX: header says GPIO44, schematic says GPIO43`.
KiCad 10 netlist quirks it handles: `pinfunction` is `NAME_PINNUMBER` (`IO0_27`); local-label
nets are prefixed `/`.

## 6. Releases

`release.yml` on `hw-v*` tags calls `hardware.yml` (`workflow_call`), then attaches
`hwlab-<tag>-complete.zip` (all outputs + reports), the JLCPCB gerber/drill zip, BOM and CPL.
**Verified:** tag `hw-v0.1` → https://github.com/KamranAghlami/hw-lab/releases/tag/hw-v0.1 (run
43876354780) with `hwlab-hw-v0.1-complete.zip` (1.7 MB), `-jlcpcb-gerbers-drill.zip` (11 gerber/drill
files, Protel extensions), `-jlcpcb-bom.csv` (21 parts, all with LCSC numbers) and `-jlcpcb-cpl.csv`.
The first attempt failed: KiBot didn't use the pip-installed iBOM and tried to **download**
`generate_interactive_bom.py` from GitHub at run time. Fixed in the image (a symlink to the
pinned install); the re-run passed with no downloads. KiBot also applies JLC rotation offsets on
its own (SOT-223 and USB-C +180° in the CPL). They look right, but check JLC's assembly preview
before the first order. Still downloaded at run time (optional, warning only): the two 3D models
missing upstream, which KiBot fetches from EasyEDA by LCSC number. Commit them to
`lib/3dmodels-extra/` for a hermetic build.

## 7. Agent placement and routing (owner-requested experiment)

The owner asked for "aesthetically plausible, credit-card form factor, rounded corners". So:
ISO/IEC 7810 ID-1, 85.60 × 53.98 mm, r = 3.18 mm (`placement.toml [board]`). The agent wrote the
placement from stated rules; Freerouting 2.1.0 routed; `tools/stitch_gnd.py` stitched the
pours. The result is committed as the board (ee75d58); CI run 43875965287 is green.

| checklist item (agreed before scoring) | agent self-score | evidence |
|---|---|---|
| decoupling: each required cap bound to its pin, 100n ≤ 3 mm, bulk ≤ 10 mm (**CI gate**) | pass | U1.3V3←C3 1.92 mm, U3.VDD←C6 2.06, U3.VDDIO←C5 2.73, U2.VI←C1 3.8, U2.VO←C2 ≤10 |
| connectors flush on edges (**gate**) | pass | J1 0.15 mm, J2 0.22 mm from the edge |
| antenna at the edge, keep-out on both layers, no copper under it (**gate**) | pass | antenna end 0.03 mm from the edge; footprint keep-out zone on F.Cu + B.Cu |
| functional grouping (power / MCU / IMU / UI) | pass | LDO + bulk caps between USB-C and the module; IMU mid-board, ~20 mm from the LDO |
| USB as a short coupled pair | **fail** | D+/D− go to B.Cu through 4 vias and run ~45 mm, not coupled. Freerouting has no diff-pair routing; OK for 12 Mbit/s but not the intent |
| power widths per class | pass | VBUS ≥ 0.4 mm enforced by a `.kicad_dru` error rule; +3V3 0.25 mm |
| tracks at 45° only | pass | 0/167 segments off-angle |
| rotations 0/90, parts inside the outline | pass | measured |
| designators readable and off pads | **fail** | J1's designator sits on its pads; the C5/C6 and R3/C4 labels are crowded |
| GND pour on both layers except under the antenna | pass with a waiver | 3 tiny top-pour slivers that no via fits → waived as an owner GUI task |
| silk: title + hash, J2 pinout, RST/BOOT, ANT | pass | `${GIT_HASH}` filled in by KiBot (`ee75d58` on the board) |
| mounting holes | not done | optional; would need board-only footprints |
| 0 unwaived DRC errors | pass | |

How it got there: 8 bootstrap iterations (probe runs 43869781009 … 43875708944), each fixing
something the measurements showed:
- a silk text on an undefined layer (KiCad 10 calls it `F.Silkscreen`; `F.SilkS` returns −1);
- +3V3 at 0.3 mm can't escape a 0.5 mm-pitch LGA → 0.25 mm;
- top-pour islands → grid stitching plus a per-island pass with island removal off during stitching;
- starved thermals on tiny pads → solid SMD connections, thermal reliefs for THT only;
- courtyard and silk collisions;
- my own decap gate passing **vacuously** (`pcb_sync` didn't set pad pin functions). It now fails when it finds nothing to check.

Freerouting takes 6–8 s per run on this board.

**What this says about agent layout:** an agent can produce a DRC-clean, measurably reasonable
2-layer layout for a small board if the rules are written down and measured. It needed
iterations, and it misses what the autorouter can't express (differential pairs, RF/return-path
judgement, silk aesthetics). The owner's GUI review scored against the same checklist is the
missing half of this experiment (§2.3 session).

## Recommended toolchain

| concern | choice |
|---|---|
| KiCad | 10.0.8 pinned in three places: CI image, library tag, desktop |
| parts | `parts.toml` atomic parts → `build_lib.py` (official libs at the pinned tag, MPN/LCSC/datasheet pins/decaps) |
| schematic | `design.py` → `schgen.py` (raw S-expressions, deterministic) |
| sch → pcb | `pcb_sync.py` in CI or F8 in the GUI; the human places and routes |
| text edits | `kisexpr.py` (canonical parse/dump), always followed by DRC |
| gates | regen check, `sch_overlap.py`, ERC + `check_report.py` waivers, `pinmap.py`, `intent_check.py`, DRC + `.kicad_dru` |
| outputs | KiBot 1.9.1 (JLCPCB template, iBOM, diff, 3D) + `kicad-cli` 2D plots |
| CI image | derived image on GHCR, rebuilt only when the Dockerfile changes |
| not recommended | kiutils (drops KiCad 10 data), SKiDL for schematics (fine for netlists), atopile (no schematic, CLI deprecated) |

## Recommended repo layout

```
CLAUDE.md                     thin: imports docs/CLAUDE.md + docs/memory/MEMORY.md
docs/  CLAUDE.md findings.md memory/ experiments/
hardware/                     the KiCad project (one board per repo)
  design.py                   the schematic source (agent edits this)
  hwlab.kicad_sch             generated, committed, CI checks it is up to date
  hwlab.kicad_pcb             human-owned (GUI), agent edits surgically
  hwlab.kicad_pro .kicad_dru  rules: net classes, severities, custom DRC
  placement.toml              initial placement only
  waivers.toml                reviewed ERC/DRC waivers with reasons
  hwlab.kibot.yaml            outputs
  lib/ parts.toml hwlab.kicad_sym hwlab.pretty/ 3dmodels/   project-local libraries
firmware/include/board_pins.h generated from the netlist, CI-checked
tools/                        stdlib-only Python (+pcbnew where noted)
ci/Dockerfile                 CI image
.github/workflows/            hardware.yml release.yml ci-image.yml
```

## CI template

`template/` holds the files to copy into the tracker repo, with a README listing what to rename.

## Open items, in priority order
1. Owner's GUI round trip (§2.3) and removing the bootstrap waiver it resolves.
2. Truly blind review with a fresh subagent (§4.2).
3. Hierarchical sheets in `schgen` for the larger tracker board.
4. Hand-route USB as a coupled pair (Freerouting can't); score the owner's GUI version on the §7 checklist.
5. Merge the CI jobs to pull the image once, if serialising is acceptable on the private repo.
6. Commit the two EasyEDA-sourced 3D models so builds never download anything.
7. Add "copper intruding into the antenna keep-out" to the planted set; mounting holes for the card.
8. Commit KiCad's own expansion of `hwlab.kicad_pro` (the first GUI save will rewrite it).
