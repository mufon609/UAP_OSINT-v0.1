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

This file opens with an at-a-glance **map** of the pipeline (next section), then
the **rationale** behind it. The contract statements themselves —
source-read-first, the orchestration branches, the handoff schema — live once in
`.claude/skills/build-protocol/SKILL.md` and are *cited* here, not restated.

---

## The shape — pipeline at a glance

This section is a **map, not a contract**: it carries no normative content of its
own. Every rule lives once in the file linked beside it; if this map ever
disagrees with a linked source, the source wins. Read it to see the whole flow
and find where each piece is defined — then follow the link for the detail.

```text
  user ▶ /build {type}/{slug} "<scope>"
    │
    ▼
  ┌───────────────────────────┐
  │  internal-investigator    │  reuse survey, read-only
  └─────────────┬─────────────┘  ── all_internal (gaps:[]) ▶ skip the next two
    │                              stages, jump to scaffold (sibling gate still runs)
    ▼
  ┌───────────────────────────┐
  │  external-investigator    │  confirm each new source by reading it
  └─────────────┬─────────────┘
    ▼
  ┌───────────────────────────┐
  │  archive                  │  the only manifest writer
  └─────────────┬─────────────┘
    ▼
  ╔═══════════════════════════╗
  ║  scaffold  (once)         ║  orchestrator step, not a role
  ╚═════════════╤═════════════╝
    ▼
  ╔═══════════════════════════╗
  ║  sibling gate  4b / 4c    ║  OCR-scan or label-less transcript?
  ╚═════════════╤═════════════╝  ▶ /prepare-*-sibling   (runs even on all_internal)
    ▼
  ┌───────────────────────────┐
  │  worker  ×N  (parallel)   │  the single verbatim boundary; emits fragments
  └─────────────┬─────────────┘
    ▼
  ┌───────────────────────────┐  merge → organize → link → render
  │  builder                  │  ── on fail ▶ route_failure.py ▶ re-enter owning role
  └─────────────┬─────────────┘
    ▼
  ┌───────────────────────────┐  fresh-context cold re-read
  │  auditor                  │  ── adjacent flagged ▶ tightening loop:
  └─────────────┬─────────────┘     re-enter worker / builder, skip ext + archive
    ▼
  health: pass & no adjacents  ▶  build-state.py --update  ▶  user commits (pre-commit gate)
```

`┌─┐` solid box = an **agent role** (a subagent in `.claude/agents/`).
`╔═╗` double box = an **orchestrator-only step** (no role; the main thread runs it).

### Stages — role ≠ step number

