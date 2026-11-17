---
name: render-provenance
description: Before sending board images to the owner, check they come from the run that built the committed layout; owner wants plain top/bottom PNGs only
metadata:
  type: feedback
---

Before sending renders/plots to the owner, confirm they were produced by the CI run that built the
**currently committed** `.kicad_pcb` (match run head SHA to the commit). Send only plain top and bottom
2D layout PNGs, no 3D/hero shots.

**Why:** the t-sim7000g-d4 session once sent the owner renders of the old 40×60 mm board as if they were
the credit-card board.
**How to apply:** `gh run view <id> --json headSha` == `git rev-parse HEAD` (for hardware/ paths) before
downloading artifacts to share. See [[owner-decisions]].
