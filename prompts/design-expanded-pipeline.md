# Design the expanded build pipeline (agent topology + per-phase checks)

Paste into a fresh Claude Code session. This is a **design / plan**
session in two phases: **(1)** investigate the repo to ground yourself,
then **(2)** design the expanded multi-agent build pipeline described
below *and* the per-phase decomposition of the validators and build
scripts. **Do not implement yet** — produce a plan + a BACKLOG entry and
get sign-off first. (Enter plan mode.)

---

## Why this exists

The current build pipeline (BACKLOG **A2**) is a five-agent chain —
**Scout → Marker → Manager → Meta-linker → Builder** — launchable via
`prompts/agent-*.md`, with per-phase validation via `validate*.py
--phase` (`scripts/checks/_phases.py` maps the ~67 checks to five
phases). It works, but it's coarse in two ways we want to fix:

- **Investigation and extraction are each a single role.** We want to
  split *internal* investigation (what the repo already holds, linked
  nodes/sources) from *external* investigation (finding missing
  load-bearing content), separate archival into its own agent, and use
  **type-specialized extraction workers** (one per source/node kind).
- **The validators still mostly run as one monolithic pass.** We want
  **tight per-agent feedback**: each agent validates *only what it just
  produced* (instant feedback), so a defect surfaces at the agent that
  caused it — not at a big end-of-build sweep.

The headline question to answer: **how do we break the scripts and checks
into per-phase/per-agent bundles so there is (A) instant feedback and
(B) no monolithic check?** `--phase` + `_phases.py` are the seed; this
session extends them to the richer topology (and resolves C42).

---

## Phase 1 — investigate the repo (read before designing)

Onboard first (`prompts/onboard.md`), then read, in order:

1. **Governance:** `README.md`, `meta/conventions.md` (esp. the
   three-layer architecture, the entity↔finding directional contract,
   "Statements as the universal evidentiary primitive", source-read-first),
   `meta/schema.yaml`, `meta/schema-research-artifact.yaml`.
2. **The current pipeline:** `prompts/build.md` — the Phase I/II/III
   walkthrough + the "The multi-agent pipeline (A2)" section (the five
   agents, the `/tmp/handoff-{slug}-{agent}.yaml` stub format, the
   agent-boundary invariant) + "Running the full pipeline". Then the
   launch prompts `prompts/agent-{scout,marker,manager,meta-linker,builder}.md`.
3. **The check/script decomposition (the load-bearing surface):**
   - `scripts/checks/_phases.py` — the phase map + `in_scope()`; the
     current 5-phase classification of all ~67 checks.
   - `scripts/checks/__init__.py` — the `Issue`/`Context` contracts and
     the routing philosophy ("the dispatch lists are the routing source
     of truth").
   - `scripts/build/{validate,validate-research,review-coverage}.py` —
     the three orchestrators, their dispatch lists (`_NODE_CHECKS`,
     `_ARTIFACT_CHECKS`, `_PRE_PARSE_CHECKS`, `_REVIEW_CHECKS`), the
     global manifest block, and the `--phase` filter.
   - `scripts/checks/` — skim the ~67 modules; each declares `CHECK_NAME`
     and a `check(ctx)`.
4. **The build scripts each agent drives:** `scripts/build/`
   {`research-scaffold`, `extract-source`, `build-from-research`,
   `associate`}.py and `scripts/tools/manifest.py`.
5. **BACKLOG:** A2 (settled 5-agent decomposition + increments 1–5, all
   shipped), C41 (first live end-to-end run — pending), C42 (validate the
   phase map), C35 (page-ref residual). Note `claim_group`/A3 is shipped
   across all 15 person nodes.

Run the health check (`CLAUDE.md` §2) so you know the baseline is green.

---

## Phase 2 — the target topology (design to this)

The user's numbered workflow. Reconcile it with the existing A2 agents —
say explicitly which A2 agent each role keeps / renames / splits /
merges, and flag the naming clash up front: **the user's "Manager" (0) is
an ORCHESTRATOR — not A2's "Manager" (which organizes quotes; that work
moves into the Build Agent / Workers here).**

- **0 — Manager (orchestrator).** Kicks off the process and monitors the
  individual agents. Hands the handoff stubs along phase 1→2→3→…. Takes
  input from the user (scope/target — per `CLAUDE.md`, the human directs
  what to build). New role; A2 had no explicit orchestrator (the session
  was it).
