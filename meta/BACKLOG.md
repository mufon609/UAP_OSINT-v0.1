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

### A2 — Promote per-entry fact-notes to verbatim quotes / columns; route patterns to findings

DECIDED. Two corpus audits of all 323 per-entry notes settled this. The first
framed it residue-vs-descriptive and proposed a new `summary` synthesis field;
the second, run through a fact / synthesis / noise lens, overturned that — the
field is **0% clutter**, but its content is mostly **facts stored as
paraphrase**, not synthesis needing a home:
- **~59% FACT** — Q (~56%) → a verbatim `quote` + source.location; C (~3%) → a
  column / enum value. ~43% of the Q notes already carry the verbatim source
  text inline.
- **~13% NOISE** → delete (column-restatement, redundant attestation, boilerplate).
- **~20% RESIDUE** → the legitimate `note` (source-limitation / dating-anchoring
  / disambiguation).
- **~8% SYNTHESIS** — only ~4% entity-local; the rest are cross-source *patterns*
  that belong on finding / investigation nodes. A per-entry synthesis field was
  REJECTED — it would entrench synthesis; `description` / `background` and the
  finding layer already carry it.

End-state: facts → quotes/columns; noise → deleted; patterns → findings;
`note` = residue-only (its narrowed positive definition now lives in
`conventions.md` "Per-entry notes" — "residue, never a fact-store or synthesis
surface").

**DONE this session:** reverted the provisional `summary` declaration; deleted
12 verified-noise notes (arlo / ttsa key_personnel column-restatements, ousd-is
DoDD-5143.01 subsidiary boilerplate ×5, a karl-nell cross-pointer); closed the
`funder` / `fund-administrator` enum gap (safire ISF + Mainwaring rows are now
structured, not `partner`+note-workaround); narrowed the `note` definition.

**DEFERRED (the bulk — per-entry, source-reading, not mechanical):**
- Promote the ~191 fact-notes (Q + C) to verbatim `quotes[]` entries (with
  `source.location`) and structured columns / enum values — this is where
  "solid facts, not synthesis" is actually won; ~43% of the Q notes already
  have the verbatim text inline.
- Route the ~13 cross-source pattern notes to finding / investigation nodes
  (F.SRI and the open `lockheed-martin-uap-materials` investigation are already
  on the books to receive several).
- The ~64 residue notes already conform — no change.

Note: the conservative noise count is **12**, not the first audit's ~41 — the
rest carry discrete facts or real caveats (quote-promotion / residue), so a
blanket "delete the notes" pass would lose content. Per-entry judgment required.

**Audit-surfaced per-node debt (running log — appended per phase; cleared
items removed as the sweep resolves them, the commit diff being the record):**

_Phase-C org batch cleared the safire / ousd-is / arlo / ipmo note debt
(promotions + delete-redundant sweeps, each gated by an independent fresh-context
audit). Two regressions were caught at the gate, not in the final state: ousd-is's
two "belongs on a stub person node" deletions (Cambone prior-roles, Overbaugh
career) were restored as quotes q50/q51; arlo's four GSA OASIS+ contract numbers,
which survived nowhere else, were promoted to q19 rather than deleted. The uaptf
q22 provenance error (Charter p.3 → 23 Sep 2020 NIA outreach memo) was also fixed._

_Still open:_
- **aaro** — `blackvault-sancorp-23-f-1114-aaro-pws.pdf` SF-33 issuing-office
  block + PWS task-area enumeration are OCR-corrupt with no clean-text sibling,
  so they are NOT promotable to verbatim quotes. Blocked on `/prepare-ocr-sibling`
  (no autonomous owner). Stays residue; defer past this effort.
- **people-node bulk** — the unswept people artifacts (hal-puthoff, russell-targ,
  kit-green, david-grusch, james-ryder, + the partially-trimmed people) carry the
  remainder of the ~191-note promotion work; Phase C people batches.

**Blocks:** none.
**Blocked by:** nothing — execution.

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