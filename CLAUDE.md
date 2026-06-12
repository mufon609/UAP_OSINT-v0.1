# CLAUDE.md — Session-start checklist

*Contributor session checklist for Claude Code — read order, health
check, build state, session rules, enforcement warnings. No reference
tables; those live with their owners.*

Read this file at the start of every Claude Code session that involves
**building, auditing, or iterating** on repository content.

**If you are instead *querying* the repo to answer a user's question** —
not modifying content — read `AGENTS.md` at the repo root first: the
consumer-agent entry point (query protocol, research-artifact layer,
task routing). CLAUDE.md below assumes a contributor session.

---

## 1. Read the governing docs

In order:

1. `README.md` — what this repository is / is not (the epistemic standard + Status markers)
2. `meta/schema.yaml` — machine-readable node spec (types, kinds, archetypes, required sections, vocabularies); `meta/schema-research-artifact.yaml` — the research-artifact spec (drives `validate-research.py`)
3. `meta/memory.md` — cross-cutting contributor working knowledge (behavioral patterns that don't fit a more specific surface)
4. `meta/topic/research-queue.md` — current priority build queue
5. `meta/roadmap.md` + `meta/BACKLOG.md` — active work + deferred items; note anything relevant to this session

Don't skip. Governance docs change between sessions.

---

## 2. Health check

Before building anything:

```
python3 scripts/build/validate.py            # node structure + verbatim quotes
python3 scripts/build/validate-research.py    # artifact structure + prose-drift
python3 scripts/build/review-coverage.py --all  # cross-layer coverage/boundary/description-drift
python3 scripts/build/build-state.py --check  # meta/build-state.md snapshot in sync
bash scripts/tests/pre-commit.sh             # full gate chain (subsumes the four above + more); ALSO runs inside `git commit` via .githooks/pre-commit (auto-armed; bypass routes denied — un-bypassable by --no-verify)
```

Exit 0 on all = repo healthy. Any errors → fix first. Don't stop at
`validate.py`: the artifact validator carries the prose-drift family and
the coverage review carries the cross-layer checks, and `pre-commit.sh`
adds the `renderer-coverage.py` and `phase_routing_parity.py` gates a
node-only pass never runs — so a node-only pass can read clean while
artifact-level warnings stand.

---

## 3. Current build state

The corpus snapshot — every node with its status and archetype/kind —
lives at `meta/build-state.md` (auto-generated; do not hand-edit).
Regenerate after any node add / remove / status change:

```
python3 scripts/build/build-state.py --update
```

The pre-commit chain runs `--check` to keep the snapshot in sync.

---

## 4. Ask the user what to build

Do not scaffold nodes without direction from the user. The priority queue
at `meta/topic/research-queue.md` is a suggestion, not a mandate. Confirm
scope, archetype/kind selection, and primary-source availability before
starting.

**One *new* person/organization node per build session.** Do not
scaffold a second until the first is fully populated, passes
`validate.py`, and is committed; lighter node types may scaffold in
batches, and edits/audits/rebuilds/sweeps are unrestricted for any
type. Rule owner — rationale and the synthesis-heavy/lighter split:
`.claude/skills/build-protocol/SKILL.md` ("One new synthesis-heavy
node per session"); hook-enforced at the scaffolder.

**Source-read-first — hard rule.** Every `✅ Confirmed — verified verbatim`
quote rests on text extracted from the archived source file *in this
session* — never training knowledge. The verbatim-quote check in
`scripts/build/validate.py` verifies this mechanically. Rule owner:
`.claude/skills/build-protocol/SKILL.md` ("Source-read-first").

---

## 5. Build path and toolkit

**The default build path is the `/build` skill** — the orchestrator runs
on the main thread and dispatches the role subagents in
`.claude/agents/` (internal-investigator · external-investigator ·
archive · worker · builder · auditor); never hand-author a node. The
standalone skills: `/audit`, `/augment`, `/verify-transcript`,
`/quote-relevance-audit`, `/archive-sweep`, `/prepare-ocr-sibling`,
`/prepare-transcript-sibling`, `/fork-init`.

The owners of the operational detail:

- Pipeline map — steps, stages, branches: `.claude/skills/build/SKILL.md`
  ("The shape")
- Shared build contract — invariants, phases, handoff stubs:
  `.claude/skills/build-protocol/SKILL.md`
- Per-script reference — every script in all six subdirectories, with
  flags and design notes: `scripts/README.md`

---

## 6. Hand-edits to node bodies are blocked

Rendered node bodies (`/people/`, `/organizations/`, `/documents/`, …)
are regenerated from their research artifacts — never hand-edited. A
committed `settings.json` deny rule plus a PreToolUse hook block the
Edit/Write path. To change a node: fix the artifact under
`meta/research/` and re-render with `build-from-research.py`, or run
`/augment` for a targeted maintenance change. `git commit` runs the full
pre-commit chain at commit execution time (`.githooks/pre-commit`,
auto-armed by the commit guard, which denies `--no-verify` and the other
bypass routes — so a compound fix-then-commit is gated on its post-fix
state); scaffolding a second uncommitted new
person/organization node is also hook-blocked (the
one-new-synthesis-node rule, §4).
