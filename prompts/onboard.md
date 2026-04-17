# Onboard prompt

Paste into a fresh Claude Code session when starting work on this
repository for the first time in a session.

---

You are joining a primary-source investigation knowledge base. Before
doing anything:

1. Read `README.md` — what this repository is.
2. Read `meta/conventions.md` — the evidentiary discipline.
3. Read `meta/schema.yaml` — the machine-readable spec for node types,
   required sections, vocabularies.
4. Read `CONTRIBUTING.md` — how to build a node.
5. Read `meta/topic/research-queue.md` — current priority queue.

Then run the health check:

```
python3 scripts/validate.py
python3 scripts/build-state.py --check
```

Both should exit 0. If errors exist, report them and stop.

Then:

1. Report the current build state (node counts per type) summarized
   from `CLAUDE.md`.
2. Summarize the top 3 items in `meta/topic/research-queue.md` Priority Build
   Queue with rationale.
3. Ask the user what to build or what task to run.

Do not begin scaffolding nodes without explicit direction from the user.
