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

The seven-role pipeline (`prompts/topology.md`) has been run *whole* on one
real node build — a user-directed, all-internal institutional-actor build:
Internal Investigator → Worker (×N) → Build → Audit, with handoff stubs
captured and friction tightened in place. The **External Investigator
(role 2) and Archive (role 3)** roles have since been exercised standalone on
an existing node — a source-recovery that re-pulled a dead JavaScript-shell
capture from a Wayback snapshot (External Investigator confirmed the snapshot
and captured verbatim spans; Archive re-pulled the file and refreshed the
manifest). Both behaved per contract. Paths still unverified end-to-end:

- **role 2 + role 3 integrated inside a full `/build`** with a genuine
  external-source gap — so far they have run standalone, not as the
  external-gap branch of a fresh orchestration.
- the **`foia` worker kind** — `caption` is now exercised (the all-internal
  `jre-2194-elizondo-2024` transcript build hit it end-to-end: internal-survey →
  caption worker → builder → audit). `pdf` + `html` + `caption` done; only `foia`
  remains, and no load-bearing *unarchived* FOIA source currently exists to build
  (every referenced FOIA doc is already archived) — wait for a genuine FOIA gap
  rather than manufacturing one.
- **error routing** (`route_failure.py`) — no validator failure has needed
  routing on a clean run (the caption build was clean; its audit findings were
  applied via builder re-entry, not a routed check failure).

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — Notation convention for "known start, unknown end (but not ongoing)" periods

Structured `period_*` fields (affiliations, contracts, program-involvement)
have no agreed way to express a period whose start is attested but whose end
is known to have occurred yet is undated — distinct from an ongoing role,
which also renders as an open end. Decide the convention (a sentinel
`period_end`, a structured flag, or a role-text annotation) and document it in
`meta/conventions.md`; today contributors fall back to an open end plus a
free-text caveat, which conflates "ended, date unknown" with "ongoing."
Surfaced when the dead research-queue entry that hal-puthoff (a2/p1) and
russell-targ cited for this was stripped. The inverse case (unknown start,
attested active-by year) currently uses the active-by year as `period_start`
with a role-text caveat (e.g. ronald-moultrie a30/a31) — fold both into one ruling.

### C2 — `extract-source.py --source` scratch path collides for an OCR-scan PDF + its `.txt` sibling

`extract-source.py --source {path}` derives the `/tmp/scratch-{stem}.txt` name
from the path's basename **without the extension**, so an OCR-scan PDF and its
same-stem `.txt` sibling both target the same scratch file. Running `--source`
on the `.pdf` therefore overwrites a clean sibling-derived scratch with the
corrupt OCR text layer — silently. The canonical build path
(`extract-source.py --artifact {yaml}`) avoids this: it names the scratch from
the artifact slug and prefers the sibling, so the footgun is latent — but a
contributor extracting an ocr-scan PDF directly gets garbage with no warning.
Fix: discriminate the `--source` scratch name by format (`scratch-{stem}-{ext}.txt`),
or refuse/warn when a verified sibling is registered for the requested PDF.
Verify no other scratch-path consumer depends on the current name first.
Surfaced building dird-26 (the survey flagged the collision; `--artifact` was
used, so no break occurred).

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

Re-confirmed on `dird-26`: the document's author line is FOIA `(b)(6)`-redacted,
so the extrinsic author attribution (Dr. Kit Green, from the DIA→Congress
products list) cannot enter the `description` prose — the source body never
contains "Kit Green" / "products list". The established workaround (also on
`dird-24`): carry the attribution navigationally via the `[/people/…]` +
`[/documents/…]` links plus a structured `context_extrinsic` field (out of
prose-drift scope, non-rendering), keeping the name out of every quote. If the
deliberate ruling is that `description` stays strictly source-body-grounded,
document this attribution-via-links pattern as the canonical handling rather
than crediting metadata vocabulary.

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