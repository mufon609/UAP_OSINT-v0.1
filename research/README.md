---
id: research/README
type: meta
schema_version: 1
created: 2026-04-17
---

# /research/

Structured investigation records (research artifacts), one per content
node. Each file is pure YAML at `research/{slug}.yaml` where `{slug}`
matches the target node's slug.

## What these are

Research artifacts are the machine-readable structured-fact layer
behind each node. They capture:

- Verbatim-quotable passages from primary sources
- Atomic claims with per-claim source attribution
- Entities referenced (person, org, event, doc, location, finding)
- Naming quirks in the sources (typos, alt spellings)
- Research gaps — open investigation threads
- Rumors (on person / org / event / location artifacts) — widely-
  reported claims lacking primary-source support here
- Iteration log — append-only audit trail of updates

The narrative node at `{type}/{slug}.md` is a derived view of this
artifact, regenerated via `scripts/build-from-research.py`.

## Conventions

- Schema defined in `meta/schema.yaml` under `types.research-artifact`
- Validated structurally via `scripts/validate-research.py`
- Scaffolded empty via `scripts/research-scaffold.py --target {type}/{slug}`
- Never hand-delete entries; use lifecycle fields
  (`superseded_by`, `contradicted_by`) to preserve history

## Current state

`/research/` is currently empty. Populated through Phase I of the
layered build process (see `prompts/build.md` when the Phase I rewrite
ships in sub-phase D.2).
