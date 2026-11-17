---
name: tracker-carry-forward
description: Inputs and constraints for the real vehicle-tracker board (separate private repo), gathered here and from T-SIM7000G
metadata:
  type: project
---

For the vehicle-tracker board that hw-lab's lessons feed (built later in a separate, private repo;
the tracker firmware is ESP-IDF on ESP32, repo `KamranAghlami/T-SIM7000G`):

- **Spec before layout**: write a hw-spec first, same rule as T-SIM7000G's "spec before code".
- **Parts/feature input**: T-SIM7000G `docs/backlog.md` §5 "next-board wishlist".
- **Modem**: consider a Cat-1 + 2G modem.
- **Power**: use a low-Iq regulator, not the AMS1117 used here. Battery sleep current matters, and 2G
  TX bursts pull ~3.2 A from the cell (T-SIM7000G `docs/memory/lessons-2026-11-12.md`); size the
  supply path, bulk caps and trace widths for that.
- **Pin map**: generate/check `firmware/include/board_pins.h` from the netlist (`tools/pinmap.py`) and
  check it against the tracker firmware's pin usage.
- Start from `template/` (findings §"Recommended repo layout"); expect hierarchical sheets in `schgen`
  (~60 parts), and do the USB pair by hand (Freerouting has no diff-pair routing).
- CI frugality matters there: the tracker repo is private and shares the 2,000 free minutes. See [[ci-budget]].

**Why:** relayed by the t-sim7000g-d4 session on 2026-11-17 before its context was rewound.
**How to apply:** read this before starting the tracker hardware; re-verify the T-SIM7000G file paths, they may have moved.
