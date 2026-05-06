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

Items with ordering or coupling constraints. A1 unblocks A2; A3 is
coupled to roadmap F.7 (finding renderer); A4 pairs with F.7. Pick
up in this order; do not skip ahead without the upstream piece in
place.

### A1. Auto-caption-vs-audio confirmation discipline (Phase F Tier 3 blocker)

Phase E's "Confirmation is a precondition for inclusion" principle
(`meta/conventions.md`) names transcripts as equivalent-footing
sources once confirmed, but does not specify what "confirmed" means
for an auto-caption transcript. A YouTube-downloaded caption file
is itself an extraction of audio by a machine-transcription service;
caption typos (e.g., "Bigalow" for "Bigelow", "lockie Martin" for
"Lockheed Martin" in Grusch's JRE episode) are structurally the
same shape as OCR character-corruption on a scanned PDF — machine
rendering of an underlying signal, with errors.

Current established practice (per
`feedback_transcript_timestamps_in_quotes.md` and Phase A work):
preserve auto-caption typos verbatim via `naming_quirks` entries
with resolution `preserve-as-sic-in-quotes`. This is a node-level
workaround; it does not resolve the broader question of whether
audio or the caption file is the authoritative source.

**Three framings to decide between:**

1. **Transcript-as-source** — what Phase E language literally says.
   Tier 3 audit just confirms quotes match the transcript file,
   which the validator already does. Cheap. Accepts caption errors
   as authentic to the source of record.
2. **Audio-as-source** — every transcript-derived quote needs
   confirmation against audio. Download audio for all transcript
   sources; sample-verify passages; possibly automate via modern
   speech-to-text diffed against the caption file, human-verify
   disagreements. Expensive.
3. **Hybrid by transcript provenance** — equivalent-footing when
   human-produced (stenographic transcripts, published interview
   transcripts — human has already done the confirmation-against-
   audio work). Audio-confirmation required when auto-caption
   (machine extraction of audio; same shape as OCR vs. page image).
   Requires classifying each transcript source via a new field
   `transcript_provenance` with values like `stenographic`,
   `human-produced`, `service-produced`, or `auto-caption`.

**Recommendation** (from the Phase F.3 closeout draft): option 3.
Most principled; aligns auto-caption handling with the OCR pattern
established in Phase A/D. Requires manifest schema field addition
+ classification pass + per-category audit methodology in
`meta/conventions.md`.

**Affected now.** 11 transcript sources, 80 quotes. Representative
cases: JRE 2065 (20 quotes — auto-caption), NewsNation Coulthart
(17 — auto-caption), American Alchemy (10 — auto-caption), plus
`when-it-mattered-55-dietrich-2021.pdf` (6 quotes — provenance
unclear, worth categorizing) and `ncas-kirkpatrick-aaro-duality`
(1 quote — auto-caption from a post-AARO Kirkpatrick presentation).
Mix expected to grow as additional interview / podcast sources land
in the corpus.

**Scope.** Convention decision can land on its own. Execution
scope depends on option chosen: option 1 is a single audit pass on
the existing transcript set; option 3 is a classification pass
across each transcript source plus sampled audio verification per
category.

**Blocks.** Phase F Tier 3. BACKLOG A2 cannot close until this
decision resolves and Tier 3 executes under it.

Surfaced: Phase F.1 diagnostic — transcript sources concentrate
~10% of the corpus's quotes; Phase E principle didn't anticipate
the auto-caption-vs-audio axis when generalizing transcripts as
equivalent-footing.

---

### A2. Verified-verbatim marker removed; full-corpus source-integrity audit (Phase F) in progress

**The principle (settled, see `meta/conventions.md`).** Confirmation
against the underlying primary source is a precondition for
inclusion in node bodies, not a rendered claim. `validate.py`'s
verbatim-quote check runs unconditionally on every block-quote with
a Source row; nodes carry no per-quote verification marker. The
discipline is enforced mechanically and is invisible to readers by
design.

**Why this entry stays open.** The principle landed via a marker
removal + validator refactor + node regeneration pass. That pass
left a corpus-integrity question: existing quotes were verified
under the old regime, which substring-matched quote text against
`pdftotext` / HTML extract output. When the source's extraction
layer is lossy (OCR-scanned PDFs, character-substituting PDF
generators), bytes-match-extract is not bytes-match-original. A
multi-tier source-integrity audit (Phase F) walks every cited
source and re-verifies extraction quality. A2 closes when Tier 6
closeout runs.

**Authoritative progress record.** Tier-by-tier methodology,
findings, and aggregate measurements live in
`meta/toolkit-notes/corpus-audit-2026-04.md`. This BACKLOG entry
tracks the high-level work plan and remaining decisions; the
closeout doc is the source of truth for audit detail.

**Schema additions shipped during Phase F.** `extraction_type`
field on `manifest_entry`, with values `text-native`, `ocr-scan`,
or `extraction-lossy`. The validator prefers a same-stem `.txt`
sibling over `pdftotext` output when extraction_type is
non-text-native — the sibling is a contributor-produced clean
transcription, visually verified against the source, with its own
manifest entry + sha256.

**Current corpus state.** 827 quotes across 144 unique source paths
across 28 research artifacts (up from 508 / 64 / 16 at Phase F.1
diagnostic — corpus has grown ~60%). The per-tier source counts in
the closeout doc were Phase F.1 snapshots; counts re-derive at each
audit-execution session.

**Remaining work.**

- **Tier 3 — transcript sources (auto-caption majority).** Audit
  blocked on BACKLOG A1 (auto-caption-vs-audio convention
  decision). Phase E's primary-source principle didn't specify
  audio-source handling; three framings are sketched in the
  closeout doc; option 3 (hybrid by `transcript_provenance`) is
  the most principled and requires schema work.
- **Tier 4 — HTML sources.** Extraction low-risk (tag-strip +
  entity-decode handles nearly all cases). Batched spot-check
  pattern across the source set.
- **Tier 5 — PDF long-tail.** Government / news / FOIA / SEC
  PDFs. Some pipelines cluster (Uintah parcel PDFs share an ORDS
  portal pipeline — verify once, apply across); the rest are
  one-by-one spot-checks.
- **Tier 6 — Closeout.** Aggregate findings across all tiers into
  the closeout doc; confirm follow-up BACKLOG entries are still
  appropriately scoped; close A2.

**Findings to date** (Tiers 1+2). Aggregate contributor-drift rate
across the audited 298 quotes: **0.67%** (6 corrections in Tier 1's
211 quotes / 0 corrections in Tier 2's 87 quotes). Tier 1 was the
worst-case segment of the corpus — high quote volume, known
extraction-layer issue (`11‡→11½` Unicode mapping), and source
complexity (54-page stenographic transcript with oral testimony +
Q&A + submitted documents). Tier 2's 0% rate in contributor-
authored short written testimonies is evidence that Tier 1's 1.4%
standalone rate was the peak, not the baseline.
**Projected remaining findings (Tiers 4+5):** 1–2 corrections.

**Recommended sequence.** Tiers 4 + 5 first (HTML and PDF long-tail
— extraction-track work, no convention decisions blocking). Tier 3
convention decision runs on its own track and should not be
collapsed into an audit-execution pass — option 3 (hybrid by
`transcript_provenance`) requires a schema field that needs the
same care `extraction_type` got. Tier 6 closeout follows once Tier
3 has executed.

**Follow-up BACKLOG entries surfaced during the audit.** All filed
for tracking; fates confirmed at Tier 6 closeout:

- **A1** — auto-caption vs audio confirmation discipline (blocks
  Tier 3)
- **C4** — `pdftotext` Unicode-mapping quirks (extraction-tool-
  layer fix; narrower than the `extraction-lossy` schema category)
- **C3** — Provenance-marker treatment on document Provenance
  tables (different shape from per-quote Verified)
- **C1** — Location reference normalization (stale `lines N-M`
  pdftotext refs; navigation-precision hygiene)
- **B1 (M2)** — naming_quirks preserve-as-sic forms unmarked in
  synthesis prose

**On C4's deferred status.** Tier 2 provided evidence that
Distiller-produced PDFs are not automatically extraction-lossy —
the Grusch written testimony uses the same Acrobat Distiller 23.0
as the Tier 1 hearing transcript but extracts cleanly. The
Unicode-mapping issue isn't consistent within a single producer, so
a wholesale tool change would be solving the wrong problem
(treating the tool as the variable when the actual variable is
upstream — font embedding, encoding tables, source-specific). The
current approach — flag lossy sources, produce `.txt` siblings,
move on — remains correct for the observed pattern. Revisit C4
only if Tier 5 surfaces a systemic pattern.

---

### A3. Person-node Statements section — three reader-visibility problems on one data-model decision

Replaces former #13, #14, #16. The Statements section on a person node
renders every quote attributed to that person, sorted chronologically.
Three problems surface here; they're tied together because the
data-model decision in Problem 3 shapes how Problems 1 and 2 should
be fixed.

**Problem 1 — Claim Inventory status column is undifferentiated.** On
whistleblower nodes, every filed-claim row renders with a hard-coded
`✅ Sworn / documented` label (in `scripts/build-from-research.py` —
grep the literal string).
Real attestation tiers vary materially:

- **sworn under oath** — congressional hearing testimony
- **sworn under penalty of perjury** — formal legal filing under
  18 U.S.C. § 1001
- **DOPSR-cleared public disclosure** — pre-publication-reviewed,
  reviewed but not sworn
- **on-record interview** — podcast / broadcast / streaming with no
  attestation ceremony

A reader scanning the inventory cannot distinguish a sworn-oath claim
from a podcast claim. Fix sketch: add an optional `attestation_tier`
enum to `quote_entry` (values `sworn-oath` / `sworn-perjury` /
`dopsr-cleared` / `on-record` / `self-attested` / `unknown`); renderer
maps tier to a differentiated status label.

**Problem 2 — Q&A answer fragments render as standalone blockquotes.**
Oral testimony produces one-word answers (`"Yes."`, `"Both."`,
`"Personally, yes."`) that the verbatim-quote check passes (the byte
appears in source) but that render as full blockquote rows whose
meaning is opaque without reading the `Attributed to` cell. Corpus
state: 9 person-node quotes are sub-30 chars; 7 are Q&A answer
fragments; 2 are legitimate terminology extracts
(`"self-licking ice cream cone"`, `"eighty-year arms race"`).
Fix sketches:

- **Q&A pair schema** — optional `question` field on `quote_entry`;
  renderer emits Q + A as a paired block. Schema extension; verbatim
  check anchors both halves against source.
- **Content-rewrite discipline** — merge tight Q&A exchanges into
  single quote entries where the answer is continuous with the
  question. Schema-stable; relies on author discipline.
- **Render-time demotion** — quotes below a length threshold render
  inline (`> **Q:** … — **A:** Yes.`) rather than as standalone
  blockquotes. No schema change; renderer-only.

**Problem 3 — cross-artifact quote duplication.** A statement made by
person X at hearing Y currently lives as identical bytes in three
places: `quotes` on the person artifact, on the hearing-event
artifact, and on the hearing-transcript artifact. Corpus state: 82
verbatim passages are duplicated across 2+ artifacts, and the
duplication grows per node built. Person nodes inflate as a
consequence (whistleblower nodes can run 1000+ lines).

This is the E.3 cross-artifact-resolver question the roadmap deferred
until ~10 nodes were through the pipeline. Threshold reached. Three
paths:

- **Path A — keep duplication, polish renders.** Each artifact owns
  its own quotes. Ship Problems 1 and 2 as render-time / schema
  additions on the existing model. Duplicates persist but Statements
  becomes scannable via tier labels and Q&A handling.
- **Path B — pull E.3 forward.** Each verbatim passage lives in
  exactly one artifact (the source-owning one — transcript for oral,
  document for text-native). Person and event artifacts carry
  `quote_refs: [qid@artifact]` pointers; the renderer resolves at
  build time. Person nodes shrink as a consequence. Whistleblower
  Claim Inventory and eyewitness Direct/Other-Statements filters
  need a cross-artifact resolver — either walk every artifact where
  `speaker_path == /people/{slug}`, or build a reverse index at
  validation time.
- **Path C — hybrid.** Ship E.3 first; re-evaluate Problems 1 and 2
  on the reformed model. Tier labels and Q&A handling likely still
  useful but their shape may shift (Q&A handling moves to the source
  artifact, not the person view of it).

**F.7 dependency.** A finding node citing a quote needs a stable
reference. On the duplicated model, `q66@david-grusch` and
`q53@2023-07-26-house-grusch` resolve to the same source passage — a
finding has to pick one arbitrarily. F.7 (finding renderer, pending
in roadmap) forces this question regardless of person-node bulk
considerations. The data-model decision should land before or with
F.7.

**Lighter alternative if Path A wins.** Add a navigation affordance —
TOC jump-links at the top of nodes ≥500 lines, or collapsible
per-venue Statements subsections. Doesn't touch the data model;
addresses the scannability symptom. Strictly cosmetic.

**Constraint from `meta/conventions.md`.** Claim Inventory is
defined as *"a render-time projection of quotes tagged
`category: filed-claim`. A filter, not a separate data structure —
the filed claim IS the quote."* Path B must preserve this filter
semantics across artifacts; the filter logic moves out of the
renderer's local-quote iteration into a cross-artifact walk.

Surfaced: Grusch rebuild — three observations converged from the
same node-build session (Problem 1 from a Claim Inventory rendering
identically across all rows; Problem 2 from oral-testimony Q&A
extraction; Problem 3 from an over-long person node prompting "can
quotes be offloaded?"). One person-node session, one design decision
point.

---

### A4. Rename `finding` → `investigation` + redesign type

Mechanical rename plus a design pass. The `finding` type will be
renamed to `investigation`; the redesign will decide what synthesis
surface an investigation node carries. See **Redesign pass** below
for the open design questions.

**Rename surfaces** (mechanical):
- `meta/schema.yaml` — `types.finding` block + `conditional_keys`
  rule for `timeline.required_when_any_of` (which lists `finding` as
  a target_node_type) + ~6 enum-list references
- Scripts — `DIRS` maps, `new.py` argparse, `validate.py`
  `node_type == "finding"` branch, any `if node_type == "finding":`
  branches in build-from-research.py / associate.py / build-state.py
  (total: 8 scripts). The scaffolder (research-scaffold.py) reads the
  type list from schema.yaml directly post-C19, so its rename is
  driven by the schema edit alone.
- `meta/templates/finding.md` → `investigation.md`
- `/findings/` directory (currently empty) → `/investigations/`
- Top-level docs — README, AGENT, CONTRIBUTING, conventions, overview,
  research-queue

**Redesign pass** (design decision deferred):
- What sections does an investigation node carry under the
  statements-only discipline? Options: quotes-only Key Passages
  parallel to documents, or a cross-reference surface parallel to
  hearing Witnesses & Testimony. See roadmap "F.7" section.
- Incorporate the investigation-pathway material that used to live in
  `research_gaps[]` (what readers expect from an active research
  thread: concrete methodology, cross-node scope, resolution state).

Surfaced: Open-Questions section removal — the rename was
deliberately deferred to a later session rather than bundled with
the removal.

---

## B. Parallel batch (renderer pass)

Items that touch the renderer and naturally batch into a single
polish pass. Per B1's own scope note, bundling reduces churn vs.
shipping each as a separate touch.

### B1. Artifact-attested nuance not reaching readers — `.note` fields dropped in tables; preserve-as-sic forms unmarked in prose

Replaces former #17 and #23. Two manifestations of the same gap:
research artifacts capture source-derived evidentiary nuance in
fields that the rendered node body silently drops or under-signals,
leaving the reader with the structured surface but not the nuance.

**Manifestation 1 — table renderers drop `.note` across relationship-bearing list sections.**

Eight list-section entry shapes carry an optional `note` field that
no current renderer emits:

- `org_relationships.note` — direct vs. downstream succession,
  oversight vs. parent-chartering, etc.
- `key_personnel.note`
- `contracts.note`
- `affiliations[].note` (person nodes)
- `relationships[].note` (person-to-person)
- `ownership_timeline.note`
- `uap_scope_activity.note`
- `location_relationships[].note`

The corresponding renderers in `scripts/build-from-research.py`
(`render_org_relationships`, `render_affiliations`,
`render_relationships`, `render_org_key_personnel`,
`render_org_primary_contracts`, `render_ownership_timeline`,
`render_uap_scope_activity`, `render_location_relationships`) emit
only the structured cells (e.g., Organization | Relationship |
Source) and drop `note` content. The `note` field IS rendered in
three other places — `rumors.note` (Primary-source refutation),
`corroboration_items.note` (What It Confirms column),
`media_versioning.note` (notes column) — so the gap is specifically
the eight relationship/list sections.

Concrete consequence on the AARO node: `or1` (DoD parent) and
`or5` (OUSD(I&S) supervisory) both render as bare `parent`
relationship type with no visible distinction; the late-July 2023
DEPSECDEF reporting-line shift documented in description prose has
no structural counterpart in the relationship table. Same shape
hits AARO with AOIMSG-vs-UAPTF predecessor disambiguation and the
IPMO co-location-vs-partner case — see "Note-rendering gap
manifestations" under AARO open notes in
`meta/topic/research-queue.md`. The UAPTF audit had flagged the
same pattern earlier with AARO-as-downstream-successor and
EXCOM-as-oversight collapsing into bare `other` relationship type.

**Manifestation 2 — verbatim source-form tokens appear unmarked in synthesis prose.**

When a primary source uses a non-canonical form (auto-caption typos,
OCR artifacts, alias-of-record), contributors register the variance
as a `naming_quirks` entry with `resolution: preserve-as-sic-in-quotes`.
Currently 74 such entries across 22 research artifacts. The verbatim
form is preserved in `quote.text` (correct per source-read-first
discipline). When the same form appears in synthesis prose
(`description`, `credibility_notes`), the reader has no explicit
signal that "Bigalow Aerospace" is the source's auto-caption output
rather than a contributor misspelling.

The Grusch node uses an implicit signal — single-quoted source form
followed by a canonical wrap link (e.g., `'Bigalow Aerospace'`
followed by [`/organizations/bigelow-aerospace`]). A discerning
reader infers the source-vs-canonical pairing from the bracket-link,
but the convention isn't documented anywhere reader-visible and
other nodes don't apply it consistently. Heaviest affected nodes:
sancorp-consulting (13 entries — pdftotext OCR artifacts: SuppOI1,
anached, thi s, etc.), alex-dietrich (8 — fraver, prinston, nits,
Nimttz, Fleer, ROC), ousd-is (8 — pdftotext extraction artifacts),
ttsa (6 — metamateiiais, struefural), aaro (5 — fulfi lled, etc.),
david-grusch (4 — Bigalow, lockie, Jim laty, Lou alzando).

**Why these are one gap.** Both surface artifact-attested
evidentiary nuance that the rendered output drops or under-signals.
M1 lives in the structured table-render path; M2 lives in the
prose-render / convention path. The fix shapes differ but the
diagnosis is shared: artifact metadata not reaching readers. Both
are renderer / convention layer; neither requires schema changes.
A single coordinated pass closes both gaps for past and future
nodes; per-node remediation is not required.

**Fix sketches.**

*M1 — render the `.note` field.*

1. **Display convention.** Inline-below row prose (indented
   paragraph below each row) reads more naturally for the 1–3
   sentences `note` actually carries; column-wise 4th-column
   "Notes" cell pushes long notes into unreadable wrapping on
   narrow screens. Recommend inline-below; confirm at prototype.
2. **Truncation policy.** Full render is probably right for an
   evidentiary repo — codify the convention once rather than
   per-section.
3. **Backlog-stub ghosting** (orthogonal but adjacent). If a
   note-bearing row references an unbuilt stub (e.g., UAPTF's `or9`
   → `/organizations/uap-excom`), the renderer could italicize /
   ghost the row to calibrate click-through expectations. Cheap to
   include if the renderer is being touched anyway.
4. **Enum-extension alternative considered and deferred.** Adding
   `downstream-successor` / `oversight` / `reporting-body` to
   `org_relationships.relationship_type` was rejected because the
   enum grows indefinitely as edge nuances surface, each addition
   is a schema commitment in advance of usage evidence, and
   rendering the existing `note` field achieves the same reader-
   visible outcome without schema prescription. Note rendering
   does NOT foreclose future enum tightening — if notes recur
   across many edges (e.g., 15+ rows saying "oversight body per
   Charter"), that becomes evidence-driven justification for an
   enum addition.

*M2 — signal source-form preservation to readers.*

1. **Inline `[sic]`** after verbatim source-form tokens in prose.
   Contributor discipline; no schema or renderer change.
2. **Renderer surface for `naming_quirks`** — emit a
   `## Source-Form Notes` section listing preserve-as-sic entries
   with their canonical forms. Surfaces 74 entries across 17
   nodes today; auto-applies to future entries.
3. **Backtick-quoted spans with trailing descriptor** —
   `` `Bigalow` [source form preserved] ``. More verbose than
   single-quote-plus-wrap; less ambiguous.

Documenting the single-quote-plus-wrap convention in
`meta/conventions.md` would also help, even without renderer change.

**Parallel renderer polish.** The note-render pass and the
end-only-period rendering (`period: – 2021` for bracketed-end-with-
unknown-start) are both passes over artifact content the structured
data already contains. If the renderer is touched broadly, grouping
related polish — column alignment, sort stability, header
formatting, note rendering, source-form notes — into one pass
reduces churn.

**Scope.** Corpus-wide. M1 affects every relationship/list row in
every node built and every node that will ever be built. M2 affects
74 naming_quirks entries across 22 artifacts today and grows as
auto-caption / OCR sources land in the corpus.

Surfaced: UAPTF audit (M1 — AARO and EXCOM rows displaying
identically to `other`-typed edges); Grusch v2 audit (M2 — auto-
caption verbatim forms in Credibility Notes prose read as
contributor misspellings without explicit signal). The same
node-build-audit cycle surfaced both shapes; reader-visibility for
artifact metadata is the umbrella.

---

### B2. `updated` frontmatter field — corpus-wide currency anchoring

**The gap.** Schema-required frontmatter across all content types
is `[id, type, schema_version, status, kind, created]`. There is no
`updated` or `last_modified` field. Body prose periodically carries time-anchored
clauses — e.g., AARO description prose carrying *"no Sancorp follow-on
or successor AARO Support Services contract is documented in archived
primary sources as of {date}"*. The "as of {date}" form freezes the
contributor's knowledge state at edit time, but a reader arriving six
months later cannot tell whether the clause reflects an actual review
on that date or is forward-projected boilerplate. Git log on the file
is the authoritative edit-history record per `meta/conventions.md`,
but readers don't reach for git log to evaluate prose currency.

**Affected surface.** Any node with rolling-currency clauses — most
acutely on government-entity org nodes where statutory deadlines,
caseload counts, contract terms, and personnel transitions accumulate
inline date anchors. AARO is the surfacing case; UAPTF, IPMO,
OUSD(I&S), Sancorp, Arlo, TTSA, and every person node with current
affiliations carry equivalent risk.

**Design choices.**

A. Add `updated:` (or `last_reviewed:`) to schema.yaml frontmatter
   `optional` set across all content types. Contributors stamp it
   when a node receives a content-currency review. Renderer surfaces
   it in the Overview row or as a node-foot annotation. Cheap;
   opt-in; no enforcement of refresh cadence. Risk: contributors
   forget to stamp.

B. Move "as of {date}" prose into a structured `currency_anchors`
   list. Each anchor: `clause` + `as_of_date` + `source.path`.
   Renderer composes the prose at build time. Heavier; forces the
   review discipline at the schema layer; surfaces the audit trail
   structurally.

C. Convention-only. Document in `meta/conventions.md` that "as of
   {date}" prose must match the most recent commit date on the node
   file, validated by a new check that reads `git log -1`. No schema
   change.

**Relationship to BACKLOG B1.** Adjacent but distinct. B1 is about
artifact-attested nuance (`note` fields, preserve-as-sic forms) not
reaching readers; this is about prose-clause currency without a
structural anchor. Both are reader-visibility issues.

**Priority.** Low. Not a correctness issue — the currency claim is
already source-attested via the underlying primary sources; the
question is whether the reader can tell when the contributor last
reviewed. Worth a single corpus-wide pass once a clear pattern emerges
across 3+ nodes.

**Scope.** Design decision (which of the three options) + schema /
renderer change + per-node sweep across nodes carrying rolling-
currency clauses.

Surfaced: AARO web audit — auditor flagged an "as of {date}" clause
as ambiguous between rolling-currency review and forward-projected
boilerplate. Currently affects AARO; pattern likely recurs corpus-wide.

---

### B3. Codify Key Passages ordering convention in `conventions.md`

The node-body renderer sorts Key Passages (and Key Testimony on
hearing events) by `statement_date` when the field is present on
entries. The ordering is currently an implicit behavior — it is
documented in `meta/conventions.md` only for hearing-kind Key
Testimony ("verbatim passages sorted by `statement_date`") and
person Statements (sorted by `statement_date` within Direct
Observations / Other Statements subsections); for document /
transcript / media / organization / location Key Passages, neither
schema.yaml nor conventions.md specifies ordering. Behavior is
emergent: artifacts with `statement_date` populated render
chronologically; artifacts without it render in artifact-entry
order; partial population produces mixed ordering.

**Concrete consequence** — TTSA audit. Populating `statement_date`
on all 44 quotes triggered chronological sort, which promoted
q5 (DeLonge email to Podesta, 2016-01-25) from mid-list to position
1 — ahead of the 2017-07-10 SEC 1-A filings. The DeLonge email is
the weakest-sourced entry in the set (self-attestation about
Roswell material and Wright-Patterson AFB, not independently
verified), and placing it at position 1 risks the chronological
convention being read as an epistemic endorsement.

Workaround applied at the time: tighten q5's `significance` header
to "DeLonge email to Podesta — claim-of-record regarding McCasland,
Roswell material, and Wright-Patterson AFB (claim made by DeLonge;
not independently verified)". The in-header framing makes the
weakest attestation carry its own epistemic hedge at the top of the
passage, independent of list position. Pattern recommendation
codified as Rule 3 below.

**Convention to codify:**

1. Chronological ordering is the corpus default for Key Passages
   across all node types that support `statement_date`. Same rule
   as the explicit hearing Key Testimony rule — extend the scope
   clause in `schema.yaml` to cover all Key-Passages sections, and
   cross-reference the behavior in `conventions.md`.
2. `statement_date` should be universally populated on quotes
   whenever the source attests a date. Partial population produces
   mixed-order rendering that confuses readers; a fully-populated
   artifact produces clean chronology. Consider promoting
   `statement_date` from optional to required where the source has
   a date (validate-research.py can warn when a quote has no
   statement_date but the source has an attested date).
3. In-header epistemic flagging is the hedge for weak attestations
   that would otherwise claim position 1 purely on chronology. The
   convention: when a quote's evidentiary weight is meaningfully
   below the median for its artifact (claim-of-record, self-
   attested, secondary-source, contested), the `significance`
   header carries an explicit hedge phrase — "claim made by X; not
   independently verified" / "claim-of-record" / "self-attested,
   contested" — so readers see the epistemic framing before they
   read the quote text. No schema change; discipline at the
   contributor layer.

**Scope note.** Rule 1 is a documentation change (schema.yaml
comment clarification + a `conventions.md` section on Key Passages
ordering). Rule 2 is a schema policy decision (whether to promote
`statement_date` from optional to required-when-attested, and
whether to add a validate-research.py warning). Rule 3 is a
contributor-discipline convention — codifying the hedge-phrase
pattern with examples in `conventions.md`. All three address the
same emergent behavior and should land in a single convention
pass.

**Current `statement_date` population** (corpus-wide, 827 quotes
across 28 artifacts):

| Target type | Populated / total | % |
|---|---|---|
| events | 21 / 21 | 100% |
| organizations | 247 / 247 | 100% |
| transcripts | 157 / 157 | 100% |
| people | 284 / 286 | 99.3% |
| documents | 40 / 99 | 40.4% |
| locations | 0 / 17 | 0% |
| **TOTAL** | **749 / 827** | **90.6%** |

Documents and locations are the gap. Documents have a partial-
population pattern (some doc artifacts populated, others not);
locations have zero coverage (suggesting the field was never
prioritized for location Key Passages — worth confirming whether
location source dates are even meaningful or whether the section
is structurally orderless). Rule 2 should land alongside per-type
guidance on what to do when no source date is attestable.

**Pattern confirmation status.** Multiple organization-node audits
have shipped since TTSA surfaced this (AARO, UAPTF, OUSD-IS, IPMO,
Sancorp, Arlo) — all populated `statement_date` and rendered
chronologically without ordering concerns surfacing. The hedge-
phrase convention (Rule 3) appears to hold but hasn't been
formally codified. Worth a single convention-pass session.

Surfaced: TTSA audit — q5 DeLonge-Podesta email promoted from
position 5 to position 1 after `statement_date` adoption; hedged
in-header in the same commit.

---

## C. Anytime (no dependencies)

Items with no upstream blockers; safe to pick up at any point in
any session. Per the preamble, this is the default-focus tier:
C work doesn't risk half-baked implementations.

### C3. Provenance-marker treatment on document node Provenance tables

Document nodes render a `## Provenance` section that tracks the
custody chain of the source file (authoring date, submission venue,
local archival, etc.). Rows use a `✅ Confirmed —` marker pattern
with evidence descriptions — for example, "PDF metadata CreationDate:
Sun Jul 23 14:41:22 2023 EDT" / "hosted at oversight.house.gov" /
"SHA256 verified via sources/manifest.yaml".

**Question surfaced during Phase B** of A2's marker-removal work:
with the per-quote `Verified` marker removed under Phase E's "no
rendered trust claim" principle, should these per-row Provenance
markers be removed too?

**Analysis from the Phase B discussion**:
the two markers look similar but do different jobs. The per-quote
Verified marker asserted "this quote matches the source" — a claim
about the quote itself that the reader could theoretically verify
but the marker was standing in for. That's the trust-performance
pattern Phase E rejects. The Provenance markers assert "this custody
event happened" — claims about the history of the artifact that
reference specific checkable evidence (PDF metadata, hostname,
SHA256). That's closer to the rendered-citation pattern (scholarly
"(Smith 2019, p. 47)") than to trust-performance: the prose after
the checkmark names the specific evidence the reader can follow.

The strongest Provenance claim is the SHA256 one (reader can literally
`sha256sum` against the archived file). Weaker is the PDF-metadata
claim (requires pulling PDF + running exiftool). Weakest is the
hostname claim (hostname may have changed since archival — the
Wayback link is the actual evidence, not the hostname).

**If revisited, the interesting move** is not removing the markers
but tightening them so the evidence is always as checkable as the
SHA256 case. That's different analysis from BACKLOG A2 and
deserves its own design pass.

**Recommendation.** Defer. Not a correctness issue (Provenance rows
are factual metadata with evidence attached; the marker is a
shorthand summary); not a readers-being-misled issue (prose names
the evidence). The analysis is genuinely different from A2 — the
removal pattern from A2 would be wrong if applied here.

**Scope if taken up.** Per-provenance-row audit: categorize each
marker's underlying evidence by checkability (SHA256-level / tool-
required / external-attestation); tighten wording to surface the
distinction where useful; or decide the current pattern is fine
given Phase E's principle doesn't scope to Provenance tables.

Surfaced: Phase F spot-check review of `✅ Confirmed —` patterns in
rendered nodes — Provenance markers share the marker pattern with
the per-quote Verified row but don't share the trust-performance
shape.

---

### C6. Migrate residual `contracts[].value` analytical prose to `.note` once BACKLOG B1 ships

**The gap.** Schema spec for `contract_entry.value` is a label-shaped
dollar string — *"$22 million" / "$22M" / "22,000,000"* per
`meta/schema.yaml:986-988`. Two contract entries on
`/organizations/arlo-solutions` carry multi-sentence analytical prose
in `value`: c10's USAspending base_and_all_options systemic-conflation
observation, and c11's three-source value reconciliation with the
≥$6.5M unreconciled-gap observation. Schema-correct home for that
prose is `.note` (in prose-drift scope, drift-checked, in-scope per
`feedback_prose_drift_warnings_must_resolve.md`). But `.note` does
not render in the Primary Contracts table today — that's the BACKLOG
B1 (table renderers drop `.note` field) gap.

**Why this entry is B1-tied, not standalone.** Migrating the prose
from `value` to `.note` *today* would lose two reader-visible
analytical observations until B1 ships. Per
`feedback_reader_visibility_discipline.md`, fixes must surface in
rendered output; trading visibility for schema-conformance is a
regression. So the migration waits on B1.

**Pre-staged work that already shipped (Arlo audit, this session,
Option B).** The duplicated content in c10.value (3-of-4 vendor
attribution, "not Arlo's individual ceiling" explicit framing) was
trimmed because the same facts already render in description ¶2 +
Timeline rows; the unique systemic-conflation observation stays in
`value` until B1 enables clean migration. c11.value left as-is —
its content (multi-source figure reconciliation with W5 field-name
disambiguation, ≥$6.5M unreconciled-gap observation) is all unique
to that surface. So the residual misuse is precisely two analytical
observations across two entries on one node.

**Post-B1 cleanup scope (when this entry fires).**

1. Move c10 systemic-conflation observation from `value` to `.note`.
   c10.value reduces to `"$856,000,000 — good faith estimate amount,
   aggregate across four BPA vendors."` — clean schema-conformant
   dollar string with source-attested gloss.
2. Move c11's reconciliation-gap observation (the ≥$6.5M
   unreconciled gap analytical claim) from `value` to `.note`.
   c11.value retains the multi-source canonical figures with
   W5 field-name disambiguation.
3. **Verify duplication doesn't reintroduce when migrating** —
   c10 and c11 already have populated `.note` fields with their
   own content. The migration target is "extend the existing
   note with the analytical observation," not "replace the note."
   Confirm migrated content doesn't duplicate what's already in
   note, in description, or in Timeline.
4. Validate prose-drift on the extended notes — the analytical
   observations use vocabulary like "systemic conflation",
   "unreconciled", "floor", "ceiling" that may need source-
   vocabulary alignment to clear the drift check.

**Corpus impact.** Confirmed Arlo-only. `sancorp-consulting`
(the only other artifact carrying `contracts[]`) has 17 entries,
all with 1-3 word `value` strings — schema-conformant and not
affected. No other gov-contractor org artifacts exist today.

**Priority.** Low. Bounded scope (2 entries, 1 artifact); cleanup
fires automatically when B1 ships.

**Scope.** ~10 minutes after B1 ships: migrate two analytical
observations from `value` to `.note`, regenerate, validate, verify
rendered Primary Contracts table shows the migrated content via
B1's note-rendering surface.

Surfaced: Arlo Solutions audit Phase 3 close-out review (Claude Web
greenlit Option B trim of duplicated `value` prose; B1-dependent
residual cleanup deferred to this entry).

---

### C8. Quote.text leading-timestamp discipline — drift between in-text marker and actual quote-start

The existing convention in
`feedback_transcript_timestamps_in_quotes.md` codifies that quote.text
on caption-source quotes carries at most ONE leading `[MM:SS]` marker
as the navigation anchor, with intermediate markers stripped. Two
failure modes the memory doesn't address have surfaced in the corpus.

**1. Drift between leading marker and quote-start.** The in-text
leading `[MM:SS]` is sometimes 4-9 seconds AFTER the source line where
the quote's first content word appears. The marker still lands on
quote content (not adjoining material) but doesn't anchor the actual
start. Reader clicking through to navigate lands mid-quote, missing
the start. Concrete cases (alex-dietrich, surfaced in 2026-05-04
cluster-1 re-review):

| qid | in-text marker | actual start in source | drift |
|---|---|---|---|
| q17 | `[1:00:56]` | `[1:00:48]` | +8s |
| q18 | `[1:02:00]` | `[1:01:51]` | +9s |
| q19 | `[5:25]`    | `[5:19]`    | +6s |
| q21 | `[56:42]`   | `[56:34]`   | +8s |
| q23 | `[19:37]`   | `[19:30]`   | +7s |
| q25 | `[15:26]`   | `[15:24]`   | +2s |
| q28 | `[58:44]`   | `[58:40]`   | +4s |
| q38 | `[9:24]`    | `[9:20]`    | +4s |
| q40 | `[13:45]`   | `[13:41]`   | +4s |

None observed in david-grusch caption-source quotes — pattern appears
contributor-specific (alex-dietrich and david-grusch were authored in
different sessions).

**2. Intermediate markers retained in quote.text.** Two david-grusch
quotes carry interior `[MM:SS]` markers explicitly forbidden by the
existing memory:

| qid | text snippet | extra marker(s) |
|---|---|---|
| q21 | `know, isotopic ratios that would have to [13:05] be engineered…` | `[13:05]` |
| q29 | `so I was a Intel officer [0:36] in the Air Force for 14 years…` | `[0:36]` |

**Why this is its own item.** Both failure modes are quote.text
content issues, distinct from the location-ref form addressed by C1.
C1 closes the location-ref dimension; this item closes the in-text
marker dimension. Combined, the two close out the timestamps-memory
convention end-to-end.

**Why deferred from C1.** Phase C of C1 is location-ref-only by
design — touching quote.text during a location-ref conversion would
mix two discipline axes and risk drift. Cluster 1 of C1 (2026-05-04)
preserved the contributor's leading markers verbatim to keep the
rendered blockquote anchor consistent with the Location row;
tightening the in-text marker requires its own pass that updates
both quote.text AND source.location together so they stay aligned.

**Fix sketch.**

1. **Detection.** Either extend `scripts/normalize-locations.py` with
   a `--text-markers` mode or write a small sibling script. Per
   caption-source quote:
   - Extract leading `[MM:SS]` from quote.text (when present).
   - Find the source line where the quote's first 4-6 content words
     appear.
   - Compare timestamps; flag drift >5 seconds.
   - Detect intermediate `[MM:SS]` markers in the quote.text body.

2. **Per-quote correction.** For each flagged quote:
   - Replace the leading `[MM:SS]` with the actual-start timestamp.
   - Strip intermediate markers.
   - Update `source.location` to match the new leading marker
     (preserves blockquote/Location-row consistency).
   - Regenerate the rendered node body via `build-from-research.py`.

3. **Memory update.** Add a sentence to
   `feedback_transcript_timestamps_in_quotes.md`: leading `[MM:SS]`
   matches the timestamp on the source line where the quote's first
   content word appears, not a later caption tick the contributor
   encountered while reading. Include one drift case as a concrete
   example.

**Scope.** 11 currently flagged quotes (9 drift + 2 intermediate-
markers), all in alex-dietrich and david-grusch. Bounded — only
caption-source quotes are at risk. Future caption-source quote
authoring uses the updated memory.

**Priority.** Low. Not a correctness issue; navigation-precision
improvement. Validator doesn't care.

Surfaced: Cluster 1 conversion re-review (2026-05-04) — spot-check
of converted location refs against source content surfaced both
failure modes.

---

### C9. *(removed 2026-05-05 — abandoned per user direction; the planned memory-to-meta migration was discretionary cleanup without unblocking value. Methodology remains functional via auto-loaded MEMORY.md; entry would have generated work for a benefit only future fork-targets see.)*

---

### C10. Subdivide `meta/toolkit-notes/` when retrospective files accumulate

`meta/toolkit-notes/` currently holds three long-form retrospective /
design files: `corpus-audit-2026-04.md` (closeout for BACKLOG A2),
`cross-artifact-consistency-check.md` (technique doc surfaced from
BACKLOG C1), `pilot-failure-2026-04-17.md` (Step C postmortem). At
n=3 a flat directory reads fine. As the toolkit accumulates more
closeouts and design records, the directory will get noisier than
scannable.

**Trigger to revisit.** When `meta/toolkit-notes/` reaches ≥5
long-form retrospective files, propose a subdivision convention.
Likely shape: `closeouts/` for retired-audit closeouts (corpus-audit-
2026-04 as the canonical example), root for forward-looking
design / technique notes (cross-artifact-consistency-check as the
canonical example). Sort-by-year and sort-by-topic are alternative
shapes; decision lands when n≥5 makes the comparison concrete.

**Why deferred.** Three files don't justify subdivision — *"don't
design for hypothetical future requirements"* per CLAUDE.md. Trigger-
on-accumulation lets the structure emerge from real data rather
than imposing it speculatively.

**Priority.** Low. Pure tidiness; no correctness implications.

**Scope.** When triggered: 30-min design pass + N file moves +
cross-reference updates (no current refs traverse to specific
files within `toolkit-notes/`).

Surfaced: 2026-05-05 governance-doc reorganization — original
investigation flagged `corpus-audit-2026-04.md` as a candidate for
"some reorganization" but determined three files don't justify
forcing shape; codified the trigger condition here.

---

### C11. *(retired 2026-05-05 — every named check lives at scripts/checks/{name}.py; validate.py / validate-research.py / review-coverage.py are thin orchestrators with explicit step lists per the C11 design doc; full session-1/2/3 progress preserved in git log; design rationale at meta/toolkit-notes/c11-validator-decomposition-design.md.)*

---

### C13. *(retired 2026-05-05 — every check yields scripts/checks/__init__.py:Issue; legacy Issue classes deleted from validate.py / validate-research.py / review-coverage.py; check_name + fatal contract fields adopted across all checks; closed alongside C11 in session 3.)*

---

### C14. *(retired 2026-05-05 — see commit `1c34081`; manifest checks fully migrated, load-3x duplication closed.)*

---

### C15. *(retired 2026-05-05 — schema-driven iff dispatch landed in commit `dc95d39`. New `scripts/checks/iff_section.py` reads `schema.yaml::types.research-artifact.conditional_keys` and emits all placement errors; per-section checks call `section_in_scope` for gating. Schema grammar upgraded from flat OR-keys to `required_when_any_of: [list of AND-rules]` to express conjunctions like witnesses_testimony's type=event AND kind=hearing. ~360 LOC of duplicated gate logic deleted across 18 per-section checks + artifact_top_level.)*

---

### C16. *(retired 2026-05-05 — `ResearchContext.regenerated_body` lazy property landed in commit `4b1cfd3`. Subprocess spawned once per artifact on first access; cached as `(body, error)` tuple for the lifetime of the context. boundary.py reads the cached value; future cross-layer consumers benefit without re-implementing subprocess + caching machinery.)*

---

### C17. Per-check investigation pass

The C11/C13/C14 cluster decomposed every named validator check into a
per-module callable in `scripts/checks/`. Each check reads clean and
is individually importable, but no contributor has done a focused
review pass on its intent, anchoring, or comment discipline.

Per-check work:

1. **Production-issue anchor.** Identify the concrete failure mode
   the check was created to catch, and confirm its logic actually
   catches that mode. `git log --diff-filter=A` on the module file
   finds the introducing commit; from there, BACKLOG / toolkit-notes
   / postmortem entries usually trace the surfacing incident.
2. **Logic review.** Surface dead code, ambiguous behavior, or schema
   gaps the check has been quietly accepting. Small fixes ship in the
   same commit; larger ones become BACKLOG entries.
3. **Docstring + comment discipline.** No dates, no session lore, no
   didactic examples; anchored to BACKLOG IDs, schema field paths,
   conventions.md sections.

Per-check tracking lives at
[`meta/toolkit-notes/check-audit.md`](toolkit-notes/check-audit.md):
status by check + sequencing recommendation batched by Context type.

**Tradeoff recorded.** An earlier shape of this entry called for
synthetic-broken-input unit tests per check — that pilot shipped and
was removed on the judgment that 49 test modules is more carrying
cost than the regression coverage buys at this corpus size. The gap
remains: a refactor that breaks a check's error path is detected only
when a contributor encounters a real broken input. Documented here so
the question doesn't get re-litigated each session.

**Status.** Complete (49/49 ✅). All named validator checks
investigated; per-check tracking lives at
[`meta/toolkit-notes/check-audit.md`](toolkit-notes/check-audit.md).

The investigation surfaced eight substantive findings beyond
docstring polish:

  - Disproved hypothesis: ``doc_form_archival_status`` (commit
    ``3ae1296``) — initially flagged as "likely subsumed by
    conditionally_required"; investigation showed orthogonal
    concerns, not subsumption.
  - Filed and CLOSED BACKLOG ``C20`` — ``timeline.timeline_category_values``
    declared "extensible; validator warns on unknown" but warn was
    never implemented. Closeout removed the schema list rather than
    wiring the warn, on the principle that the list had no consumer
    and the field has always operated as free-text (the canonical
    list was cargo-cult decoration).
  - Fixed bug: ``status_archetype_kind`` truthy-guard layering
    bug (commit ``610a695``) — null archetype/kind/status slipped
    through both presence + enum checks; tightened to presence-
    guard semantics.
  - Synced stale fallback: ``table_cell_word_budget`` hardcoded
    fallback (50) lagged schema bump to 55 by ~3 weeks (commit
    ``1352006``).
  - Filed and CLOSED BACKLOG ``C21`` — silent
    ``ctx.schema.get(..., default)`` fallbacks across 6 sites
    masked schema drift; removed all six in a coordinated sweep
    (commits ``c42acea`` + ``719bca8``).
  - Fixed schema-doc drift: ``vouching_chain`` schema comments
    claimed "renders inside Credibility Notes" but renderer emits
    standalone H2 (commit ``b9905c5``).
  - Filed BACKLOG ``C22`` — ``uap_relevance`` + ``uap_scope_activity``
    are explicitly UAP-named, contradicting the toolkit's "schema
    is topic-neutral" scope claim (commit ``397d994``).

Pattern observation: anchor shapes cluster into roughly six
families — reactive incident; defensive feature-pairing; renderer-
coupled entry-list; foundational schema discipline (with sub-shapes
stable/stable, multi-stage, evolving-discipline, forward-defensive);
hybrid additive-and-reductive multi-stage; metadata-only channel.
Multiple paired-check families also surfaced (verbatim_quotes ↔
coverage; prose_drift ↔ description_token_drift; frontmatter_
required ↔ id_path_match ↔ status_archetype_kind; relationship-
shape taxonomy across 4 checks).

Surfaced: C11/C13/C14 closeout audit — verification pass spot-checked
individual check error paths but didn't commit a per-check review.
Logged so the gap doesn't drift out of awareness.

---

### C19. *(retired 2026-05-05 — scripts/research-scaffold.py now reads schema.yaml::types.research-artifact.conditional_keys via the same evaluate_required_when helper the validators use; commit `73fbae2`. Removed RUMORS_TYPES, TIMELINE_TYPES, ARCHETYPE_SECTION, KIND_SECTIONS_BY_TYPE constants + 6 inline `if node_type == "X":` blocks. Replaced with single loop over conditional_keys + small EMPTY_SECTION_SHAPES map (4 entries for prose fields and event_intrinsic dict; everything else defaults to []). evaluate_required_when refactored to take positional args (target_type, target_archetype, target_kind) so the scaffolder can dispatch without faking a Context. build-from-research.py renderer dispatch — type-intrinsic rendering logic, gated by validator before render runs — remains as-is per scope note.)*

---

### C22. Topic-customization mechanism + rename `uap_*` → `top_*`

The toolkit's scope statement (``README.md`` + ``meta/conventions.md``
"Scope") claims schema and structure are topic-neutral. Two schema
field names contradict that — ``uap_relevance`` (person artifact;
renders as ``## UAP Relevance``) and ``uap_scope_activity``
(location artifact; renders as ``## UAP-Scope Activity``). A fork-
target on a different investigation inherits these UAP-named fields
and section headers; the README's "Forking for a different topic"
instructions don't cover the inline rename needed to make them fit
the new topic.

The fix isn't just rename. The toolkit lacks a topic-customization
mechanism altogether — fork-targets currently inherit a hard-coded
UAP topic identity in field names + rendered headers + (potentially)
elsewhere as the instance grows. C22 scope is to establish the
mechanism, then use it to rename ``uap_*`` → ``top_*`` as the first
application.

**Mechanism.** Promote ``meta/topic/overview.md`` from "required
prose document" to "the canonical topic-config record." overview.md
already exists, is required (existence-checked by ``validate.py``
main()), and carries the topic identity at narrative grade
(scope statement, primary corpora, agent orientation). Add two
additive frontmatter fields:

```yaml
id: meta/topic/overview
type: meta
schema_version: 1
created: 2026-04-17
topic: uap                # lowercase identifier; matches /meta/topic/ instance
display_name: UAP         # rendered text in section headers + agent prose
```

The prose body stays untouched. ``governance_files`` check learns
the two fields are required when ``id == meta/topic/overview``.

Rationale: overview.md is already the topic's identity-of-record;
prose body + structured frontmatter together is the same pattern
as research artifacts (which carry both YAML config + prose
``description``). No new required file.

**Bootstrap flow.** Existing fork instructions delete
``meta/topic/`` along with content. A fresh fork-target needs to
recreate ``meta/topic/overview.md`` with the new frontmatter
fields populated + prose-body scaffold. Handled by a new
paste-ready prompt:

``prompts/fork-init.md`` — paste into a fresh Claude Code session
when bootstrapping a fork target. The prompt:

  1. Detects ``meta/topic/overview.md`` is missing (validate.py
     exits 1 with the canonical "Required file missing" error).
  2. Prompts the user in-conversation for:
     - ``topic`` identifier (lowercase; e.g., ``uap``, ``warhol``,
       ``oklahoma-bombing``)
     - ``display_name`` (rendered text; e.g., ``UAP``, ``Warhol
       Estate``, ``Oklahoma City Bombing``)
  3. Generates ``meta/topic/overview.md`` with the new
     frontmatter fields + topic-statement template + scope-
     boundaries scaffold (template lives in ``meta/templates/`` or
     inline in the prompt).
  4. Runs ``scripts/tests/pre-commit.sh`` to verify clean state.
  5. Hands off to ``prompts/onboard.md`` for normal session start.

Same pattern as existing ``prompts/onboard.md`` /
``prompts/build.md`` — a paste-ready workflow for a specific
phase, not a CLI script.

**Implementation surfaces:**

  - **overview.md frontmatter** — additive fields ``topic`` +
    ``display_name`` on the existing required file. No new file.
  - **``governance_files`` check** — learns that overview.md
    frontmatter requires ``topic`` + ``display_name`` (gated on
    ``id == meta/topic/overview``).
  - **New helper** in ``scripts/lib/_common.py`` —
    ``load_topic()`` reads overview.md frontmatter, returns
    ``{topic, display_name}``. Cached per-process. Errors loudly
    if overview.md is missing or the fields are absent (consistent
    with the C21 schema-config "no silent fallbacks" principle).
  - **Schema rename** — ``uap_relevance`` → ``top_relevance``;
    ``uap_scope_activity`` → ``top_scope_activity`` in
    ``schema.yaml``, ``conditional_keys`` rules, ``required_keys``
    invariants, all schema comment cross-references. The schema
    field-name prefix is fixed-toolkit-neutral as ``top_*``
    regardless of instance topic; per-instance customization
    happens at the rendered-header layer via ``display_name``
    substitution.
  - **Renderer change** — ``scripts/build-from-research.py`` reads
    ``load_topic()`` and substitutes ``display_name`` in section
    headers: ``## {display_name} Relevance``,
    ``## {display_name}-Scope Activity``.
  - **Validator check rename** — rename
    ``scripts/checks/uap_scope_activity.py`` →
    ``top_scope_activity.py`` plus all internal references.
  - **Existing artifact migration** — rename ``uap_relevance:`` →
    ``top_relevance:`` across the 6 person artifacts; rename
    ``uap_scope_activity:`` → ``top_scope_activity:`` on the 1
    location artifact (skinwalker-ranch).
  - **Existing rendered nodes** — regenerate via
    ``build-from-research.py``. With ``display_name: UAP`` in
    overview.md, the rendered output should be byte-identical to
    current state (UAP-named headers stay UAP-named, just driven
    by config rather than hardcoded). Verify via
    ``scripts/tests/pre-commit.sh`` clean pass.
  - **Prompt** — new ``prompts/fork-init.md`` orchestrating the
    bootstrap workflow.
  - **README** — one-sentence amendment to "Forking for a
    different topic": "After deleting ``meta/topic/``, run
    ``prompts/fork-init.md`` in a fresh session to bootstrap your
    topic." No expansion beyond that.
  - **CLAUDE.md** — no change. Existing-instance contributors
    don't need to know about the bootstrap flow; overview.md is
    already in place.

**Audit pass for other UAP-hardcoded surfaces.** Beyond the two
schema field names + their rendered headers, grep the codebase for
hardcoded UAP references that should also become topic-driven:

  - Section headers in templates (``meta/templates/*.md``)
  - Prompt files (``prompts/*.md``)
  - Error-message strings in checks / scripts

Audit findings determine which become topic-aware vs. which stay
UAP-specific because they're load-bearing for THIS instance's
investigation (the topic-statement prose in overview.md, corpus
addendum names like ``aawsap-dird``, etc.).

**Open question on prefix.** ``top_*`` per the user's instruction
(shorter); ``topic_*`` is the unambiguous alternative if the
shortened form reads awkwardly in artifact YAML. Resolve at
implementation time.

**Priority.** Low. Not a correctness issue — toolkit operates
correctly with UAP-named fields. The gap is fork-readiness and
philosophy-vs-reality alignment. Worth resolving when the toolkit
is ready to support a second instance.

**Scope.** Mechanism + rename + audit pass + bootstrap prompt.
Realistic estimate: ~4-6 hours focused — small per-piece work
multiplied by the ~6-surface audit + verification that pre-commit
stays 0/0 through the migration. Single coherent session; don't
fragment.

**Design rationale (why this consolidates onto overview.md
frontmatter rather than introducing a new ``topic.yaml``).** The
toolkit's existing pattern is "one file owns one identity." research
artifacts carry both structured fields + prose ``description`` in
the same file; this design extends that pattern to the topic-
identity layer. overview.md is already required, already validated,
already read at session-start by humans + agents. Promoting it from
"prose document" to "config + prose document" with two additive
frontmatter fields keeps the topic-identity surface consolidated and
avoids parallel files that could drift. The README's existing fork
instructions ("Create your own ``meta/topic/overview.md``") become
"Run prompts/fork-init.md to generate your overview.md" — same
required-file destination, just with a paste-ready bootstrap.

Surfaced: C17 ``uap_scope_activity`` investigation revealed the
contradiction between the toolkit's stated philosophy and schema
reality. User-directed reframe (Round 1) expanded scope from
"rename the two fields" to "establish topic-customization
mechanism, then rename". User-directed reframe (Round 2) consolidated
the topic-config storage onto overview.md frontmatter rather than a
new ``topic.yaml`` file, on the principle of complementing the
existing repo design rather than paralleling it.


