---
id: meta/README
type: meta
schema_version: 1
created: 2026-05-05
---

# /meta/

Governance, specs, templates, structured-fact backing, and toolkit-
internal records. Everything that isn't investigator-facing content
(`/people/`, `/organizations/`, ...), source archive (`/sources/`),
or scripts (`/scripts/`).

## Layout

| Path | Role |
|---|---|
| `BACKLOG.md` | Deferred work register — items partitioned A (priority sequence) / B (parallel batch) / C (anytime) |
| `conventions.md` | Evidentiary discipline + structural rationale (the *why* behind every rule) |
| `roadmap.md` | Active toolkit-development work + completed phases |
| `schema.yaml` | Machine-readable spec — node types, archetypes, kinds, required sections, vocabularies |
| `sources-access.md` | Site-specific archival workarounds (SEC, defense.gov, Twitter/X, etc.) |
| `templates/` | Scaffolding templates per node type — consumed by `scripts/new.py` |
| `research/` | YAML research artifacts backing each content node — Phase I working surface; consumed by `scripts/build-from-research.py`; fork-deletes |
| `toolkit-notes/` | Validator issue-log (auto-appended). Reserved for future retrospectives or technique notes; currently no `.md` content. |
| `topic/` | Topic-specific governance — priority research queue, topic overview, corpus addenda, in-progress working notes; fork-deletes when toolkit is forked to a different investigation |

## Root vs subdirs

The split is codified in `conventions.md` under "Repository layout —
content flat, tooling organized" (sub-section "Inside `/meta/` — root
vs subdirs"). Briefly:

- **Root** holds stable specs and forward-looking work registers
  (rules + active agenda).
- **`toolkit-notes/`** is reserved for backward-looking lessons
  (why a rule exists; what was tried before). Currently holds only
  the validator-appended `issue-log.yaml`.
- **`topic/`** and **`research/`** are the subdirs that fork-delete
  (`topic/` carries topic-specific governance; `research/` carries
  topic-specific structured facts). Everything else is topic-neutral
  toolkit and survives a fork.

New governance items should land at the right tier on first author.
When in doubt, consult `conventions.md` for the principle and
existing files in each subdir as analogues.
