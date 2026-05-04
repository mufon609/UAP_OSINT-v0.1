---
id: BACKLOG
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

Items waiting on an external event (FOIA resolution, registry access,
etc.) the repo can't drive live in a separate section at the bottom
("Externally blocked"). They aren't numbered — there's no in-repo work
to schedule until the external trigger fires.

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
`✅ Sworn / documented` label (`scripts/build-from-research.py:723`).
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
- `meta/schema.yaml` — `types.finding` block + ~6 enum-list references
- Scripts — `DIRS` maps, `TIMELINE_TYPES`/`RUMORS_TYPES` sets,
  `new.py` argparse, `validate.py` `node_type == "finding"` branch
  (total: 8 scripts)
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

### C1. Location reference normalization — stale pdftotext line refs in quote Locations

Quotes across the corpus cite `Location: lines 805-810` or similar
line-range references that point at line numbers in pdftotext output
of the cited source rather than government page numbers or other
stable document anchors. These were keyed to the pdftotext extraction
in use at the time the quote was authored.

**Problem shape.** The validator's verbatim-quote check verifies
quote text substring-matches the extract; it does NOT verify Location
accuracy. So stale `lines N-M` refs don't cause validation failures,
but they become increasingly imprecise as sources get re-extracted
(e.g., Phase F Tier 1's clean-text sibling renumbers the hearing
transcript).

**Scope (current corpus).** 356 quotes across 16 artifacts cite
line-range Locations of this shape. Affected artifacts include the
three House Oversight 2023-07-26 hearing artifacts (fravor / graves /
grusch), the SASC AARO hearing transcript, written-testimony
documents, and AARO / Skinwalker Ranch / multiple person nodes.
Corpus-wide normalization, not a per-artifact spot fix.

**Second imprecision shape — boundary inclusion** (surfaced during
the 2023-04-19 SASC AARO hearing event build). Beyond re-extraction
staleness, contributor-authored Location refs can be imprecise from
the start by including adjoining material in the range. Concrete
cases on `research/2023-04-19-sasc-aaro-hearing.yaml`: q8 cites
`lines 1784-1792` but Kirkpatrick's spoken portion ends at line 1788
(Sen. Rosen interrupts at 1789, page footer at 1791-1792). q11 cites
`lines 2178-2183` but the quote content runs 2180-2182 (prior speaker
turn at 2178-2179, next speaker at 2183). Different root cause from
staleness — caught during writing rather than during re-extraction —
but same fix target: tighter ref discipline using the conventions
below. The systematic sweep addresses both shapes.

**Fix shape.** Systematic conversion of `lines N-M` refs to:
- `p. N, ¶M` for stenographic PDFs (hearing transcripts)
- `p. N` for single-line citations
- `¶N` for short documents without pagination
- `[MM:SS]` ranges for transcript/caption sources
- `lines N-M of the extract` explicitly when the extract is the
  intended reference (rare)

