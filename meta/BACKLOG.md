---
id: meta/BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

Open items are partitioned into three sections by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
and **C — Anytime** (no upstream blockers). Item identifiers are
A1, A2, ..., B1, B2, ..., C1, C2, ... — within each section,
retired items leave a gap rather than shifting remaining IDs, so
git-log and commit-message references stay valid. The same
gap-stable policy in `meta/conventions.md` applies to validator
check names.

**Default focus: Section C.** C items have no upstream dependencies
and can be picked up and finished in a single pass. A and B items
carry ordering or coupling constraints — starting one without its
dependencies risks half-baked implementations and leaves the BACKLOG
cluttered with partial work. For ad-hoc sessions, prefer C work.
Reserve A and B for sessions explicitly scoped to those tracks.

Items waiting on an external event the repo can't drive (FOIA
resolution, registry access, third-party publication) and that are
**topic-specific** to the current investigation live in
`meta/topic/research-queue.md` "Externally blocked" — that's the fork-
boundary-correct home for them. If a genuinely toolkit-neutral
externally-blocked item ever surfaces (rare), reinstate the
"Externally blocked" heading at the bottom of this file.

---

## A. Priority sequence

Items with ordering or coupling constraints.

*No priority-sequence items currently open.*

---

## B. Parallel batch (renderer pass)

Items that touch the renderer and naturally batch into a single
polish pass — bundling reduces churn vs. shipping each as a
separate touch.

*No parallel-batch items currently open.*

---

## C. Anytime (no dependencies)

Items with no upstream blockers; safe to pick up at any point in
any session. Per the preamble, this is the default-focus tier:
C work doesn't risk half-baked implementations.

### C1 — Render `not-primary-source-established` rumors to reader

**Scope.** Today the rumor schema renders `primary-source-disputed`
rumors as a `## Primary-Source Contradictions` section on the node
body, but `not-primary-source-established` rumors have NO renderer
surface — they're investigator-only YAML memory. Change the renderer
so `not-primary-source-established` rumors render in a new section
(working title: `## Claims Circulating Without Primary Source`) with
the same fact-table shape as Primary-Source Contradictions. Section
auto-suppresses when no qualifying rumors exist. Reader-visible
transparency: a reader landing on a node sees both confirmed claims
and curated-but-unsourced ones, and can self-police by sending better
sources.

**Evidence.** Current state of rumor entries across the corpus:

| Status | Count | Renders? |
|---|---|---|
| `primary-source-disputed` | 3 | yes (`## Primary-Source Contradictions`) |
| `not-primary-source-established` | 20 | **no** (artifact-only) |

Twenty curated rumors across 11 artifacts are invisible to readers
despite being deliberate contributor work. Affected artifacts:

| Artifact | Rumors (not-established) |
|---|---|
| `/people/russell-targ` | 3 (birth, pre-SRI employers, CIA/Stargate) |
| `/locations/skinwalker-ranch` | 4 |
| `/people/alex-dietrich`, `/people/ronald-moultrie`, `/people/sue-gough` | 1 each |
| `/organizations/aaro`, `/organizations/arlo-solutions`, `/organizations/ipmo`, `/organizations/ttsa`, `/organizations/uaptf` | 2 each |
| `/events/2004-nimitz-encounter` | 3 |

**Build dependencies.** None — single coordinated change to schema +
renderer + conventions doc. No content edits needed (existing rumor
entries auto-render once the renderer surfaces them).

**Implementation sketch.**

