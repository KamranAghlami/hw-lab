---
name: open-owner-questions
description: Owner decisions still open as of 2026-11-17 (GUI re-save test only; blind review done)
metadata:
  type: project
---

1. **GUI round trip in KiCad 10.0.8** (findings §2.3). Still open, but smaller. On 2026-11-17 the owner asked
   why they should do it, so the agent did the fixes itself (IMU GND open, labels; findings §7.1). What remains
   needs the real GUI: open `hardware/hwlab.kicad_pcb` (and the .kicad_pro), save, commit and push, so the
   re-save diff can be measured. Optional: hand-route USB D+/D- as a coupled pair. Ask, don't assume.
2. ~~Truly blind review~~: approved by the owner 2026-11-17 and done (findings §4.3, 11/11, 0 false alarms).

Deferred to the tracker board (peer recommendation, not yet owner-confirmed): hierarchical sheets, hand-routed
USB pair, hermetic EasyEDA 3D models, antenna-intrusion planted case, mounting holes. See [[tracker-carry-forward]].

**Why:** tracks which experiments still need the owner.
**How to apply:** ask the owner directly. When answered, move the answer to [[owner-decisions]] and delete this file.
