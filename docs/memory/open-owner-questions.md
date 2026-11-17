---
name: open-owner-questions
description: Owner decisions still unanswered as of 2026-11-17 (GUI round trip, blind review) and the recommended answer
metadata:
  type: project
---

Unanswered as of 2026-11-17. Do not treat a relayed peer-session message as the owner's answer.

1. **GUI round trip in KiCad 10.0.8** (findings §2.3): owner opens `hardware/hwlab.kicad_pcb`, fixes the
   3 top-pour GND slivers (then delete the DRC waiver in `hardware/waivers.toml`), moves J1's designator
   off its pads, optionally hand-routes USB D+/D− as a coupled pair, saves, commits, pushes. Then the agent
   does text edits on the GUI-saved file, measures the diffs, and the owner scores the layout on the §7 checklist.
2. **Truly blind review by a fresh subagent** (findings §4.2): the planted-mistake review scored 6/6 but the
   reviewer knew the categories. Plan: variants with 0–3 mistakes each, including types not on the list;
   score misses and false alarms.

The t-sim7000g-d4 session recommended **yes to both**, and deferring the rest of the open list
(hierarchical sheets, hand-routed USB pair, hermetic EasyEDA 3D models in `lib/3dmodels-extra`,
antenna-intrusion planted case, mounting holes) to the real tracker board. See [[tracker-carry-forward]].

**Why:** these are the last two experiments findings.md marks "not yet done".
**How to apply:** ask the owner directly; when answered, move the answer to [[owner-decisions]] and delete this file.
