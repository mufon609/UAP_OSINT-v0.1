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
  - Bash(python3 scripts/build/research-scaffold.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/build-state.py *)
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

**Relay, don't author — the one handoff rule.** Every role's policy —
evidentiary discipline, entity-linking (stub-never-null), quote scope and
voice, relevance judgment, prose-drift framing — already lives complete and
correct in that role's contract (`build-protocol` + `.claude/agents/{role}.md`).
At each handoff your job is to **relay the step's closed input set** (the
`Pass:` column of the table below — named fields quoted verbatim from prior
stubs, the target, source paths) and **nothing else**. Do not restate,
summarize, re-derive, or "clarify" *how* a role should judge linking,
relevance, quote scope, or prose-drift: a subagent weights its just-issued task
prompt **above** its standing contract, so any policy you improvise into the
prompt silently overrides the contract. The recurring failure this prevents: an
authored Description dropped every source-attested entity link after the
orchestrator imported the discretionary quote-relevance judgment ("judge
load-bearing-ness") into the absolute entity-linking rule. If you feel the
urge to explain how a role should decide something,
stop — that judgment is the role's, and its contract already states it. Relay
stub fields verbatim; do not paraphrase them.

A disk-stub transport (the pre-skills-migration `/tmp/handoff-{slug}-{role}.yaml`
files) was evaluated and **rejected** as the fix for this hazard: it transports
stub *data* losslessly but does nothing to stop the orchestrator adding policy
prose alongside the file path — it addresses data fidelity, not the
policy-injection hazard — and the verbatim-boundary roles (the worker has no
Write tool) cannot satisfy a role-written handoff file, so reintroducing it
would either puncture that capability boundary or reverse the "no file is
written for the handoff" principle for zero gain on the real hazard. Its one
legitimate kernel — relay the stub verbatim, never paraphrase — is the rule
above.

One disk path does exist, and it is **not** the rejected design: the
**harness itself** persists an oversized role return to a session file
(`tool-results/*.json`) and hands back a short preview plus the path — a
return value above the context-injection cap never arrives whole in-context.
When that happens, **never relay the truncated preview as if it were the
stub**: `Read` the persisted file, confirm it is the complete fragment, and
relay the persisted path verbatim (alongside the step's other named input
fields) to the next role, which `Read`s the same bytes. The relay stays
byte-identical, no role wrote a file, and the orchestrator authored nothing —
both principles above hold.

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
  ┌───────────────────────────┐  fresh-context cold re-read
  │  auditor                  │  ── adjacent flagged ▶ report to user; tightening
  └─────────────┬─────────────┘     loop only on user direction (skip ext + archive)
    ▼
  health: pass  ▶  report adjacents to user  ▶  build-state.py --update  ▶  user commits (pre-commit gate)
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
| 7 | audit | `auditor` | fresh-context cold re-read; adjacent-node propagation | [`agents/auditor.md`](../../agents/auditor.md) |
| 8 | finalize | — *orchestrator* | refresh build-state; user commits at the gate | step 8 below |

### Branches — when the straight line bends

| Branch | Trigger | Effect | Defined in |
|---|---|---|---|
| all-internal | survey sets `all_internal: true` / `gaps: []` | skip steps 2–3 (no new bytes); sibling gate + scaffold still run | [`build-protocol`](../build-protocol/SKILL.md) "Orchestration branches" |
| failure routing | builder returns `result: fail` | `route_failure.py` maps check → phase → role; re-enter that role, fix the **data**, rebuild | [`build-protocol`](../build-protocol/SKILL.md) "Fix the data, never the node body" |
| tightening loop | auditor flags `adjacent_needs_update[]` **and the user directs the fix** | re-enter worker (extract) or builder (derived field), skip external + archive, re-audit | [`build-protocol`](../build-protocol/SKILL.md) "Partial re-entry" |
| `/augment` | user-triggered maintenance change | same partial-re-entry contract, entered directly at the role the change needs | [`augment` skill](../augment/SKILL.md) |

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
| 1 internal-investigator | target `{type}/{slug}` + scope (from user) | `linked_nodes`, `reusable_sources`, `gaps`, `blocking_prep`, `all_internal` |
| 2 external-investigator | `gaps[]`, `linked_nodes` (step-1 stub) | `queued_sources[]` (confirming_span-checked), `unfilled_gaps` |
| 3 archive | `queued_sources[]` (step-2 stub) | `archived[]` + scratch paths, `primary_sources_registered` |
| 5 worker (×N, parallel) | one `{source-path}`, its scratch path, `worker_kind`, `{slug}` | the fragment (`quotes`, `cross_ref_candidates`, `background_material`, `cited_works`) |
| 6 builder | all worker fragments; `linked_nodes`, `topic_relevance`, `reusable_sources` (step-1 stub) | `result`, `claim_groups`, `validator_findings` |
| 7 auditor | the rendered node path `{type}/{slug}.md` | `health`, `adjacent_needs_update[]` |
| 4b/4c sibling gate *(Skill, not Agent)* | the `{source-path}` (4b) / `{slug}` (4c) — nothing more | a registered, verified sibling |

These are inputs, not interpretation. `linked_nodes` is a **required input
field** for the builder — check that it is present and relayed, not *how* the
builder reads it; the contract owns that. (Step↔role numbering matches the
"Stages" table in "The shape" above.)

**The same rule applies to the sibling sub-skills (4b/4c).** Relay only the
`{source-path}` / `{slug}` to `/prepare-ocr-sibling` / `/prepare-transcript-sibling`
— the sub-skill **and its own agent contracts** (`ocr-page-producer`,
`ocr-page-verifier`, the attribution agents) own the transcription, fill, and
verification discipline. Do not re-author that discipline into the sub-skill
invocation; the relay/contract split holds one level down too.

1. **`Agent(internal-investigator)`** with the target. Read its stub:
   `linked_nodes`, `reusable_sources`, `gaps`, `all_internal`.
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
   `archived[]` + the scratch paths.
4. **Scaffold once, here** *(orchestrator step — not a role)* — only after sourcing has settled the node's
   classification (person **archetype** / org **kind** / document **form**)
   and the full source set. Two commands, in order:
   - `python3 scripts/build/new.py {type} --slug {slug} --{archetype|kind|form} … --name "…"`
   - `python3 scripts/build/research-scaffold.py --target {type}/{slug} --sources {ALL reuse + archived paths}`
     (it writes fresh and cannot append, so every source goes in this one call)
   - then `python3 scripts/build/validate-research.py --phase archive meta/research/{slug}.yaml`
     (the artifact's first validation).
   - *(The scaffolder is hook-gated: a second uncommitted new person/org node
     in one session is blocked. Lighter types may batch. Don't work around it.)*
4b. **OCR-scan sibling readiness — gate before the Worker.** A primary source
   flagged `extraction_type: ocr-scan` / `extraction-lossy` (manifest) is **not
   worker-ready**: its extract layer is corrupt, so a quote pulled from it is
   garbage or trips the verbatim gate (the why + the
   produce→independently-verify→register contract: build-protocol →
   "Some primary sources need a verified sibling"). Read the manifest entry for
   each primary source; any ocr-scan / extraction-lossy source lacking a
   verified same-stem `.txt` sibling MUST get one before the Worker. This is the
   orchestrator's responsibility, **never the Worker's** (the Worker has no Write
   tool), and it runs **regardless of the all-internal branch** — all-internal
   skips new-bytes sourcing (external + archive), not source-prep. The remedy is
   the **`/prepare-ocr-sibling`** skill, which produces, independently verifies,
   and registers the sibling: **invoke `/prepare-ocr-sibling {source-path}` via
   the Skill tool — you are the main thread, so you can.** Only if your
   environment cannot dispatch a skill from here, **HALT** and direct the user to
   run it. Either way, do it before handing the Worker a corrupt extract. Once
   every ocr-scan source has a verified sibling, the canonical scratch comes from
   `extract-source.py --artifact` (it prefers the sibling). Text-native sources
   need no sibling.
4c. **Transcript sibling readiness — gate before the Worker.** A primary source
   flagged `transcript_provenance: auto-caption` / `human-corrected-caption`
   (label-less; no inline speaker labels) is **not worker-ready for `speaker_id`**:
   the caption file carries the verbatim text but no built-in attribution, so
   `speaker_id` on quotes cannot be derived from it alone (the why + the
   produce→independently-verify→register contract: build-protocol →
   "Some primary sources need a verified sibling"). Read the manifest entry for
   each primary source; any label-less transcript source lacking a verified
   `-attribution.yaml` sibling MUST get one before the Worker. Same shape as 4b:
   orchestrator's responsibility, **never the Worker's**, and it runs
   **regardless of the all-internal branch**. The remedy is the
   **`/prepare-transcript-sibling`** skill, which runs the agent-based
   attribution pipeline (semantic parse → structural validate → independent
   verify → conditional image-verification backstop) and registers the paired
   sibling: **invoke `/prepare-transcript-sibling {slug}` via the Skill tool
   — you are the main thread, so you can.** Only if your environment cannot
   dispatch a skill from here, **HALT** and direct the user to run it.
   Either way, do it before the Worker emits a speaker-attributed quote.
   Unlike 4b, the verbatim source is unchanged — `extract-source.py
   --artifact` still pulls from the auto-caption file; the sibling YAML adds
   the attribution layer `validate-research.py` matches `speaker_id` against
   (indexed by line range into the source file). Labeled sources
   (`stenographic` / `published-transcript`) need no sibling.
5. **`Agent(worker)` once per source, in parallel** — issue the worker calls
   in a single message so they run concurrently; each returns a fragment (it
   does not write the artifact). Collect every fragment.
6. **`Agent(builder)`** — Pass per the table: all worker fragments, plus
   `linked_nodes` + `topic_relevance` + `reusable_sources` from the step-1 stub.
   `linked_nodes` is a required *input* — relay it; do not describe how it is
   used (the contract owns that). The builder merges the fragments, runs the
   extract check, then organize → link → render. Read its stub.
   - **On `result: fail`:** run
     `python3 scripts/tools/route_failure.py {failing_check_names}`, re-enter
     the owning role it names (Worker for `extract`, Builder for
     `organize`/`link`/`render`, Archive for `archive`), apply the data fix,
     and rebuild. (This is the dissolved Error agent — a lookup, not a role.)
7. **`Agent(auditor)`** on the rendered node.
   - **Adjacent flags are recommendations, not work orders.** The auditor is
     recommend-only as build role 6 (`agents/auditor.md`): relay its
     `adjacent_needs_update[]` entries to the user in the final report and
     stop — do not enter the tightening loop on your own. A cross-node sweep
     is a scope decision the user owns, and an auditor premise can be wrong
     (a flagged 26-node gap once proved 24/26 already-correct on the
     builder's disk re-check); the entries lose nothing by waiting in the
     report.
   - **tightening-loop branch (user-directed only):** when the user directs a
     flagged fix, for each `adjacent_needs_update[]` entry with
     `skip_external: true`, re-enter at the Worker (shape a — extract from the
     already-archived scratch) or the Builder (shape b — a stale derived field,
     no extraction), rebuild, and re-audit. External + Archive are skipped (no
     new URL, no new bytes). A sweep wider than the built node's immediate
     adjacents runs as its own user-directed `/augment` session instead.
8. **Finalize** *(orchestrator step — not a role)* — done when the auditor reports
   `health: pass`; any `adjacent_needs_update[]` entries ride in the final
   report for the user to direct and do not block finalize. A node was added/changed, so refresh the
   build-state block (`python3 scripts/build/build-state.py --update`) — the
   build-state gate (`--check`) is otherwise red at commit. Report the built
   node and a short summary of each role's returned stub. (Stubs are return
   values — the orchestrator reads each as it goes; no role or orchestrator
   writes a handoff file. The one disk case is a harness-persisted oversized
   return — relay the persisted path, never the preview; see the transport
   note after the disk-stub-rejection paragraph above.)

The user commits when ready (the pre-commit gate runs at the commit boundary).
