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
5. Read `meta/roadmap.md` — active work (Step G content population
   in progress) + architectural corrections that shape the current
   codebase.
6. Read `meta/topic/research-queue.md` — current priority queue.
7. Read `meta/BACKLOG.md` — deferred work items; note any active entries
   relevant to the session's planned task.
8. Read `meta/memory.md` — cross-cutting contributor working knowledge
   (behavioral patterns that don't fit `conventions.md` / `schema.yaml`
   / specific prompts). Then review the personal Claude Code memory
   directory for this project — `MEMORY.md` is auto-loaded into the
   conversation context; each referenced file lives at
   `~/.claude/projects/<sanitized-project-path>/memory/`. The personal
   memory directory holds Claude-session-specific behavioral patterns
   (e.g., post-compaction discipline) that don't belong in the repo's
   contributor-facing files. Durable evidentiary and structural rules
   are NOT in either memory surface — those live in `conventions.md`,
   already read in step 3.

Then run the health check:

```
bash scripts/tests/pre-commit.sh
```

All nine gates must be green:
- `help-check` — every `scripts/{build,tools}/*.py --help` exits clean
- `test_stopwords` — STOPWORDS shape + content-word regression test
- `smoke` — fixture scaffolds validate cleanly
- `scripts/build/validate.py` — structural + verbatim-quote checks
  (orchestrator; per-check modules in `scripts/checks/`)
- `scripts/build/validate-research.py` — research-artifact structural
  + prose-drift + iff-section dispatch (orchestrator; per-check modules
  in `scripts/checks/`)
- `scripts/build/review-coverage.py --all` — Phase III coverage /
  boundary / stub-linking / description-drift review (orchestrator;
  per-check modules in `scripts/checks/`)
- `scripts/build/build-state.py --check` — CLAUDE.md build-state block in sync
- `file-size-check` — git-tracked files within GitHub thresholds
  (warn 50MB / error 100MB; per `meta/sources-access.md` "Large
  primary-source files (>100MB)")
- `cookies-check` — no Netscape cookies content or Google session
  cookies in tracked files (defensive backstop to `.gitignore` patterns)

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
