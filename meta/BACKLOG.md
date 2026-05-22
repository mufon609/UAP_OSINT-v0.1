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
and **C — Anytime** (no upstream blockers). Item identifiers within
each section (A1, A2, …, B1, …, C1, C2, …) are positional working
labels, not stable identifiers. A closed item's block is deleted in
full — no marker, no placeholder. A new entry takes the lowest section
number not currently in use, so **numbers recycle**; once a section,
and ultimately the whole BACKLOG, is cleared, numbering restarts from 1.
Because an ID is transient and reused, never reference it from outside
this file — not in code, docs, prompts, commit messages, or `git log`
searches. Describe the work; the commit diff + message are the record.
See `meta/conventions.md` "BACKLOG lifecycle discipline".

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

Cross-references between entries use `**Blocks:**` / `**Blocked by:**`
lines so the dependency graph is visible inline.

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Exercise the pipeline paths the first whole run didn't hit

The seven-role pipeline (`prompts/topology.md`) has now been run *whole* on
one real node build — a user-directed, all-internal institutional-actor
build: Orchestrator → Internal Investigator → Worker (×N) → Build → Audit,
with handoff stubs captured and friction tightened in place. Three paths
were NOT exercised by that run and remain unverified end-to-end:

- the **External Investigator (role 2) + Archive (role 3)** roles — skipped
  by the all-internal branch (every source was already archived). Needs a
  build with a genuine external-source gap.
- the **`caption` and `foia` worker kinds** — only `pdf` + `html` were hit.
- **Error-Agent routing** — no validator failure needed routing on the clean
  run.

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

### A2 — Migrate the per-entry `.note` field to the `summary` / `note` split (stage 2+)

DECIDED (keep + structural refactor). A corpus audit of all 323 per-entry notes
found **0% opinion/rumor/clutter** and **~79% irreplaceable** — removal was off
the table. The field silently does TWO jobs: (A, ~37%) genuine *residue*
(caveat / source-limitation / disambiguation / dating-anchoring) in column-rich
sections, and (B, ~42%) *primary descriptive content* in bare-ref sections
(`org_relationships`, `corroboration_items`, `relationships`) whose columns are
only `path` + enum. The remaining ~21% is drift with a structured home:
~8% misplaced-fact (D — flight hours, award counts, the Clapper AATIP-SAP memo,
purchase prices; belong in Timeline rows / quotes / columns; also a
contradiction-check blind spot), ~9% redundant source-attestation (E), ~4%
column-duplication (C).

End-state: a per-entry `summary` field carries the B descriptive content;
`note` narrows to residue-only (A), empty by default.

**Stage 1 — DONE** (committed): `summary` declared optional on the
`relationship` / `corroboration` / `org_relationship` / `location_relationship`
entry shapes; registered in `prose_drift_fields` for person / organization /
event / location (so it is source-grounded like every synthesis surface);
`summary` table columns exempted from the cell word-budget (it carries prose,
like `note`). Additive — no node bodies changed.

**Stage 2 — REMAINING (the migration; per-entry, careful):**
- Per bare-ref section, point its renderer's descriptive column at `summary`
  (the corroboration renderer already shows `note` as "What It Confirms" — a
  proven churn-free pattern: render `summary or note`, then rename the B-notes
  `note:`→`summary:` block-scoped, body output unchanged).
- For each B-note, after renaming, prose-drift now checks it → **re-ground to
  source vocabulary** (the C5 "3–6 passes" cost — a corroboration trial showed
  ~50% of even the cleanest section's entries had ungrounded synthesis tokens).
- **B-vs-A separation per entry** (blanket rename is unsafe): some "note"s mix
  descriptive content (→summary) with a residue tail (→stays note) — e.g.
  alex-dietrich corroboration c4's "two conflicting attestations … source-
  priority" is an A caveat, not B.
- Migrate the ~26 D facts to Timeline rows / quotes / columns; delete the
  ~43 C/E; drop `note` in `ownership_timeline` + `top_scope_activity`
  (100% fact-dump). Rebuild affected nodes; `pre-commit.sh` green per section.

**Stage 3:** rewrite `conventions.md` ~878 ("Per-entry notes") from the current
section-blind definition to the clean split — `summary` = descriptive content
for bare-ref sections; `note` = residue-only, empty by default.

This is a focused per-entry source-reading effort (≈105 B re-groundings +
26 D relocations), not a mechanical pass — best done in a dedicated session.

**Blocks:** none.
**Blocked by:** nothing (stage 1 shipped; stage 2+ is execution).

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C5 — Streamline prose-drift iteration WITHOUT weakening it (critical; handle carefully)

The prose-drift gate is correct and the resulting nodes are worth the
energy — but source-grounding a synthesis `description` took 3–6 rewrite
passes per node this session (`check-vocab.py` pre-flight roughly halves
it). Two rough edges: token-passing can yield stilted non-English ("is
acknowledging by") that no grammar check catches; and contributors burn
passes guessing source morphology. This is CRITICAL repo discipline —
any streamlining must NOT relax the zero-ungrounded-token floor.
Candidate directions that preserve the floor: tighter `check-vocab.py`
integration into the authoring loop, a morphology-aware suggestion
surface (source has `gives`, not `give`), or surfacing the source token
pool inline. Implement extremely carefully; the gate's rigor is the point.

### C6 — prose-drift grounds `description` against source text only, not `document_intrinsic` / `naming_quirks` (handle carefully)

The Phase-I prose-drift check grounds `description` tokens against the
primary-source TEXT only — it does not credit `document_intrinsic` values
or `naming_quirks.canonical`. Consequence (seen on `dird-01`): describing
a fact that lives only in structured metadata — e.g. a FOIA redaction,
whose vocabulary (`redacted`, `withheld`, `exemption`) is absent from the
source prose — is impossible in the description, and must be surfaced via
Key Passages + `naming_quirks` instead. This may be intended (description
= strictly source-grounded synthesis); decide deliberately whether the
check should credit canonical-form `naming_quirks` / `document_intrinsic`
vocabulary. Same check family as C5; handle with the same care.

### C8 — Phase-I prose-drift and Phase-III description-drift treat adjacent punctuation differently

On `dird-15`, a comma fused inside a closing quote (`apparent "cloaking,"`)
PASSED the Phase-I prose-drift check (the bare token appears in the source
elsewhere) but FAILED the Phase-III description-drift check (which
tokenizes the rendered section and caught the fused punctuation). Two
checks in the same family with different adjacent-punctuation exposure —
a contributor can clear one and trip the other on the same text.
Reconcile their tokenization (shared adjacency handling) so the same text
passes/fails both consistently. Same check family as C5/C6.

### C9 — verbatim-quote check doesn't normalize page-footer/header boilerplate

On `dird-15` (q12/q13), a Discussion passage spanning a printed-page
boundary carries the page footnote + page number + classification
footer/header wedged mid-sentence; that boilerplate isn't in the quote,
so a single verbatim quote across the boundary fails the verbatim-quote
check, forcing a split into two adjacent Key Passages. `normalize_for_compare`
already strips `[MM:SS]` caption timestamps but does NOT strip recognized
page-footer/header/page-number boilerplate. Consider normalizing
recognized page boilerplate in the verbatim check (carefully — it must
not mask real mismatches), or document the split-at-page-boundary
expectation prominently. Recurs on every page-spanning quote in paginated
sources.