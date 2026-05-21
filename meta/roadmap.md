---
id: meta/roadmap
type: meta
schema_version: 1
created: 2026-04-17
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
build propagation tooling without a real propagation case — likely after
~10 nodes through the full pipeline. The build topology's Audit role
(`prompts/topology.md`) already runs a manual adjacent-node propagation
pass; this item is the *mechanical* layer it lacks: bidirectional
`corroborated_by` / `superseded_by` / `contradicted_by` pointers resolving
across artifacts, plus validator coverage for broken cross-artifact refs.

---

## Conventions

- 🟡 = in progress
- ⏳ = pending (next-up)
- ⏸ = deferred (not next-up)
- ❌ = removed / rejected
