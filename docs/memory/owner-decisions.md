---
name: owner-decisions
description: Decisions the owner made explicitly (versions, repo)
metadata:
  type: project
---

- 2026-11-16: Owner's desktop runs KiCad **10.0.8**; CI pins `kicad/kicad:10.0.8` and libraries are fetched from the KiCad GitLab tag `10.0.8`.
- 2026-11-16: Owner approved creating the **private** GitHub repo `KamranAghlami/hw-lab`.

**Why:** brief requires CI and desktop KiCad to match, and the repo to be private with owner approval.
**How to apply:** bump the image tag, `tools/fetch_kicad_lib.py` tag, and docs together, and only after asking the owner. See [[dev-machine]].
