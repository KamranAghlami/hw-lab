---
name: owner-decisions
description: Decisions the owner made explicitly (versions, repo visibility, board shape, render preferences)
metadata:
  type: project
---

- 2026-11-16: Owner's desktop runs KiCad **10.0.8**; CI pins `kicad/kicad:10.0.8` and libraries are fetched from the KiCad GitLab tag `10.0.8`.
- 2026-11-16: Owner approved creating `KamranAghlami/hw-lab` as **private**; later the same day it was made **public** to save private Actions minutes (owner's call, relayed and executed by the t-sim7000g-d4 session). The real tracker repo stays private.
- 2026-11-16: Board shape: ISO/IEC 7810 ID-1 credit card (85.60 x 53.98 mm, r 3.18 mm), "aesthetically plausible"; agent placement/routing is in scope as an experiment.
- 2026-11-16: Renders: plain top + bottom views only (2D layout PNGs, orthographic 3D); no angled/ray-traced hero shots.
- 2026-11-16: Owner accepted that their commit email is visible in the now-public repo (it is already public in other repos).
- The CI image `ghcr.io/kamranaghlami/hw-lab-ci:10.0.8` is a **private** GHCR package (verified 2026-11-17); the public repo's workflows pull it with `GITHUB_TOKEN`.
- Owner is in Iran: only use services whose terms allow it (GitHub has a US Treasury licence; most US clouds e.g. Oracle do not). Never suggest VPN sign-ups.

**Why:** these were explicit owner choices; several override the original brief.
**How to apply:** bump image tag, `parts.toml [upstream] tag` and docs together, only after asking. See [[dev-machine]], [[ci-budget]].
