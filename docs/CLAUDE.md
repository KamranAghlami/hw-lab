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

## Layout

See `docs/findings.md` § "Repo layout" for the annotated tree.

## Common commands

```sh
# remote KiCad sandbox: runs ci/probe/<name>.sh in the KiCad image, uploads ./out
gh workflow run probe.yml -f script=<name>
gh run watch <id>; gh run download <id> -D build/<name>
```
