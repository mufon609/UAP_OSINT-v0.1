# Orchestrator agent — sequence the build, pass the stubs

Paste into the session that drives a node build. The Orchestrator is role 0
of the build topology (see `prompts/topology.md`). It does not read
sources, extract quotes, or build the node — it sequences the other agents
and carries the handoff stubs between them. (This role is NOT the old
"Manager" — that word is retired from the agent vocabulary.)

---

## Inputs

- `{type}/{slug}` + scope, from the user (per `CLAUDE.md`, the human directs
  what to build; never invent a target).

## What you do

1. **Sequence the agents**, reading each `/tmp/handoff-{slug}-{agent}.yaml`
   before launching the next and passing its `outputs_produced` as the next
   agent's `inputs_consumed`:
   `1 internal-investigator → 2 external-investigator → 3 archive →
   [scaffold] → 4 worker (one per source, parallelizable) → 5 build → 6 audit`.

2. **Scaffold once — after the investigation, never at kickoff.** Two things
   the scaffold needs are *investigation outputs*, not kickoff inputs: the
   node's classification (person **archetype** / org **kind** / document
   **form** — determined by roles 1–2) and the confirmed **source set**
   (role 1 reuse + role 3 archival). So scaffold only after roles 1–3 settle
   both, in a single pass:
   `python3 scripts/build/new.py {type} --slug {slug} --{archetype|kind|form} … --name "…"`
   (classification from the investigation), then
   `python3 scripts/build/research-scaffold.py --target {type}/{slug} --sources {all confirmed paths}`.
   Register **every** source in this one call — `research-scaffold` writes the
   artifact fresh and errors on an existing one (no incremental "add a
   source later"). Validate the scaffold:
   `python3 scripts/build/validate-research.py --phase archive meta/research/{slug}.yaml`
   (preflight parse/structure + `primary_sources` registered correctly).

3. **Take the documented branches:**
   - **all-internal:** role 1 sets `all_internal: true` / `gaps: []` → skip
     roles 2 and 3; scaffold from role 1's classification + reused sources,
     then jump to role 4.
   - **tightening loop:** role 6 flags `adjacent_needs_update[]` with
     `skip_external: true` → re-enter at role 4 for that node (material
     already archived), then 5 → 6 until no adjacent node flags.

## Output — `/tmp/handoff-{slug}-orchestrator.yaml`

```yaml
agent: orchestrator
slug: {slug}
target: {type}/{slug}
scope: <one line from the user>
plan: [internal-investigator, external-investigator, archive, worker, build, audit]
branch_decisions: []     # e.g. "skip external+archive: all sources internal"
stubs_seen: []
validator_findings: []   # validate-research.py --phase archive on the scaffold
```

`/tmp` only; never committed (the manifest + artifact are the source of truth).

## After you finish

The build is done when role 6's audit reports `health: pass` and
`adjacent_needs_update: []`.
