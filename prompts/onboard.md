# Onboard prompt

Paste into a fresh Claude Code session when starting work on this
repository for the first time in a session.

---

You are joining a primary-source investigation knowledge base. Before
doing anything:

1. Read `CLAUDE.md` — session-start checklist and current build state.
2. Read `README.md` — what this repository is.
3. Read `meta/conventions.md` — the evidentiary discipline.
4. Read `meta/schema.yaml` — the machine-readable spec for node types,
   required sections, vocabularies, research-artifact shape.
5. Read `meta/roadmap.md` — active work (F.7 finding
   renderer pending; Step G content population in progress) +
   architectural corrections that shape the current codebase.
6. Read `meta/topic/research-queue.md` — current priority queue.
7. Read `meta/BACKLOG.md` — deferred work items; note any active entries
   relevant to the session's planned task.
8. Review the persistent Claude Code memory for this project. `MEMORY.md`
   is auto-loaded into your conversation context by the harness; read
   every file it references (stored in your Claude Code project memory
   directory — typically `~/.claude/projects/<sanitized-project-path>/memory/`).
   Apply the durable policies logged there: impartial validator
   reporting (no category-tuned thresholds); resolve every prose-drift-check
   warning structurally on scoped fields (top-level free-prose:
   `description`, `background`, `uap_relevance`, `credibility_notes`;
   per-entry synthesis content notes: `ownership_timeline.note`,
   `uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
   `media_versioning.note`, `vouching_chain.attestation`) —
   zero-warnings target. Structural label cells + cross-reference
   descriptor notes (`corroboration_items.note`,
   `witnesses_testimony.note`, `org_relationships.note`,
   `location_relationships.note`, role titles, `timeline[].event`)
   are not scanned; never set count targets / ranges when scoping
   artifact list population — let the source drive density.

Then run the health check:

```
bash scripts/tests/pre-commit.sh
```

All seven gates must be green:
- `help-check` — every `scripts/*.py --help` exits clean
- `test_stopwords` — STOPWORDS shape + content-word regression test
- `smoke` — fixture scaffolds validate cleanly
- `validate.py` — structural + verbatim-quote checks (orchestrator;
  per-check modules in `scripts/checks/`)
- `validate-research.py` — research-artifact structural + prose-drift
  + iff-section dispatch (orchestrator; per-check modules in
  `scripts/checks/`)
- `review-coverage.py --all` — Phase III coverage / boundary /
  stub-linking / description-drift review (orchestrator; per-check
  modules in `scripts/checks/`)
- `build-state.py --check` — CLAUDE.md build-state block in sync

If errors exist, report them and stop.

Then:

1. Report the current build state (node counts per type) summarized
   from `CLAUDE.md`.
2. Summarize the top 3 items in `meta/topic/research-queue.md` Priority
   Build Queue with rationale.
3. Report the active roadmap sub-phase and what's queued next (from
   `meta/roadmap.md`).
4. Ask the user what to build or what task to run.

Do not begin scaffolding nodes without explicit direction from the user.