The `/build` **step** numbers and the **role** numbers (roles 1–6, as numbered in
each agent's description) deliberately diverge: step 4 is *scaffold* (no role),
while role 4 is the *worker*. Read this table, not the numbers, to map one to the
other.

| `/build` step | Stage | Agent role | What it owns | Detail |
|---|---|---|---|---|
| 1 | survey | `internal-investigator` | reuse + gaps; read-only, no web, no manifest | [`agents/internal-investigator.md`](../.claude/agents/internal-investigator.md) |
| 2 | source | `external-investigator` | confirm new sources by reading; no manifest commit | [`agents/external-investigator.md`](../.claude/agents/external-investigator.md) |
| 3 | archive | `archive` | the only manifest writer; download · Wayback · extract | [`agents/archive.md`](../.claude/agents/archive.md) |
| 4 | scaffold | — *orchestrator* | `new.py` + `research-scaffold.py`, once | [`build/SKILL.md`](../.claude/skills/build/SKILL.md) step 4 |
| 4b / 4c | sibling gate | — *orchestrator* | OCR / label-less-transcript sibling readiness | [`build/SKILL.md`](../.claude/skills/build/SKILL.md) steps 4b–4c |
| 5 | extract | `worker` ×N | the single verbatim boundary; emits fragments | [`agents/worker.md`](../.claude/agents/worker.md) |
| 6 | synthesize | `builder` | merge → organize → link → render; the prose-drift surface | [`agents/builder.md`](../.claude/agents/builder.md) |
| 7 | audit | `auditor` | fresh-context cold re-read; adjacent-node propagation | [`agents/auditor.md`](../.claude/agents/auditor.md) |
| 8 | finalize | — *orchestrator* | refresh build-state; user commits at the gate | [`build/SKILL.md`](../.claude/skills/build/SKILL.md) step 8 |

### Branches — when the straight line bends

| Branch | Trigger | Effect | Defined in |
|---|---|---|---|
| all-internal | survey sets `all_internal: true` / `gaps: []` | skip steps 2–3 (no new bytes); sibling gate + scaffold still run | [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Orchestration branches" |
| failure routing | builder returns `result: fail` | `route_failure.py` maps check → phase → role; re-enter that role, fix the **data**, rebuild | [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Fix the data, never the node body" |
| tightening loop | auditor flags `adjacent_needs_update[]` | re-enter worker (extract) or builder (derived field), skip external + archive, re-audit | [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Partial re-entry" |
| `/augment` | user-triggered maintenance change | same partial-re-entry contract, entered directly at the role the change needs | [`augment` skill](../.claude/skills/augment/SKILL.md) |

### Cross-cutting contracts — true at every stage

Defined once, obeyed everywhere; not restated per role:

- **Gates read disk, not memory** — a fresh-context subagent can't fabricate a quote → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "The non-negotiable invariant"
- **Source-read-first** — inclusion judged on source content, hard-enforced at `extract` → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Source-read-first"
- **Handoff = return value** — each role returns its stub; no file is written for the handoff → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Handoff stubs" · [`stub-schemas.md`](../.claude/skills/build-protocol/stub-schemas.md)
- **Fix the data, never the node body** — the body is regenerated, never hand-edited → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Fix the data, never the node body"
- **References run downward** — the four-tier linking contract → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Tier linking contract" · [`conventions.md`](../meta/conventions.md) "Tier model and linking contract"
- **One new synthesis-heavy node per session** — hook-enforced on the scaffolder → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "One new synthesis-heavy node per session"
- **Phase vocabulary** — generated from `scripts/checks/_phases.py`, not memorized → [`build-protocol`](../.claude/skills/build-protocol/SKILL.md) "Build phases"

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

**Mechanical enforcement vs. role discipline (verified).** Whole-tool
*absence* from a role's `tools:` binds hard — the Worker genuinely has no
Write/Bash; the investigators have no WebFetch/WebSearch. But **per-command
scoping inside `tools:` is advisory** in the current Claude Code environment: a
role carrying any `Bash(...)` entry effectively gets full Bash, so the
"no manifest-write" / "no web-via-curl" lines above rest on **role discipline**,
not a hard gate (empirically, roles asked to cross those lines could). The
mechanical floor is therefore *not* the per-command `tools:` scoping but: (1)
committed `settings.json` `permissions.deny` rules, which **do** bind for
subagents and hot-reload; and (2) the disk-truth gate (verbatim + prose-drift)
enforced un-bypassably at the commit boundary. Nothing commits red, so a rogue
web-pull or manifest-write cannot yield a passing quote — the gate re-derives
truth from disk regardless of which role touched what.

Two former roles **dissolved**: the Orchestrator (a control loop, now the
`/build` skill) and the Error agent (a `check → phase → role` lookup, now
`scripts/tools/route_failure.py` driven by `scripts/checks/_phases.py`).

## Source-read-first

Stated once in `build-protocol` (*Source-read-first*): content-not-URL inclusion,
hard-enforced at the `extract` phase, load-bearing-ness judged in context. The *why*
it can be trusted — the gate re-reads disk, not agent memory, so a fresh-context
subagent cannot fabricate a quote — is `build-protocol`'s *non-negotiable invariant*.
That disk-truth property is the keystone the whole role decomposition rests on.

## Phase vocabulary

Each `--phase` token names the role whose output it validates; `--phase` only ever
**narrows** a run (an unflagged run is the full pass). The check → phase map **and the
one-line description of each phase** live in `scripts/checks/_phases.py` — the single
source of truth; run `python3 scripts/checks/_phases.py --list-phases` for the live
list. The canonical phase tokens are enumerated here (so `phase_routing_parity.py` can
confirm none ships undocumented), but their descriptions are **not** restated — read
them from `--list-phases`:

- `archive` · `extract` · `organize` · `link` · `render`

`preflight` (parse / structure) runs in every phase.

## Orchestration branches

The three branches — **all-internal** (internal survey skips external + archive),
the auditor-triggered **tightening loop**, and user-triggered **`/augment`** — and the
**partial-re-entry** contract they share (skip scaffold, run only the roles a change
needs, route failures to the owning role, preserve contradictions) are specified once
in `build-protocol` (*Orchestration branches*). The rationale: a change re-enters at
the phase its material demands, never a fresh scaffold — the cheapest correct path.

## Fix the data, never the node body — how it's enforced

The rule (regenerate the body from the artifact; route a failing check via
`route_failure.py` to its owning role; the fix target is always artifact data) is in
`build-protocol`. What lives here is *why it actually holds*. A hand-edit to a node
body is blocked two ways. The mechanical gate is a committed `settings.json`
`permissions.deny` rule on the node-type directories — it binds for the main thread
*and* subagents (the `builder` is the one role holding `Edit`), and the renderer is
unaffected because it writes the body via Python file I/O, not the Edit/Write tool. A
`PreToolUse` hook (`.claude/hooks/block_node_body_edit.sh`) is the main-thread
backstop, carrying the fix-pointing message. (The hook alone is insufficient: a
`settings.json` `PreToolUse` hook does **not** fire for a *subagent's* tool call, so
the deny rule is what actually gates the builder.) Two more hooks back the discipline
— and these gate main-thread actions, so the hook mechanism is sufficient: a `git
commit` runs the full pre-commit chain and blocks on any red gate (un-bypassable by
`--no-verify`), and scaffolding a second uncommitted new person/organization node is
blocked (the one-new-synthesis-node-per-session rule).

## Handoff

The return-value-*is*-the-handoff mechanism (each role returns its stub per
`build-protocol`'s *Handoff stubs* + `stub-schemas.md`; no file is written for it)
keeps the durable record in one place — the manifest, artifact, and git.