The conversion is mechanical per quote once the rule is written
down, but each quote needs a per-source read to determine the
correct replacement form. Tooling could help (a script that reads
each quote's source and proposes a normalized Location) but
human-in-loop verification is still needed for boundary-inclusion
cases.

**Priority.** Low. Not a correctness issue; navigational-precision
improvement for readers. Validator doesn't care.

**Scope.** Corpus-wide normalization across 356 quotes / 16
artifacts. Independent of the Phase F audit tiers; can run before,
after, or between them. Tooling-pass + per-source review per quote
(no fully-mechanical fix because boundary-inclusion correction
requires reading the quote against its source).

Surfaced: Phase F Tier 1 — the hearing-transcript `.txt` sibling
used government page numbers as section markers, which rendered
existing `lines N-M` quote Locations increasingly out-of-sync.
Corrections deferred per explicit Phase F Tier 1 scope decision
(Phase F is about extraction integrity, not navigation precision).

---

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

### C4. pdftotext Unicode-mapping quirks on text-native PDFs (extraction-tool-layer)

The `extraction-lossy` enum category added in Phase F Tier 1 captures
the high-level source-condition pattern: text layer present (not
OCR'd) but pdftotext produces artifacts. The underlying root cause
for the known case (hearing transcript PDF, `11½` rendering as
`11‡` via pdftotext) is specifically a Unicode-mapping issue at the
PDF-generation layer — Acrobat Distiller mapped U+00BD ONE HALF to
U+2021 DOUBLE DAGGER in the text stream.

**Possible narrower fix:** use a different PDF text extraction tool
(e.g., `pdfplumber`, `pymupdf`, `mutool`) that handles this Unicode
mapping correctly, rather than producing a clean-text sibling per-
source. If the alternate tool gives clean output on the hearing
transcript and all other corpus PDFs, the extraction-lossy category
might dissolve for the Unicode-mapping subcase, leaving only
genuinely OCR'd sources needing siblings.

**Scope consideration.** This is a narrower question than the
extraction-lossy schema category. The category stays regardless —
OCR sources still need sibling handling. But if a tool change could
eliminate the Unicode-mapping failure mode across the corpus, that
reduces the sibling-production workload for future tiers of the audit
(and for future contributors adding sources).

**Methodology for evaluation** (deferred to a separate session):
run alternate PDF extraction tools against the hearing transcript
PDF; compare output to the known-correct visual content; check for
`11½` rendering correctness; check other Unicode edge cases
(fractions, typography, signature glyphs, section signs). If an
alternate tool gives clean output uniformly, propose adopting it in
`validate.py` as the PDF extraction path (with pdftotext retained
as fallback for compatibility).

**Affected now.** Hearing transcript PDF (only known case to date).
Future corpus PDFs may exhibit similar conditions — evaluation cost
is bounded.

Surfaced: Phase F Tier 1 — `11‡` for `11½` caught during hearing-
transcript audit; extraction-lossy enum added to handle the pattern
generically, but the specific case might have a narrower solution
at the tool layer.

---

### C5. Codify description-vs-structured-table date-precision discipline

**The gap.** `meta/conventions.md` does not specify how dates should
divide between description prose (synthesis, prose-drift checked) and
structured surfaces (Primary Contracts, Timeline, Key Personnel,
Ownership Timeline) that carry source-attested per-row metadata.
Contributors have written description prose that duplicates
field-precise dates already living in a structured surface — and
because the prose layer rephrases ("on April 18, 2024" / "established
the BPA on February 14, 2025"), the duplication creates a drift surface
between the two layers without adding evidentiary value.

**Concrete cases on `/organizations/arlo-solutions`.** The Arlo
audit (this session) surfaced the pattern twice:

1. *HQ003424F0190 (CL&S contract).* Original description prose:
   *"a $3.7 million contract with the OUSD(I&S) CL&S Integrated
   Vetting team on April 18, 2024"*. April 18 is the press-release
   announcement date; the contract's period of performance start
   date per USAspending is April 30. Description prose conflated
   the two. Fix shipped: trim description to "announced by Arlo
   on April 18, 2024" only; let the Primary Contracts row carry
   the precise period_start / period_end.
2. *HQ003425A0004 (Enterprise BPA).* Existing description prose:
   *"On February 14, 2025, WHS established the OUSD(I&S)
   Enterprise BPA HQ003425A0004"*. USAspending's date_signed is
   2025-02-14; period_of_performance.start_date is 2025-02-15.
   Same loose-shorthand pattern (signing-date as proxy for period-
   start). Acceptable as narrative-grade orientation if the
   convention is codified, but currently unwritten.

**Convention to codify.** A line in `meta/conventions.md` along the
lines of:

> Description prose carries orientation-grade dates anchored to
> semantic events ("announced", "issued", "filed", "took office",
> "established"). Field-precise contract / period dates live in
> their structured surface (Primary Contracts, Timeline, Key
> Personnel, Ownership Timeline) where they are source-attested
> per row. Description should not duplicate field-precise dates
> from a structured surface; if a date is in the table, the
> description can refer to the event without re-stating the
> field.

**Why it helps the researcher.** Three layers, three roles —
description for landscape, structured table for field-precise
data, Key Passages for verbatim source. Each precise date lives
in exactly one layer; the others reference the event without
re-stating the field. Eliminates the drift surface between
description and table; reduces prose-drift-check friction;
matches what the layered build process already does in
practice.

**Inverse case — structured surface must carry the dates the
prose defers to.** The convention assumes description prose CAN
defer to a structured-surface counterpart. When a structured
row is missing a source-attested date the prose names, the
convention has a gap: "table is authoritative for field-precise
dates" only works if the table carries those dates. Concrete
example on `/organizations/arlo-solutions`: contract row c10
(HQ003425A0004 BPA) populates `period_start: '2025-02-14'` only;
no `period_end`. USAspending's API record actually attests
`period_of_performance.end_date: '2030-02-14'` (5-year ordering
period — base + four 1-year options per the RFQ). With c10
missing period_end, description prose's "On February 14, 2025,
WHS established the BPA" has no structured-surface counterpart
for the BPA's ordering-period closure. Convention codification
should pair with a discipline rule: BPA / IDV / multi-year
contract rows populate period_end from USAspending
period_of_performance when source-attested, even when the
prose layer doesn't explicitly call out the end date. Otherwise
the layered-precision principle has a class of contracts where
it can't be applied.

**Affected now.** Corpus-wide pattern. AARO, UAPTF, IPMO,
OUSD-IS, Sancorp, Arlo, TTSA all carry description prose with
embedded field-precise dates that also live in their respective
structured tables. No regression risk — codification doesn't
change existing prose unless contributors choose to align it.

**Priority.** Low. Not a correctness issue (the table is the
authoritative surface today; description prose is acceptable
narrative). Discipline-uniformity issue; codification would
prevent future contributors from re-introducing the conflation
pattern (W1 above) and surface a clear answer when prose-drift
flags a date-related compound term.

**Scope.** Single convention pass — add a section to
`meta/conventions.md` ("Date precision in description prose"),
cross-reference from schema.yaml comments on `description`
fields. Optional: validator advisory that flags when a
description prose token matches a date string also appearing in
a structured surface on the same artifact (would require
field-aware tokenizer changes).

Surfaced: Arlo Solutions audit Phase 1 / Phase 2 (W1) —
"$3.7M contract on April 18, 2024" conflated press-release date
with USAspending Start Date; fix landed by trimming description
to announcement only and letting the Primary Contracts row
carry period-of-performance precision.

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

## Externally blocked

Items waiting on an external event the repo can't drive — FOIA
resolutions, subscription registry access, third-party publication.
Each has a clear closure path. They aren't numbered because there's
no in-repo work to schedule; they sit here for visibility so a
future session reviewing the relevant node or context knows the
trigger is pending.

### Reveal Systems Inc. — California SoS / OpenCorporates registry hunt

Per the Kirkpatrick audit § 7 ("Items still open"), specific
state-of-incorporation entity number, filing date, current operating
status, and principals-beyond-inventor list for the Kirkpatrick /
Bogaard / Fairchild patent-assignee Reveal Systems Inc. were not
retrievable through open-access channels. What was established during
the archival pass:

- California is the state of incorporation per the May 2020 USPTO
  assignment record on US20200357080A1: the assignment-of-assignor's-
  interest record on the original non-provisional names "REVEAL
  SYSTEMS, INC., CALIFORNIA" as the assignee.
- The California Secretary of State business search portal is
  Imperva-blocked at the API layer (HTTP 403 to all automated POSTs);
  the bizfileonline.sos.ca.gov frontend returns an Incapsula JS
  challenge page with `noindex,nofollow` headers. Wayback Machine
  has no usable captures of registry-search result pages.
- OpenCorporates is HAProxy CAPTCHA-blocked (hCaptcha challenge on
  every request) and has no Wayback presence for Reveal-Systems-named
  entities.

**Name-collision warning** (load-bearing for any future Reveal Systems
Inc. node build under audit § 6): a different "Reveal Systems Inc."
exists with a Bloomberg company profile (ticker `0408205D:US`) — that
entity produces real estate software (custom legal forms, contracts).
It is **not** the patent-assignee Reveal Systems Inc. Future research
must distinguish via patent-assignee chain (CA assignment record →
USPTO file wrapper) rather than by name search alone.

**Path to closure** when subscription / interactive access becomes
available:
1. CA SoS bizfileonline.sos.ca.gov direct interactive query (browser-
   solved Imperva challenge) — yields entity number + filing date +
   current status + agent for service of process.
2. PACER / federal court records — would surface any litigation,
   bankruptcy, dissolution.
3. CrunchBase / PitchBook subscription — yields any institutional-
   investor activity (audit § 3.1 noted "no documented public-facing
   product launch, marketing presence, or commercial activity"; this
   would confirm or correct that observation).

**Priority.** Low. Not a correctness issue; depth-of-record question
for the eventual `/organizations/reveal-systems-inc` node build (audit
§ 6 recommendation). Patent-record evidence is sufficient for the
existing Kirkpatrick-node Credibility Notes framing.

**Scope.** Single registry-lookup pass once interactive access is
available; otherwise indefinite-blocked.

Surfaced: Kirkpatrick audit-iteration follow-up — open-access
registry hunt established CA state of incorporation per patent
record but blocked at SoS / OpenCorporates layer; name-collision
discovery worth recording so future Reveal Systems node-build
sessions don't conflate.

---

### Mellon–Kirkpatrick Signal exchange — Black Vault FOIA appeal pending

The April 18 2024 BlackVault release of FOIA case 24-F-0266 includes
the June 11–13 2023 Signal text-message exchange between Sean
Kirkpatrick and Christopher Mellon. Kirkpatrick's responses
("absurd and false"; "defending and adjudicating, and you're
undermining the very organization you purported to help establish
for this purpose") are visible verbatim in the released screenshots
and are now registered as Statements quotes q36 and q37 on
`/people/sean-kirkpatrick`.

Mellon's full reply on the same exchange is partially redacted in
the released screenshot — the visible portion documents Mellon
responding that he never claimed Grusch's claims were "accurate" but
felt Grusch was "sincere and credible," that he expressly called the
allegations "warrant[ing] investigation," and that he would "seek to
avoid further communication unless it is something that seems
extraordinary or if [Kirkpatrick] initiate[s]." The remaining text
is cut off in the released screenshot and Black Vault has filed a
FOIA appeal under case 24-F-0266 for the redacted portion.

**Status.** Pending external FOIA-appeal resolution. Out of repository
control; cannot be advanced through technical or research action.

**Path to closure** (passive, requires external event):
- Black Vault FOIA appeal resolves and the redacted text is released.
  At that point, Mellon's full reply becomes registerable on the
  Mellon person node (when built — that node is unbuilt per audit § 6
  Sol Foundation / disclosure-ecosystem build queue).
- Until resolution, the documentary record on Kirkpatrick's side is
  complete; the Mellon-side completion is downstream.

**Priority.** Low. Not a correctness issue for Kirkpatrick's node;
adds nuance to the documentary record on the Mellon side. Holds
until either (a) the FOIA appeal resolves, or (b) the Mellon node
is built (audit § 6 disclosure-ecosystem cluster) and the
incomplete-reply note becomes load-bearing for the Mellon Statements
section.

**Scope.** When the appeal resolves: re-fetch the FOIA 24-F-0266
release from Black Vault, re-extract, register Mellon's full reply
as a quote on the Mellon node (when built), and update Credibility
Notes Group B on the Kirkpatrick node accordingly.

Surfaced: Kirkpatrick audit-iteration follow-up — audit § 7 "Mellon
Signal reply text (full)" Open item logged for visibility so a
future session reviewing the Mellon node or the Kirkpatrick
credibility notes knows the appeal is pending.
