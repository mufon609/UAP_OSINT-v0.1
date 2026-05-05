---
id: meta/README
type: meta
schema_version: 1
created: 2026-05-05
---

# /meta/

Governance, specs, templates, and toolkit-internal records. Everything
that isn't investigator-facing content (`/people/`, `/organizations/`,
..., `/research/`), source archive (`/sources/`), or scripts
(`/scripts/`).

## Layout

| Path | Role |
|---|---|
| `BACKLOG.md` | Deferred work register — items partitioned A (priority sequence) / B (parallel batch) / C (anytime) |
| `conventions.md` | Evidentiary discipline + structural rationale (the *why* behind every rule) |
| `roadmap.md` | Active toolkit-development work + completed phases |
| `schema.yaml` | Machine-readable spec — node types, archetypes, kinds, required sections, vocabularies |
| `sources-access.md` | Site-specific archival workarounds (SEC, defense.gov, Twitter/X, etc.) |
| `templates/` | Scaffolding templates per node type — consumed by `scripts/new.py` |
| `toolkit-notes/` | Retrospectives, postmortems, technique docs, design records |
| `topic/` | Topic-specific governance — priority research queue, topic overview, corpus addenda, in-progress working notes; fork-deletes when toolkit is forked to a different investigation |

## Root vs subdirs

The split is codified in `conventions.md` under "Repository layout —
content flat, tooling organized" (sub-section "Inside `/meta/` — root
vs subdirs"). Briefly:

- **Root** holds stable specs and forward-looking work registers
  (rules + active agenda).
- **`toolkit-notes/`** holds backward-looking lessons (why a rule
  exists; what was tried before).
- **`topic/`** is the only subdir that fork-deletes. Everything else
  is topic-neutral toolkit and survives a fork.

New governance items should land at the right tier on first author.
When in doubt, consult `conventions.md` for the principle and
existing files in each subdir as analogues.
