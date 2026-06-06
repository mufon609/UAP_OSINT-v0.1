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

**Target.** `{type}/{slug}` + scope come from the user — per the project
discipline, never invent a build target. If `$ARGUMENTS` is empty, ask what to
build before doing anything.

## Sequence

> **Numbering note.** The numbers below are **step** numbers — this file's unit of
> reference — and each step either dispatches a role (named in its `Agent(...)`
> call) or is an *orchestrator-only* step (scaffold · sibling gate · finalize),
> marked as such inline. Step numbers are **not** role numbers: the six roles are
> numbered 1–6 in their own agent descriptions, and that count diverges from the
> steps here because the orchestrator-only steps fall between the role steps. For
> the explicit step ↔ role mapping, see the table in
> `../../../prompts/topology.md` "The shape". This file refers to roles by **name**,
> never by number.

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
6. **`Agent(builder)`** passing **all worker fragments + the `linked_nodes` /
   topic-relevance context from step 1** (this context is REQUIRED — the
   builder judges relevance against it, not the source alone) + the
   internal-investigator's reuse material (step 1). The builder merges the
   fragments, runs the extract check, then
   organize → link → render. Read its stub.
   - **On `result: fail`:** run
     `python3 scripts/tools/route_failure.py {failing_check_names}`, re-enter
     the owning role it names (Worker for `extract`, Builder for
     `organize`/`link`/`render`, Archive for `archive`), apply the data fix,
     and rebuild. (This is the dissolved Error agent — a lookup, not a role.)
7. **`Agent(auditor)`** on the rendered node.
   - **tightening-loop branch:** for each `adjacent_needs_update[]` entry with
     `skip_external: true`, re-enter at the Worker (shape a — extract from the
     already-archived scratch) or the Builder (shape b — a stale derived field,
     no extraction), rebuild, and re-audit. External + Archive are skipped (no
     new URL, no new bytes).
8. **Finalize** *(orchestrator step — not a role)* — done when the auditor reports
   `health: pass` and `adjacent_needs_update: []`. A node was added/changed, so refresh the
   build-state block (`python3 scripts/build/build-state.py --update`) — the
   build-state gate (`--check`) is otherwise red at commit. Report the built
   node and a short summary of each role's returned stub. (Stubs are return
   values — the orchestrator reads each as it goes; nothing is written to disk
   for the handoff.)

The user commits when ready (the pre-commit gate runs at the commit boundary).
