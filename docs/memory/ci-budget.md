---
name: ci-budget
description: GitHub Actions minutes are a real constraint on the owner's account (GitHub Free)
metadata:
  type: project
---

Owner is on GitHub Free: 2,000 private-repo Actions minutes/month shared by all private repos. On 2026-11-16 other repos had already used ~1,770 min of November (mongoose_cli alone ~1,394). hw-lab was switched to public that day (via the t-sim7000g-d4 session, relayed as the owner's decision) to make its runs free; the real tracker repo will stay private.

**Why:** a full hw-lab pipeline run costs ~4 billed minutes (2 jobs, ~60 s image pull each); the planted matrix ~14.
**How to apply:** path-filter hardware CI, cancel superseded runs, use the GHCR image, avoid probe runs that aren't needed. Self-hosted runners are not an option (owner's connection is too poor), and the 1 vCPU / 2 GB VPS dev box can't run KiCad. See [[dev-machine]].