1. `meta/schema.yaml::types.research-artifact.rumor_entry` — update
   the `status_values` comment block to note the renderer surface for
   `not-primary-source-established` (currently says "no renderer
   surface").
2. `scripts/build/renderers/_universal.py` (or wherever
   `Primary-Source Contradictions` is rendered) — add a parallel
   render block that filters rumors by `status:
   not-primary-source-established` and emits the new section. Section
   header copy candidates: `## Claims Circulating Without Primary
   Source` / `## Public-Record Claims Lacking Primary Source` /
   `## Investigator-Curated Unverified Claims` — pick one in
   implementation.
3. `meta/conventions.md` — update the rumor-discipline section to
   reflect that both rumor types are now reader-visible.
4. Regenerate the 11 affected artifacts via `build-from-research.py`;
   they pick up the new section automatically. Inspect a couple for
   reader-visibility quality.
5. Re-run pre-commit; commit as one focused commit per the audit-
   correction pattern.

**Density math.** Affects 11 of 37 currently-built artifacts (~30%).
Renders 20 new reader-visible rumor entries on first build pass. Each
new section is a 3-column fact table (claim / circulates-in / note)
— same shape as the existing Primary-Source Contradictions section,
so reader cognitive load is bounded.

**Surfaced from.** Russell Targ audit session (2026-05-15) — user
question about whether the audit's 4 rumors should be reader-visible.
Investigation confirmed the asymmetry (disputed renders, not-
established doesn't) is not reader-honest, and substantial existing
investigator work would gain visibility from a single renderer
change.

---

### C2 — Prompts cross-reference + UX polish pass

**Scope.** A round of contributor-experience polish across
`prompts/*.md` that surfaces existing tools and workflows at the
right phase boundaries. Each individual change is small; the value
is in the bundle — the prompts currently fail to mention several
high-leverage tools and workflows that exist in the toolkit.

**Evidence.** Specific gaps surfaced during the Targ build + audit:

| Prompt | Missing reference | Why it matters |
|---|---|---|
| `prompts/build.md` Step 5 / Step 10 | `scripts/tools/check-vocab.py` as the pre-flight vocabulary helper for prose-drift discipline | Iterating prose against the prose-drift check is the single heaviest friction point in the build; check-vocab.py reduces 5+ validator passes to 1-2 |
| `prompts/build.md` Phase III | `scripts/tools/coverage-suggest.py` as a post-build self-audit step | Catches build-phase under-extraction before contributor commits; same author may not catch their own gap |
| `prompts/audit.md` | Cross-reference to `prompts/quote-relevance-audit.md` as the next-deeper layer | Audit catches extraction completeness; quote-relevance audit catches content-relevance — separate concerns, currently not linked |
| `prompts/audit.md` | Cross-reference to `meta/sources-access.md` Wayback-fuzzy-timestamp workflow when a manifest entry is `status: pending` + has `wayback_date` set | First Targ audit pass missed this and stalled at the IRVA bio — workflow is documented but not discoverable from the audit prompt |
| `prompts/audit.md` "Audit output" | Template for the final audit report (mechanical findings / semantic gaps / missing sources / rumors / recommendations) | Standardized output makes audits comparable across sessions and contributors; currently free-form |
| `prompts/archive-sweep.md` | Wayback-fuzzy-timestamp workflow for recovering 404'd sources | Same Wayback retrieval gap that affected the audit |
| `CLAUDE.md` + `AGENT.md` | One-line callout for the Wayback fuzzy-timestamp workflow | Highest-traffic docs; both should surface the workflow so future sessions don't repeat the dead-end |

**Build dependencies.** Should ship after C1 (rumor rendering) and
after `coverage-suggest.py` lands (already shipped). The audit-prompt
cross-ref to rumor rendering needs C1 to land first; otherwise the
prompt would describe a renderer behavior that doesn't exist yet.

**Implementation sketch.**

1. `prompts/build.md` Step 5 — add `check-vocab.py` reference paragraph.
2. `prompts/build.md` Phase III — add optional `coverage-suggest.py`
   step (self-audit before commit).
3. `prompts/audit.md` — add the four cross-references in the table
   above + audit-output template.
4. `prompts/archive-sweep.md` — add Wayback-fuzzy-timestamp note.
5. `CLAUDE.md` + `AGENT.md` — one-line Wayback callout each.
6. Pre-commit + commit as one polish-pass commit.

**Density math.** ~6 documentation files touched, each with 1-3
small edits. Estimated ~50-100 lines of doc changes total. No
schema / renderer changes; pure doc surface.

**Surfaced from.** Russell Targ build + audit retrospective
(2026-05-15) — user asked for cross-prompt improvements; specific
recommendations emerged from process-friction observation across two
build sessions + two audit passes.
