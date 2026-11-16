# Hardware CI template (from hw-lab)

`template/install.sh <repo> <board> <ghcr-owner>` copies the tested setup into another repo.
What you get and what to change:

| file | what it is | change for a new board |
|---|---|---|
| `.github/workflows/hardware.yml` | checks (regen, overlap lint, ERC, pin map, intent, DRC) + KiBot outputs | `BOARD` path is already renamed; adjust `paths:` if your layout differs |
| `.github/workflows/release.yml` | `hw-v*` tag → full pipeline → GitHub release with the fab package | nothing |
| `.github/workflows/ci-image.yml` + `ci/Dockerfile` | the CI image on GHCR | bump `kicad/kicad:<ver>` **together with** `parts.toml [upstream] tag` and the desktop KiCad |
| `hardware/<board>.kibot.yaml` | outputs: PDF, JLC gerbers/BOM/CPL, iBOM, 3D, STEP, diffs | nothing |
| `hardware/<board>.kicad_pro` | net classes, DRC severities, JLC limits, `GIT_HASH` variable | net-class patterns for your nets |
| `hardware/<board>.kicad_dru` | custom DRC (power width etc.) | add rules for what matters (e.g. 2 A modem supply, RF keep-outs) |
| `hardware/lib/parts.toml` | atomic parts: MPN, LCSC, datasheet pin tables, required decaps | your parts; run `tools/build_lib.py` |
| `tools/pinmap.py` | netlist → firmware header | `SPECIAL` table for your MCU's non-`IOn` pins |

Then write `hardware/design.py` (see hw-lab's for the pattern), run it, commit the generated
`.kicad_sch`, and create the board with `tools/pcb_sync.py` (or F8 in the GUI).

Order of first runs:
1. Push `ci/Dockerfile` + `ci-image.yml` → image builds (about 3 min).
2. Push the rest → `hardware.yml` runs. On a private repo each run bills about 3–4 minutes.

Not copied (hw-lab only): `probe.yml`, `planted.yml`, `experiments/`.
