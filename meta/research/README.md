---
id: meta/research/README
type: meta
---

# /meta/research/

Structured investigation records (research artifacts), one per content
node. Each file is pure YAML at `meta/research/{slug}.yaml` where
`{slug}` matches the target node's slug.

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
- Per-type structured sections (timeline, affiliations, relationships,
  corroboration_items, program_involvement, vouching_chain, etc.)

The narrative node at `{type}/{slug}.md` is a derived view of its
artifact. `scripts/build/build-from-research.py` deterministically regenerates
the narrative from the artifact (Phase II of the layered build
process) for all nine node types — document, person, event,
transcript, media, organization, location, finding, and investigation.

## Conventions

- Schema defined in `meta/schema.yaml` under `types.research-artifact`
- Validated structurally via `scripts/build/validate-research.py`
- Scaffolded empty via `scripts/build/research-scaffold.py --target {type}/{slug}`
- Never hand-delete entries; use lifecycle fields
  (`superseded_by`, `contradicted_by`) to preserve history

## Workflow

Artifacts are produced by the build pipeline — `research-scaffold.py`
creates an empty shell, `extract-source.py` produces scratch files from
the archived primary sources, and the `/build` pipeline (worker + builder
roles) populates the sections. `build-from-research.py` then regenerates
the narrative node from the artifact, and `review-coverage.py` verifies
the two layers are in coverage alignment.

Current inventory lives on disk under `meta/research/`. Use
`validate-research.py` to audit artifact integrity.
