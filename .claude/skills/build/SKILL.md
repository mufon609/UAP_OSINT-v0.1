---
name: build
description: Orchestrate a primary-source node build through the multi-agent pipeline — internal/external investigation, archival, verbatim extraction, synthesis, and audit. Use when the user directs a node to be built or rebuilt. Runs on the main thread and dispatches the role subagents; never hand-author a node.
argument-hint: {type}/{slug} "<scope>"
skills: build-protocol
tools: Agent(internal-investigator, external-investigator, archive, worker, builder, auditor), Read, Bash(python3 scripts/build/new.py *), Bash(python3 scripts/build/research-scaffold.py *), Bash(python3 scripts/build/validate-research.py *), Bash(python3 scripts/tools/route_failure.py *), Bash(python3 scripts/checks/_phases.py *)
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
     steps 2–3; scaffold from the reused sources and go to step 5.
2. **`Agent(external-investigator)`** with `gaps[]` + `linked_nodes`. Read
   `queued_sources[]`. **Reject any queued source lacking a `confirming_span`**
   — a bare "read it" is not accepted (build-protocol → the invariant).
3. **`Agent(archive)`** with the (validated) `queued_sources[]`. Read
   `archived[]` + the scratch paths.
4. *(reserved — sourcing complete)*
5. **Scaffold once, here** — only after sourcing has settled the node's
   classification (person **archetype** / org **kind** / document **form**)
   and the full source set. Two commands, in order:
   - `python3 scripts/build/new.py {type} --slug {slug} --{archetype|kind|form} … --name "…"`
   - `python3 scripts/build/research-scaffold.py --target {type}/{slug} --sources {ALL reuse + archived paths}`
     (it writes fresh and cannot append, so every source goes in this one call)
   - then `python3 scripts/build/validate-research.py --phase archive meta/research/{slug}.yaml`
     (the artifact's first validation).
   - *(The scaffolder is hook-gated: a second uncommitted new person/org node
     in one session is blocked. Lighter types may batch. Don't work around it.)*
6. **`Agent(worker)` once per source, in parallel** — issue the worker calls
   in a single message so they run concurrently; each returns a fragment (it
   does not write the artifact). Collect every fragment.
7. **`Agent(builder)`** passing **all worker fragments + the `linked_nodes` /
   topic-relevance context from step 1** (this context is REQUIRED — the
   builder judges relevance against it, not the source alone) + role 1's reuse
   material. The builder merges the fragments, runs the extract check, then
   organize → link → render. Read its stub.
   - **On `result: fail`:** run
     `python3 scripts/tools/route_failure.py {failing_check_names}`, re-enter
     the owning role it names (Worker for `extract`, Builder for
     `organize`/`link`/`render`, Archive for `archive`), apply the data fix,
     and rebuild. (This is the dissolved Error agent — a lookup, not a role.)
8. **`Agent(auditor)`** on the rendered node.
   - **tightening-loop branch:** for each `adjacent_needs_update[]` entry with
     `skip_external: true`, re-enter at the Worker (shape a — extract from the
     already-archived scratch) or the Builder (shape b — a stale derived field,
     no extraction), rebuild, and re-audit. External + Archive are skipped (no
     new URL, no new bytes).
9. **Done** when the auditor reports `health: pass` and
   `adjacent_needs_update: []`. Report the built node and where its handoff
   stubs landed (`/tmp/handoff-{slug}-*.yaml`).

The user commits when ready (the pre-commit gate runs at the commit boundary).
