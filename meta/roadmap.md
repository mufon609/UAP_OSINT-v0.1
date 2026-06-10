---
id: meta/roadmap
type: meta
---

# Roadmap

Active work on the toolkit. Git log + the code itself is the authoritative
record of what shipped; **shipped items are deleted from this file, not
kept as records.**

---

## Active work

### Step G — Content population  🟡 IN PROGRESS

Ongoing entity-node builds driven by the priority queue. Cluster status,
build candidates, and per-node rationale live in
`meta/topic/research-queue.md` (canonical); the auto-generated build-state
block in `CLAUDE.md` is the authoritative count of what shipped.

### E.3 — Cross-node update propagation  ⏸ DEFERRED

Blocked on: multiple artifacts with overlapping evidentiary claims. Can't
build propagation tooling without a real propagation case. The build
pipeline carries **no** propagation pass: the auditor's manual
adjacent-node propagation goal (and its tightening loop) was removed
2026-06-09 after it generalized wrongly from one node to its family (the
dird-31 26-artifact misfire, 24/26 already correct) — a build pays
attention to the built node and nothing else. Cross-node updates happen
only when the user directs `/augment` at a named node. If propagation
returns, it is rebuilt deliberately as its own task with its own tooling,
not re-attached to the build.
(Cross-artifact ref *integrity* is already covered — `corroborated_by` /
`superseded_by` / `contradicted_by` resolution by
`scripts/checks/cross_refs.py` plus the tier-linking checks; what remains
is propagation, not validation.)

---

## Conventions

- 🟡 = in progress
- ⏳ = pending (next-up)
- ⏸ = deferred (not next-up)
- ❌ = removed / rejected
