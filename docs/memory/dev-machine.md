---
name: dev-machine
description: Dev box is 1 vCPU / 2 GB RAM shared with live services; never install KiCad or Docker images there
metadata:
  type: project
---

The agent's dev machine is tiny (1 vCPU, 2 GB RAM, no swap, live services). KiCad and Docker images are not installed; every `kicad-cli`/`pcbnew`/KiBot step runs in GitHub Actions. Python tooling goes in `./venv` only (never system Python).

**Why:** owner constraint in the brief; the box has ~350 MB free RAM.
**How to apply:** for any KiCad experiment write `ci/probe/<name>.sh` and run `gh workflow run probe.yml -f script=<name>`; download results with `gh run download`. Related: [[owner-decisions]].