- **1 — Internal Investigator.** Investigates sources and nodes already
  in the repo that are linked to the future build; extracts the existing
  node/source data the build can reuse. (New — A2's Scout only looked
  outward.)
- **2 — External Investigator.** Fills gaps — finds missing load-bearing
  content not present internally, or investigates a specific task.
  Extracts exact, verifiable URLs and queues source material for
  archiving. (≈ A2 Scout's investigator half + `prompts/web-claude-investigator.md`.)
- **3 — Archive / Manifest Management Agent.** Archives the queued
  sources (`manifest.py add` → sha256 + archive bits; Wayback;
  `meta/sources-access.md` workarounds), keeps the manifest healthy.
  (≈ A2 Scout's verifier/archival half.)
- **4 — Worker / Sub-Agents.** Grab verbatim quotes / info, **specialized
  by source or node type** (consider one per kind — e.g. paginated-PDF,
  HTML, caption-transcript, FOIA-`.txt`-sibling; or per node type). (≈ A2
  Marker, refined into type-specialized extractors. Source-read-first +
  the verbatim-quote invariant still bind here.)
- **5 — Build Agent (+ Error Agent).** Places the info into the research
  artifact YAML; **tests before building**; builds the node out only if
  error-free; passes any errors to an **Error Agent** that investigates +
  reports back; fixes are applied to the broken *data* (never the node
  body) and the checks are re-run. (≈ A2 Manager's "organize into the
  node" + A2 Builder + a new error-triage role.)
- **6 — Audit Agent.** Audits repo/node health; compares adjacent / linked
  nodes to find any that should be updated with the new source material —
  **if so, that path skips role 2 (External Investigator)** (the material
  is already in hand; this is the tightening loop). (≈ `prompts/audit.md`
  + the cross-layer review checks + the adjacent-node propagation that has
  no home today.)

For each role, define: inputs, outputs, the handoff stub it writes, which
scripts it runs, whether it reads primary sources directly, and which
checks give it instant feedback (see below).

---

## The core problem — break up scripts + checks per phase/agent

This is the deliverable's center. For (A) instant feedback and (B) no
monolithic pass:

1. **Re-map the ~67 checks to the richer phase set.** `_phases.py` today
   has 6 buckets (preflight + scout/marker/manager/meta-linker/builder).
   The new topology has more boundaries (internal-investigation,
   external-investigation, archive, per-type extraction, build, error,
   audit). Re-classify each check by *which agent produces the state it
   reads* — and surface the checks that don't cleanly belong to one
   agent (assign to the latest phase that supplies their inputs). Resolve
   C42 in the process.
2. **Per-agent feedback loop.** Each agent runs `validate*.py --phase X`
   (its own bundle + always-on preflight) the moment it finishes, writing
   the result into its handoff stub — so a defect is caught at its
   producing boundary, not three agents downstream. Decide the CLI shape
   for the new phases (extend the existing `--phase` choices /
   `_phases.py`), and whether type-specialized workers (role 4) get a
   sub-phase or share the marker phase.
3. **Decompose the build scripts too, not just the checks.** Which agent
   runs `manifest.py add` (3), `extract-source.py` (1 or 3→4),
   `research-scaffold.py` (0/5), `build-from-research.py` +
   `review-coverage.py` (5/6)? Define the script-level handoffs so no
   agent re-does another's work and the "fix the artifact, never the node
   body, then rebuild" rule still holds.
4. **Keep the global consistency guarantee.** Per-phase bundles give
   instant feedback, but a final unflagged full pass (the Build/Audit
   agent's run) must stay as the global check. Be explicit about what
   only the full pass can catch (cross-cutting checks: link_resolution,
   boundary, coverage, the finding/entity boundary checks).
5. **The orchestrator + stubs.** How does the Manager (0) sequence agents,
   pass stubs, and decide branches (e.g. role 6 skipping role 2)? Where
   do stubs live (today: `/tmp/handoff-{slug}-{agent}.yaml`, ephemeral)?

---

## Deliverable

A written plan (and a new BACKLOG entry — Section A, since it has
ordering/coupling with A2; pick the next unused ID) covering: the
reconciled agent topology (with the A2 mapping + naming-clash resolution),
the re-mapped per-phase check classification, the per-agent feedback +
script-handoff design, and a staged implementation (what ships first;
respect the repo's anti-batch-synthesis rule). Surface the open decisions
via `AskUserQuestion` before finalizing. Then `ExitPlanMode` for sign-off.
Do not implement in this session unless the user says go.
