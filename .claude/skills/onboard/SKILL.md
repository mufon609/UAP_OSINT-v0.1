---
name: onboard
description: Orient to this primary-source investigation repository at the start of a session — read the governing docs, confirm the health check is green, and report current build state. Use when starting work here for the first time in a session.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(python3 scripts/build/build-state.py *)
  - Bash(bash scripts/tests/pre-commit.sh)
---

# Onboard

You are joining a primary-source investigation knowledge base. The toolkit is
topic-neutral; this instance's subject is described in
`meta/topic/overview.md`.

## Build-state sync (computed now)

```!
python3 scripts/build/build-state.py --check
```

## Read the governing docs, in order

1. `CLAUDE.md` — session-start checklist + current build state.
2. `README.md` — what this repository is.
3. `meta/schema.yaml` — node types, required sections, vocabularies; and
   `meta/schema-research-artifact.yaml` — the research-artifact spec that drives
   `validate-research.py`.
4. `meta/roadmap.md` — active work + the architectural corrections that shaped
   the codebase.
5. `meta/topic/research-queue.md` — current priority queue.
6. `meta/BACKLOG.md` — deferred items; note any relevant to this session.
7. `meta/memory.md` — cross-cutting contributor working knowledge. Then review
   the personal memory directory (`MEMORY.md` is auto-loaded; referenced files
   live under `~/.claude/projects/<sanitized-project-path>/memory/`). Durable
   evidentiary rules live with their owners (`meta/schema.yaml`, `.claude/skills/build-protocol/`, `scripts/checks/`), not memory.

## Health check

Run `bash scripts/tests/pre-commit.sh` — every gate must be green (the chain
includes the structural / verbatim / prose-drift / coverage validators, the
`.claude/` skills lint, and the phase-routing parity gate). If any gate fails,
report it and stop. (At commit time these same gates run as a blocking hook —
nothing red can be committed.)

## Then

1. Report the current build state (node counts per type) from `CLAUDE.md`.
2. Summarize the top 3 items in the research queue with rationale.
3. Report the active roadmap step and what's queued next.
4. Ask the user what to build or what task to run.

Do not scaffold nodes without explicit direction. When the user directs a
build, run it through `/build` (the multi-agent pipeline) — don't hand-author
the artifact in the main thread.
