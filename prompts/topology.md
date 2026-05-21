# Build topology — design rationale

This is the **why** behind the multi-agent node build. The **how** is live in
the toolkit:

- **Orchestrator** → the `/build` skill (`.claude/skills/build/`). It runs on
  the main thread and dispatches the role subagents (a subagent can't spawn
  subagents, so the orchestrator must be the main thread).
- **Role subagents** → `.claude/agents/{internal-investigator,external-investigator,archive,worker,builder,auditor}.md`.
- **Shared contract** (handoff-stub schemas, phase vocabulary, source-read-first,
  fix-the-data, branches) → preloaded into every role from
  `.claude/skills/build-protocol/` (so no role restates it).

`prompts/build.md` remains the single-session fallback for a build that
shouldn't be decomposed.

---

## Why these roles (capability boundaries, not feedback granularity)

Each role is a distinct **capability boundary** that makes the discipline
mechanical — the separation *is* the enforcement:

| Role (subagent) | Capability boundary it enforces |
|---|---|
| `internal-investigator` | read-only; no web tools, no manifest-write → an "archived-only" reuse survey that can't quietly pull from the web |
| `external-investigator` | web-enabled, but no manifest commit; its read is re-checkable (returns a verbatim `confirming_span`, not a bare "I read it") |
| `archive` | the only role that writes the manifest |
| `worker` | the single phase that introduces verbatim quotes; emits a fragment, never writes the shared artifact (so parallel workers can't race) |
| `builder` | the synthesis / prose-drift surface; edits only the artifact, never the node body; serializes the worker-fragment merge |
| `auditor` | a fresh-context cold re-read — the independent verifier the producing role can't be |

Two former roles **dissolved**: the Orchestrator (a control loop, now the
`/build` skill) and the Error agent (a `check → phase → role` lookup, now
`scripts/tools/route_failure.py` driven by `scripts/checks/_phases.py`).

## Source-read-first

Every inclusion decision is made against source **content**, never a URL or
title. Soft-enforced where sources are surveyed/fetched; **hard-enforced at the
`extract` phase**, where the verbatim check matches every emitted quote against
the archived + extracted file (the gate reads disk, not agent memory — which is
why fresh-context subagents are safe). Load-bearing-ness is judged in context:
the internal survey assembles the `linked_nodes` + topic-relevance framing and
threads it forward; no role judges relevance from a source in isolation.

## Phase vocabulary

Each `--phase` token names the role whose output it validates. The map from
check → phase lives in `scripts/checks/_phases.py` (the single source of truth);
run `python3 scripts/checks/_phases.py --list-phases` for the live list. The
canonical phases: `archive` (manifest + primary_sources), `extract` (verbatim
quotes / speakers), `organize` (free-prose synthesis), `link` (cross-reference
surfaces + prose-drift), `render` (render-time structure + cross-layer checks).
`preflight` (parse/structure) runs in every phase. `--phase` only ever
**narrows** a run; an unflagged run is the full pass.

## Orchestration branches

- **all-internal** — the internal survey sets `all_internal: true` → external +
  archive are skipped.
- **tightening loop** — the audit flags `adjacent_needs_update[]` with
  `skip_external: true` → re-enter at `extract` (the material is already
  archived; no new URL, no new bytes), rebuild, re-audit.

## Fix the data, never the node body — now enforced, not just stated

The node body is regenerated from the artifact; a hand-edit to a node body is
blocked by a `PreToolUse` hook (`.claude/hooks/block_node_body_edit.sh`). When a
check fails, `route_failure.py` maps it to the owning role and the fix target is
always artifact data. Two more hooks back the discipline: a `git commit` runs
the full pre-commit chain and blocks on any red gate (un-bypassable by
`--no-verify`), and scaffolding a second uncommitted new person/organization
node is blocked (the one-new-synthesis-node-per-session rule).

## Handoff

Each role returns its stub (schema in
`.claude/skills/build-protocol/stub-schemas.md`) as its value to the
orchestrator, and also writes it to `/tmp/handoff-{slug}-{role}.yaml` as an
audit trail. `/tmp` is never committed — the manifest, artifact, and git remain
the source of truth.
