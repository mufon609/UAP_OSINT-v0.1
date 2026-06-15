---
name: build
description: Orchestrate a primary-source node build through the multi-agent pipeline — internal/external investigation, archival, verbatim extraction, synthesis, and audit. Use when the user directs a node to be built or rebuilt. Runs on the main thread and dispatches the role subagents; never hand-author a node.
argument-hint: {type}/{slug} "<scope>"
allowed-tools:
  - Agent(internal-investigator, external-investigator, archive, worker, builder, auditor)
  - Skill(prepare-ocr-sibling)
  - Skill(prepare-transcript-sibling)
  - Read
  - Bash(python3 scripts/build/new.py *)
  - Bash(python3 scripts/build/extract-source.py *)
  - Bash(python3 scripts/build/research-scaffold.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/build-state.py *)
  - Bash(python3 scripts/tools/ocr-consensus.py *)
  - Bash(python3 scripts/tools/route_failure.py *)
  - Bash(python3 scripts/checks/_phases.py *)
---

# Build orchestrator

You are the Orchestrator — the main thread. You **cannot** be a subagent
(subagents can't spawn subagents), which is exactly why this is a skill that
runs here and dispatches the role subagents via the Agent tool. You sequence
the roles, scaffold once at the right moment, pass each role's returned stub
to the next, and never hand-author the node. The shared contract
(stub schemas, phases, branches, fix-the-data) is preloaded from
`build-protocol`.

**Relay, don't author — the three handoff rules.**

1. **Relay each step's closed input set verbatim** — the `Pass:` column of the
   table below (named fields quoted verbatim from prior stubs, the target,
   source paths) — and **nothing else**. A stub's optional `notes` block
   (build-protocol → stub-schemas.md "Advisory notes") travels only when the
   whole stub is the relayed unit (e.g. a worker fragment); never extract it
   into another step's named-field set.
2. **Never restate, summarize, or "clarify" a role's policy** — evidentiary
   discipline, entity-linking, quote scope and voice, relevance judgment,
   prose-drift framing. It lives complete in that role's contract
   (`build-protocol` + `.claude/agents/{role}.md`), and a subagent weights its
   just-issued task prompt **above** its standing contract, so any policy you
   improvise into the prompt silently overrides the contract. If you feel the
   urge to explain how a role should decide something, stop — its contract
   already states it.
3. **Never relay a truncated stub.** A role return above the harness
   context-injection cap never arrives whole: the harness persists the full
   return to a session file (`tool-results/*.json`) and hands back a short
   preview plus the path. `Read` the persisted file, confirm it is the
   complete stub, and relay the **path** verbatim (alongside the step's other
   named input fields) — never the preview. The next role `Read`s the same
   bytes.

Why these rules: the failure rule 2 prevents actually happened — an authored
Description dropped every source-attested entity link after the orchestrator
imported the discretionary quote-relevance judgment into the absolute
entity-linking rule. The hazard these rules guard is **policy injection**,
never data transport: the worker writes its fragment **file** and
`scripts/build/merge-fragments.py` copies the verbatim payload into the
artifact byte-exactly, schema fields only — mechanical data transport that
removes the retyping drift surface the verbatim check exists to catch. (An
earlier blanket rejection of disk handoffs conflated the two; policy stays
governed by rule 2, the stub `notes` contract — stub-schemas.md "Advisory
notes" — and the merge script's field filter, which ignores everything a
fragment carries beyond the schema.) No role or orchestrator ever writes a
*policy* handoff file; rule 3's persisted file is written by the harness.

**Target.** `{type}/{slug}` + scope come from the user — per the project
discipline, never invent a build target. If `$ARGUMENTS` is empty, ask what to
build before doing anything.

## The shape — pipeline at a glance

A **map, not a contract**: it carries no normative content of its own. Every
rule lives once in the file linked beside it; if this map ever disagrees with a
linked source, the source wins.

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
  ┌───────────────────────────┐
  │  auditor                  │  fresh-context cold re-read; the built node only
  └─────────────┬─────────────┘
    ▼
  health: pass  ▶  build-state.py --update  ▶  user commits (pre-commit gate)
```

`┌─┐` solid box = an **agent role** (a subagent in `.claude/agents/`).
`╔═╗` double box = an **orchestrator-only step** (no role; the main thread runs it).

### Stages — role ≠ step number

| Step | Stage | Agent role | What it owns | Detail |
|---|---|---|---|---|
| 1 | survey | `internal-investigator` | reuse + gaps; read-only, no web, no manifest | [`agents/internal-investigator.md`](../../agents/internal-investigator.md) |
| 2 | source | `external-investigator` | confirm new sources by reading; no manifest commit | [`agents/external-investigator.md`](../../agents/external-investigator.md) |
| 3 | archive | `archive` | the only manifest writer; download · Wayback · extract | [`agents/archive.md`](../../agents/archive.md) |
| 4 | scaffold | — *orchestrator* | `new.py` + `research-scaffold.py`, once | step 4 below |
| 4b / 4c | sibling gate | — *orchestrator* | OCR / label-less-transcript sibling readiness | steps 4b–4c below |
| 5 | extract | `worker` ×N | the single verbatim boundary; emits fragments | [`agents/worker.md`](../../agents/worker.md) |
| 6 | synthesize | `builder` | merge → organize → link → render; the prose-drift surface | [`agents/builder.md`](../../agents/builder.md) |
| 7 | audit | `auditor` | fresh-context cold re-read of the built node | [`agents/auditor.md`](../../agents/auditor.md) |
| 8 | finalize | — *orchestrator* | refresh build-state; user commits at the gate | step 8 below |

### Branches — when the straight line bends

| Branch | Trigger | Effect | Defined in |
|---|---|---|---|
| all-internal | survey sets `all_internal: true` / `gaps: []` | skip steps 2–3 (no new bytes); sibling gate + scaffold still run | [`build-protocol`](../build-protocol/SKILL.md) "Orchestration branches" |
| failure routing | builder returns `result: fail` | `route_failure.py` maps check → phase → role; re-enter that role, fix the **data**, rebuild | [`build-protocol`](../build-protocol/SKILL.md) "Fix the data, never the node body" |
| `/augment` | user-triggered maintenance change | partial re-entry: skip scaffold, enter directly at the role the change needs | [`augment` skill](../augment/SKILL.md) |

## Sequence

> **Numbering note.** The numbers below are **step** numbers — this file's unit of
> reference — and each step either dispatches a role (named in its `Agent(...)`
> call) or is an *orchestrator-only* step (scaffold · sibling gate · finalize),
> marked as such inline. Step numbers are **not** role numbers: the six roles are
> numbered 1–6 in their own agent descriptions, and that count diverges from the
> steps here because the orchestrator-only steps fall between the role steps. For
> the explicit step ↔ role mapping, see the "Stages" table in "The shape"
> above. This file refers to roles by **name**, never by number.

**Per-step inputs (closed).** Pass exactly the `Pass:` cell — relay only, add no
framing. Field names are the stub fields from `build-protocol/stub-schemas.md`.

| Step → role | Pass (relay verbatim from prior stub / user) | Read back (stub) |
|---|---|---|
| 1 internal-investigator | target `{type}/{slug}` + scope (from user) | `linked_nodes`, `reusable_sources`, `topic_relevance`, `gaps`, `blocking_prep`, `all_internal` |
| 2 external-investigator | `gaps[]`, `linked_nodes` (step-1 stub) | `queued_sources[]` (confirming_span-checked), `unfilled_gaps` |
| 3 archive | `queued_sources[]` (step-2 stub) | `archived[]`, `primary_sources_registered` |
| 5 worker (×N, parallel) | one `{source-path}`, its scratch path, `worker_kind`, `{slug}` | the slim stub (`fragment_path` + `counts`; the fragment file carries the payload) |
| 6 builder | all worker `fragment_path`s; `linked_nodes`, `topic_relevance` (step-1 stub) | `result`, `routed`, `claim_groups`, `validator_findings` |
| 7 auditor | the rendered node path `{type}/{slug}.md` | `health`, `validator_findings` |
| 4b/4c sibling gate *(Skill, not Agent)* | the `{source-path}` (4b) / `{slug}` (4c) — nothing more | a registered, verified sibling |

These are inputs, not interpretation. `linked_nodes` is a **required input
field** for the builder — check that it is present and relayed, not *how* the
builder reads it; the contract owns that. (Step↔role numbering matches the
"Stages" table in "The shape" above.)

**The same rule applies to the sibling sub-skills (4b/4c).** Relay only the
`{source-path}` / `{slug}` to `/prepare-ocr-sibling` / `/prepare-transcript-sibling`
— the sub-skill **and its own agent contracts** (`ocr-page-producer`,
`ocr-page-verifier`; `attribution-producer`, `attribution-verifier`) own the transcription, fill, and
verification discipline. Do not re-author that discipline into the sub-skill
invocation; the relay/contract split holds one level down too.

1. **`Agent(internal-investigator)`** with the target. Read its stub:
   `linked_nodes`, `reusable_sources`, `topic_relevance`, `gaps`,
   `blocking_prep`, `all_internal`.
   - **all-internal branch:** if `all_internal: true` / `gaps: []`, skip
     steps 2–3 (no new-bytes sourcing); scaffold from the reused sources and go
     to step 4. Source-**prep** is not skipped: step 4b (OCR-scan sibling
     readiness) and the canonical scratch extraction still run for any reused
     source. A `blocking_prep` item in the survey stub flags a reused ocr-scan
     source that still needs its sibling.
2. **`Agent(external-investigator)`** with `gaps[]` + `linked_nodes`. Read
   `queued_sources[]`. **Reject any queued source lacking a `confirming_span`**
   — a bare "read it" is not accepted (build-protocol → the non-negotiable invariant).
3. **`Agent(archive)`** with the (validated) `queued_sources[]`. Read
   `archived[]`.
4. **Scaffold once, here** *(orchestrator step — not a role)* — only after sourcing has settled the node's
   classification (person **archetype** / org **kind** / document **form**)
   and the full source set. Two commands, in order:
   - `python3 scripts/build/new.py {type} --slug {slug} --{archetype|kind|form} … --name "…"`
     (the literal `archetype` / `kind` / `doc_form` vocabulary for the type is in `meta/schema.yaml`)
   - `python3 scripts/build/research-scaffold.py --target {type}/{slug} --sources {ALL reuse + archived paths}`
     (it writes fresh and cannot append, so every source goes in this one call)
   - then `python3 scripts/build/validate-research.py --phase archive meta/research/{slug}.yaml`
     (the artifact's first validation).
   - *(The scaffolder is hook-gated: one new person/org node per session; all
     other types may batch — build-protocol → "One new synthesis-heavy node per
     session" enumerates them. Don't work around it.)*
4b. **OCR-scan sibling gate** *(orchestrator step — before any Worker)*. Read
   the manifest entry for each primary source. A source flagged
   `extraction_type: ocr-scan` / `extraction-lossy` without a verified
   same-stem `.txt` sibling is **not worker-ready** (its extract layer is
   corrupt): **invoke `/prepare-ocr-sibling {source-path}` via the Skill
   tool**; if that invocation fails, **HALT** and direct the user to run it
   (the why + the produce→independently-verify→register contract:
   build-protocol → "Some primary sources need a verified sibling"). A source
   whose verified sibling **already exists** (a reuse) still gets one command:
   `python3 scripts/tools/ocr-consensus.py verify {source-path} --stamp-artifact
   meta/research/{slug}.yaml` — it lands `content_block` on the fresh artifact
   mechanically and re-confirms the sibling against the engines (seconds on
   the engine cache; the `ocr_sibling_presence` check is the commit-boundary
   backstop). This gate
   runs **regardless of the all-internal branch** — all-internal skips
   new-bytes sourcing, not source-prep. Text-native sources need no sibling. Once the
   sibling gates (4b/4c) clear, produce the canonical worker scratches —
   an orchestrator action, one run:
   `python3 scripts/build/extract-source.py --artifact meta/research/{slug}.yaml`
   writes the `/tmp/scratch-{slug}-N.txt` path for every primary source
   (these are the scratch paths relayed to the workers) and prefers the
   verified `.txt` sibling for an ocr-scan source.
4c. **Transcript sibling gate** *(orchestrator step — same shape as 4b)*.
   Only `transcript_provenance: stenographic` / `published-transcript`
   sources carry trustworthy inline labels and skip this gate. **Every
   other transcript source** — `auto-caption`, `human-corrected-caption`,
   an explicit `unknown`, or an absent flag (classify an unclassified
   source in the manifest while here) — without a verified
   `-attribution.yaml` sibling is **not worker-ready for `speaker_id`** (the
   caption carries verbatim text but no attribution): **invoke
   `/prepare-transcript-sibling {slug}` via the Skill tool**; if that
   invocation fails, **HALT** and direct the user to run it. Runs regardless
   of the all-internal branch. Unlike 4b the verbatim source is unchanged —
   `extract-source.py --artifact` still pulls from the caption file; the
   sibling adds the attribution layer `validate-research.py` matches
   `speaker_id` against (the `transcript_sibling_presence` check is the
   commit-boundary backstop for this gate).
5. **`Agent(worker)` once per source, in parallel** — issue the worker calls
   in a single message so they run concurrently; each writes its fragment
   file and returns a slim stub (`fragment_path` + `counts` — it does not
   write the artifact). Collect every fragment path.
6. **`Agent(builder)`** — Pass per the table: all worker fragment paths, plus
   `linked_nodes` + `topic_relevance` from the step-1 stub.
   `linked_nodes` is a required *input* — relay it; do not describe how it is
   used (the contract owns that). The builder merges the fragment files via
   `merge-fragments.py` (byte-exact mechanical transport), runs the
   extract check, then organize → link → render. Read its stub.
   - **On `result: fail`:** run
     `python3 scripts/tools/route_failure.py {failing_check_names}`, re-enter
     the owning role it names (Worker for `extract`, Builder for
     `organize`/`link`/`render`, Archive for `archive`), apply the data fix,
     and rebuild. (This is the dissolved Error agent — a lookup, not a role.)
6b. **Quote-corroboration stamp** *(orchestrator step — after the builder,
   before the auditor)*. For each sibling-backed source the artifact now
   quotes (every 4b source), run
   `python3 scripts/tools/ocr-consensus.py corroborate-quotes {source-path}
   --artifact meta/research/{slug}.yaml` — it re-checks just the quoted spans
   against the engine reads (seconds on the cache 4b warmed) and stamps the
   canonical `quote_corroboration` value, enumerating the contested /
   PaddleOCR-filled-page tokens the auditor must settle against the page
   images. The `quote_ocr_corroboration` check is the commit-boundary
   backstop; the stamp is the auditor's target list, so it must land before
   step 7.
7. **`Agent(auditor)`** on the rendered node. The auditor's scope is the
   built node only, and it is recommend-only as a build role
   (`agents/auditor.md`): relay its findings to the user in the final report.
   A failing check routes through `route_failure.py` exactly as in step 6.
   An auditor recommendation that fails **no** check (e.g. a locator-precision
   note) is applied by re-entering the Builder with the finding relayed
   verbatim; green gates on the re-render close it — no fresh audit pass (the
   fix's wording originated with the auditor).
   Any change to a node *other than the one being built* is out of scope for
   a build — it runs as its own user-directed `/augment` session.
8. **Finalize** *(orchestrator step — not a role)* — done when the auditor reports
   `health: pass`. A node was added/changed, so refresh the
   build-state snapshot at `meta/build-state.md`
   (`python3 scripts/build/build-state.py --update`) — the
   build-state gate (`--check`) is otherwise red at commit. Report the built
   node and a short summary of each role's returned stub. (Stubs are return
   values the orchestrator reads as it goes — handoff rules in "Relay, don't
   author" above.)

The user commits when ready (the pre-commit gate runs at the commit boundary).
