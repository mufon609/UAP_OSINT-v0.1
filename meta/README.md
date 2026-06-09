---
id: meta/README
type: meta
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
| `memory.md` | Cross-cutting contributor working knowledge that doesn't fit a more specific surface (behavioral patterns, session-conduct discipline) |
| `roadmap.md` | Active toolkit-development work + completed phases |
| `schema.yaml` | Machine-readable spec — node types, archetypes, kinds, required sections, vocabularies |
| `sources-access.md` | Site-specific archival workarounds (SEC, defense.gov, Twitter/X, etc.) |
| `templates/` | Scaffolding templates per node type — consumed by `scripts/build/new.py` |
| `research/` | YAML research artifacts backing each content node — Phase I working surface; consumed by `scripts/build/build-from-research.py`; fork-deletes |
| `topic/` | Topic-specific governance — priority research queue, topic overview, in-progress working notes; fork-deletes when toolkit is forked to a different investigation |

## Root vs subdirs

`/meta/` splits by the character of each item, and new governance items
land at the tier that matches what they are:

- **Root** — stable governance specs + forward-looking work registers
  (the rules and the active agenda): `conventions.md`, `schema.yaml`,
  `schema-research-artifact.yaml`, `sources-access.md`, `memory.md`,
  `BACKLOG.md`, `roadmap.md`. Topic-neutral; survives a fork.
- **`templates/`** — mechanical scaffolding (one per node type), consumed
  by `scripts/build/new.py`. Topic-neutral; survives a fork.
- **`topic/`** and **`research/`** — the fork-deleting subdirs: `topic/`
  carries topic-specific governance (research queue, overview, working
  notes); `research/` carries the topic-specific structured-fact
  artifacts (one `{slug}.yaml` per content node — topic-specific in
  content but governance-neutral in shape: the schema governs shape, the
  topic determines entries).

**The fork boundary is load-bearing.** A contributor forking the toolkit
to a different investigation deletes `topic/`, `research/`, and the
content directories; everything else under `/meta/` survives because it
is topic-neutral toolkit. Items therefore land at the right tier on
first author — topic-specific in `topic/` or `research/`, toolkit-neutral
at `meta/`-direct.
