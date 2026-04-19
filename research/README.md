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

- Verbatim-quotable passages from primary sources (`quotes`)
- Atomic claims with per-claim source attribution (`claims`) — **on
  synthesis artifacts only** (person, organization, event, finding,
  location). Document, transcript, and media artifacts carry no
  claims layer by design; their evidentiary content lives entirely
  in `quotes`. See `meta/conventions.md` "Document nodes vs synthesis
  nodes" for the rationale.
- Entities referenced (person, org, event, doc, transcript, media,
  location, finding)
- Naming quirks in the sources (typos, alt spellings)
- Research gaps — open investigation threads
- Rumors (on person / org / event / location artifacts) — widely-
  reported claims lacking primary-source support here
- Iteration log — append-only audit trail of updates

The narrative node at `{type}/{slug}.md` is a derived view of its
artifact. For **document nodes**, `scripts/build-from-research.py`
deterministically regenerates the narrative from the artifact
(Phase II of the layered build process). For **other node types**,
the narrative is currently hand-authored from the artifact per
`meta/conventions.md` discipline; Phase II coverage extension to
synthesis nodes is tracked in `BACKLOG.md`.

## Conventions

- Schema defined in `meta/schema.yaml` under `types.research-artifact`
- Validated structurally via `scripts/validate-research.py`
- Scaffolded empty via `scripts/research-scaffold.py --target {type}/{slug}`
- Never hand-delete entries; use lifecycle fields
  (`superseded_by`, `contradicted_by`) to preserve history

## Workflow

Artifacts are produced by Phase I of the layered build process —
`research-scaffold.py` creates an empty shell, `extract-source.py`
produces scratch files from the archived primary sources, and Phase I
populates the sections per `prompts/build.md`. Phase II
(`build-from-research.py`) then regenerates the narrative node from the
artifact. Phase III (`review-coverage.py`) verifies the two layers are
in coverage alignment.

Current inventory lives on disk under `research/`. Use
`validate-research.py` to audit artifact integrity.
