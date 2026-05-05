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

- Verbatim statements from primary sources (`quotes[]`) — the universal
  evidentiary primitive across all node types, filtered at render time
  for type-specific section rendering (`## Statements` on person,
  `## Key Testimony` on hearings, `## Key Passages` elsewhere). See
  `meta/conventions.md` "Statements as the universal evidentiary
  primitive" for the rationale.
- Entities referenced (person, org, event, doc, transcript, media,
  location, finding)
- Naming quirks in the sources (typos, alt spellings)
- Rumors (on person / org / event / location artifacts) — widely-
  reported claims lacking primary-source support here
- Per-type structured sections (timeline, affiliations, relationships,
  corroboration_items, program_involvement, vouching_chain, etc.)

The narrative node at `{type}/{slug}.md` is a derived view of its
artifact. For **renderer-supported types** (document, person, event,
transcript, media, organization, location),
`scripts/build-from-research.py` deterministically regenerates the
narrative from the artifact (Phase II of the layered build process).
Finding is the last remaining type; F.7 renderer design pass is open
(see `meta/roadmap.md`).

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
