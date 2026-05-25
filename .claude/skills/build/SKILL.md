---
name: build
description: Orchestrate a primary-source node build through the multi-agent pipeline — internal/external investigation, archival, verbatim extraction, synthesis, and audit. Use when the user directs a node to be built or rebuilt. Runs on the main thread and dispatches the role subagents; never hand-author a node.
argument-hint: {type}/{slug} "<scope>"
allowed-tools:
  - Agent(internal-investigator, external-investigator, archive, worker, builder, auditor)
  - Read
  - Bash(python3 scripts/build/new.py *)
  - Bash(python3 scripts/build/research-scaffold.py *)
  - Bash(python3 scripts/build/validate-research.py *)
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
4. **Scaffold once, here** — only after sourcing has settled the node's
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
   worker-ready**: its `pdftotext`/extract layer is corrupt, so a quote pulled
   from it is garbage or trips the verbatim gate (build-protocol →
   source-read-first). Read the manifest entry for each primary source; for any
   ocr-scan / extraction-lossy source that lacks a verified same-stem `.txt`
   sibling, the sibling MUST exist before the Worker. It is produced by VLM
   page-image read **and independently verified by a different agent** (the
   producer cannot self-verify a hallucination), then registered as a paired
   entry — the four-path procedure + the independent-verification rule are in
   `meta/conventions.md` "Producing the `.txt` sibling". This is the
   orchestrator's responsibility, **never the Worker's** (the Worker has no
   Write tool). It runs **regardless of the all-internal branch** — all-internal
   skips new-bytes sourcing (external + archive), not source-prep. If a
   sibling is missing, the remedy is the **`/prepare-ocr-sibling`** skill — it
   produces the sibling (VLM page-image read), independently verifies it (a
   different agent — the producer can't self-verify), and registers the paired
   entry. Run it (or, if you can't dispatch a skill from here, **HALT** and
   direct the user to run `/prepare-ocr-sibling {source-path}`) before handing
   the Worker a corrupt extract. Once every ocr-scan source has a verified
   sibling, the canonical scratch comes from `extract-source.py --artifact`
   (it prefers the sibling). Text-native sources need no sibling.
5. **`Agent(worker)` once per source, in parallel** — issue the worker calls
   in a single message so they run concurrently; each returns a fragment (it
   does not write the artifact). Collect every fragment.
6. **`Agent(builder)`** passing **all worker fragments + the `linked_nodes` /
   topic-relevance context from step 1** (this context is REQUIRED — the
   builder judges relevance against it, not the source alone) + role 1's reuse
   material. The builder merges the fragments, runs the extract check, then
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
8. **Done** when the auditor reports `health: pass` and
   `adjacent_needs_update: []`. A node was added/changed, so refresh the
   build-state block (`python3 scripts/build/build-state.py --update`) — the
   build-state gate (`--check`) is otherwise red at commit. Report the built
   node and a short summary of each role's returned stub. (Stubs are return
   values — the orchestrator reads each as it goes; nothing is written to disk
   for the handoff.)

The user commits when ready (the pre-commit gate runs at the commit boundary).
