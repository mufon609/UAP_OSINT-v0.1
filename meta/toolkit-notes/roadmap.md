---
id: meta/toolkit-notes/roadmap
type: meta
schema_version: 1
created: 2026-04-17
---

# Refactor roadmap

Top-level plan for the ground-up refactor of the UAP research repository
into a topic-neutral primary-source investigation toolkit. Preserved as
durable context so conversation-summary compaction does not lose the
outline of what's been done and what remains.

Update this file as phases complete or scopes change. The file is the
source of truth; conversation recall is not.

---

## Step 0 — Design consultation  ✅ DONE

Scope definition. Settled on:

- Topic-neutral toolkit (UAP is the first instance)
- Fresh ground-up build in `REFACTOR/`, original repo preserved
- Minimum taxonomy (orgs: gov/gov-contractor/private;
  documents: gov-doc/non-gov-doc + doc_form)
- Schema-driven validation via `meta/schema.yaml`
- Topic-specific material lives under `meta/topic/` (deleted cleanly on fork)

---

## Step A/B/C — Governance + infrastructure  ✅ DONE

### A — Schema, conventions, scripts skeleton
`meta/schema.yaml`, `meta/conventions.md`, templates under
`meta/templates/`, AGENT.md, CLAUDE.md, CONTRIBUTING.md, README.md.
Flat scripts (no shared `lib/`): `new.py`, `validate.py`, `manifest.py`,
`archive.py`, `associate.py`, `audit-schedule.py`, `build-state.py`,
`transcribe.py`.

### B — Bug fixes
- **B1** — manifest SHA256 integrity (checksum at archive-time;
  `manifest.py verify-checksums`; validator check #12)
- **B2** — `schema_version` value check against `schema.compatible_with`
  (prevents drifted-version content passing validation silently)

### C — Pilot failure postmortem
First Phase 2 pilot (2026-04-17) produced fabricated quotes and
mis-attributed claims in 10 nodes. Deleted all 10. Established four
process fixes:
- Mechanical verbatim quote verification (validator check #11)
- Source-read-first hard rule
- One-node-per-session hard rule
- Postmortem captured at `meta/toolkit-notes/pilot-failure-2026-04-17.md`

---

## Step D — Layered-process tooling  🟡 IN PROGRESS (D.0–D.4 done)

Three-phase build process: **Investigation → Build → Review**. Each
phase has dedicated tooling and a bounded discipline.

### D.0 — Research-artifact schema design  ✅ DONE
`meta/schema.yaml` research-artifact spec: required keys, entry shapes
per section (quotes, claims, entities_referenced, naming_quirks,
research_gaps, rumors conditional), lifecycle fields, iteration log,
validation invariants.

### D.1 — Phase I scaffolding + validation  ✅ DONE
- `scripts/research-scaffold.py` — scaffolds empty `research/{slug}.yaml`
  with type-conditional `rumors` section
- `scripts/validate-research.py` — 18 check helpers, structural
  validation only (coverage checks live in D.4)

### D.2 — Phase I source extraction + prompt  ✅ DONE
- `scripts/extract-source.py` — wraps `pdftotext` + `pdfinfo`; writes
  `/tmp/scratch-{slug}-N.txt`; batch + single modes
- `prompts/build.md` — Phase I workflow with 11 steps + 6 bounded agent
  tasks (T1–T6)

### D.3 — Phase II build  ✅ DONE
- `scripts/build-from-research.py` — deterministic regeneration from
  research artifact → node body. **Document-only scope.** Pre-flight
  validates artifact; per-section renderers; post-build validates node;
  invokes `associate.py`.
- Schema: added `description` required field, `retain_as_done` optional
  on research-gap entries.
- Existing Fravor node cleaned: removed "What This Does Not Establish"
  section.
- Prompt updated with Phase II workflow.

### D.4 — Phase III review  ✅ DONE
- `scripts/review-coverage.py` — four mechanical consistency checks
  between the regenerated node and its research artifact: Coverage
  (artifact claim/quote → node body), Boundary (node body matches
  build-from-research.py dry-run, excluding Associated Nodes),
  Stub-linking (every `entities_referenced.wrap_path` renders as a
  `[\`/path\`]` link), and OQ deduplication (Open Questions items
  map 1:1 to unresolved + retain_as_done research_gaps).
- Shipped as a sibling script (not bolted onto validate.py), confirming
  the split pattern for future check modules. Resolves BACKLOG item 2's
  deferred design decision.
- Document-type scope (matches build-from-research.py D.3); other
  types emit a skip notice. Per-type extension lands with its Phase II
  renderer (BACKLOG).
- Agent-assisted semantic review is not a separate script — documented
  in `prompts/build.md` Phase III Step 2 as a human-read pass. Bounded
  agent task (T7) is a future increment.

### D.5 — Fravor pilot rebuild  ⏳ PENDING
First end-to-end run of Phase I → II → III on a single node (the
existing Fravor written-testimony document). Populates the empty
research artifact, regenerates the node, passes Phase III review.
Serves as the working example for the rest of the build queue and
exposes integration bugs the sub-phase smoke tests missed.

### D.6 — Docs + prompt updates post-pilot  ⏳ PENDING
Updates driven by what D.5 teaches. Likely: revised Phase I
discipline, clarified field conventions in `context_extrinsic` /
`document_intrinsic`, any new validator checks surfaced by pilot
observation.

### D.7 — Post-pilot cleanup  ⏳ PENDING
Retiring temporary scaffolding, consolidating interim decisions into
permanent docs, BACKLOG triage.

---

## Step E — Iteration tooling, cross-node updates  ⏸ DEFERRED

Append-only research artifacts demand iteration tooling:

- Bumping `last_iteration` (i0 → i1 → …) and generating the
  `iterations[]` entry
- Cross-node updates: when a claim in one artifact changes the
  evidentiary picture for another node, propagate the reference
  (`corroborated_by`, `superseded_by`, `contradicted_by`)
- Audit-cadence enforcement plumbing: `audit-schedule.py` is
  operational (per-entry staleness detection shipped with D.1). What
  remains is wiring `--overdue` into a pre-commit / CI hook so stale
  artifacts block commits past the grace period

Deferred until after Step D stabilizes and the iteration pressure
becomes real (likely after ~10 nodes have been through Phase I→II→III
and some of them are ready for i1).

---

## Conventions

- ✅ = done
- 🟡 = in progress
- ⏳ = pending (next-up)
- ⏸ = deferred (not next-up)
- Phase completion = tooling ships + prompt/docs updated + smoke tests
  pass + relevant BACKLOG entries filed

Keep this file ≤ one screen per step. Long-form design notes belong
in `meta/toolkit-notes/{topic}.md` files, not here.
