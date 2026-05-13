---
id: meta/conventions
type: meta
schema_version: 1
created: 2026-04-17
---

# Conventions

Human-readable rationale for the repository's evidentiary discipline and
structural decisions. The machine-readable specification — required
fields, valid vocabularies, required sections per node type — lives in
`schema.yaml`. This file explains *why* those rules exist.

---

## Core principle

Every claim is anchored to a primary source or explicitly flagged as
unverified. Contradictions are preserved, not reconciled. Testimony under
oath is documented separately from independent verification of the claim.
Primary-source URLs are archived locally so the record survives if the
source site dies.

The repository does not adjudicate between conflicting primary sources.
It documents what each source says and links to both. The reader draws
their own conclusions from the preserved evidence.

---

## Structure reflects evidence type

Evidentiary categories are separated structurally, not hidden in cells.

- A pilot who observed an object is an **eyewitness** — requires
  `Corroboration` (instrumented, testimonial, government statement).
- Someone who filed a formal complaint about claims made by others is a
  **whistleblower** — requires `Claim Inventory` (claim → document →
  status) and `Vouching Chain` (named attestations).
- Someone whose significance is institutional access is an
  **institutional-actor** — requires `Program Involvement` (program,
  role, evidentiary basis).
- A journalist whose significance is published reporting is a
  **reporter** — requires `Publication Record` (outlet, beat, notable
  coverage).

These distinctions are not cosmetic. An eyewitness account rests on direct
sensory observation; a whistleblower's account rests on the credibility of
sources they have not themselves observed; an institutional actor's
significance rests on what they had access to; a reporter's significance
rests on what they published. Structural separation makes the evidentiary
category visible before the reader reads the content.

The same principle applies to organizations (government vs.
government-contractor vs. private), events (proceeding vs. observed
incident), and documents (government vs. non-government).

---

## Statements as the universal evidentiary primitive

The evidentiary content of every node rests on `quotes[]` in the
research artifact — verbatim passages from primary sources. No
contributor-synthesized claim layer sits between source and reader,
on any node type.

The rationale is failure-mode specific: contributor-prose summaries
introduce fine drift (dropped qualifiers, synonym rephrases,
word-level condensations) that mechanical checks catch poorly.
Eliminating the prose claim layer eliminates the drift surface. Other
nodes that cite facts from a source link to the source-bearing node
(document / transcript / media) and reference the specific passage —
no intermediate paraphrase exists to drift.

### Confirmation is a precondition for inclusion

Quotes appear in node bodies only after confirmation against the
underlying primary source. Confirmation is a precondition for
inclusion, not a rendered flag. The rendered output carries no
verification marker — the source link is the evidence; a reader
verifies a quote by following the link to the archived source, not
by reading a checkbox.

The principle is enforced mechanically by the build validator: the
verbatim-quote check fails any commit where a quote's text does not
appear in the extracted source. The enforcement is invisible to the
reader by design. The validator catches silent drift (a quote edited
in an artifact months later that no longer matches the source) and
broken source references; it does not, and cannot, perform trust on
the reader's behalf.

Transcripts of speech sources — congressional hearings, podcasts,
broadcasts, interviews, depositions, conference talks — are
equivalent-footing sources once confirmed against the relevant
primary source. The inclusion bar does not vary by medium: every
quote, whether extracted from a PDF, an HTML page, a stenographic
transcript, or a captioning file, must appear in the cited source.
No marker variant, no different verification path, no renderer
special-casing. What "the cited source" means for a transcript
depends on the transcript's provenance: human-produced transcripts
(stenographic court reporting, outlet-published transcripts with
human editorial review) ARE the primary source; auto-caption files
(YouTube auto-captions, Otter.ai, Whisper output) are machine
extractions of the underlying audio/video, and the underlying media
is the original source. See "Transcript provenance and audit
discipline" below for the per-provenance verification path.

OCR-scanned sources are a known blind spot: when both the quote text
and the source extract carry the same OCR corruption, the
verbatim-quote check passes despite the quote not matching the
original document. The `extraction_type: ocr-scan` field on
manifest entries flags such sources to ingestion-pipeline discipline
(text-layer pull, modern OCR, VLM on page images, or visual
verification against the original) before quotes are derived. The
validator does not close the OCR-corruption gap; the ingestion
pipeline does.

The same `.txt`-sibling preference handles `extraction_type:
extraction-lossy` sources — text-native PDFs whose extracted text
is unreliable for non-OCR reasons (Unicode-mapping artifacts at
PDF-generation time, stenographic-format noise like inline line-
number prefixes and page-footer triplets). A 2026-05-04 evaluation
of the known Unicode-mapping case (`11½` encoded as byte `\x87` →
U+2021 in the embedded font's CMap) confirmed the corruption lives
in the source PDF's content stream itself: `pdftotext`, `mutool`,
and `pypdf` all faithfully reproduce the same bytes because the
PDF tells every compliant reader that the glyph is `‡`. Switching
extraction tools is not a path forward — the contributor-produced
clean transcription, visually verified against the source page, is
the canonical recovery for both ocr-scan and extraction-lossy
sources. Do not re-open this question without new evidence (e.g.,
a substantively different failure mode that doesn't reduce to
"PDF content stream encodes the wrong glyph").

**Detecting a new OCR-scan source.** A PDF whose Producer / Creator
metadata names an OCR engine (OmniPage, AINSLIB.OCR, ABBYY,
Tesseract) or whose text layer was demonstrably reconstructed from
page images needs the `ocr-scan` flag even when its `pdftotext`
output looks clean on a casual read. The signals to check:

- **Visual diff.** Compare `pdftotext` output of any page against
  the rendered PDF page. Clean text-native extractions don't show
  character-level divergences from visible content; OCR sources do.
- **Character-cluster transpositions.** Common OCR misreads cluster
  in predictable pairs — `rt`↔`tr`, `ar`↔`at`, `re`↔`te`, `ll`↔`11`,
  `cl`↔`d`, `rn`↔`m`. Grep for words containing these in positions
  where they don't make English sense (`telated`, `compatrtmented`,
  `appatently`) as a fast first-pass screen.
- **Unicode-mapping artifacts.** Substitution at the PDF-generation
  layer can produce nonsense glyphs (`‡` for `½`, `®` for `©`) that
  the extractor reproduces faithfully. These look correct on text-
  navigation tools but wrong against visible content.
- **Producer-string heuristic.** Run `pdfinfo` on the PDF and check
  the Producer / Creator fields. OmniPage CSDK, AINSLIB.OCR, ABBYY
  FineReader, and Tesseract producers all warrant inspection even
  when the extract looks clean. (One PDF in the BACKLOG A2 audit had
  a clean extract despite OCR producer metadata; that's the
  exception case — flagged `ocr-scan` with a verification note
  instead of producing a `.txt` sibling. Most OCR-produced PDFs need
  the sibling.)

When detection confirms `ocr-scan`, set the manifest entry's
`extraction_type` accordingly. If the extracted text is clean enough
to use, the validator falls back to `pdftotext` (per
`extract_source_text` in `scripts/lib/_common.py`); otherwise produce
a contributor-verified `.txt` sibling. The three-step contributor
discipline below handles the per-quote case during the window before
the sibling exists.

**Producing the `.txt` sibling — four valid paths.** The sibling is
canonical because it has been *visually verified against the source
by an agent independent of the producer*. Production methods are
interchangeable; the independent-verification step is what closes the
trust gap. Pick the path that fits the document's shape.

1. **Text-layer pull.** Some scanned PDFs carry a clean text layer
   despite OCR-suggesting producer metadata (the BACKLOG A2 audit
   surfaced one such case). Run `pdftotext -layout source.pdf`, diff
   the output against the rendered page, and copy to the sibling
   path if clean. Lowest effort; only viable when the layer happens
   to be reliable. The validator's `extract_source_text` already
   prefers the sibling when present, so the workflow is strictly
   one-shot.

2. **Modern OCR.** Tesseract / Google Cloud Vision / Azure Read API
   on rasterized pages. Output requires page-by-page contributor
   review against the source PDF — OCR introduces character-level
   corruption (`rt`↔`tr`, `cl`↔`d`, `rn`↔`m`, `ll`↔`11`) that the
   contributor must correct before the sibling becomes canonical.
   The contributor IS the independent verifier here; reading both
   the OCR output and the source page closes the trust gap. Best for
   batch-processing long documents where per-character review at
   scale is more practical than full retyping.

3. **VLM page-image read.** A multimodal LLM reads the source's
   page images directly and produces transcribed text in one pass
   (e.g., Claude's Read tool with `pages: N-M`, max 20 pages per
   request). Per-character OCR corruptions don't appear because the
   model isn't reading character-glyph features — it's reading the
   image at a higher level of abstraction. Failure mode is different:
   the model may *hallucinate* over ambiguous content (faded ink,
   redactions, marginal handwriting, signature glyphs) where OCR
   would simply garble.

   *Independent verification by a different agent — a human
   contributor or a different model session — is required before the
   sibling becomes canonical.* The producing session cannot self-
   verify hallucinations; the failure mode is invisible to the agent
   that produced it. Practical for short documents (single-digit
   page counts) where chunking overhead is low and human spot-check
   is fast. For documents > 20 pages, track the chunk boundaries
   explicitly (e.g., `pages: 1-20`, `pages: 21-40`) so re-runs land
   on the same page sets.

4. **Manual transcription.** The contributor reads the source page
   directly and types the transcription. Highest fidelity for very
   short documents (1-3 pages, e.g., the SD004 page-1 Q&A). The
   contributor is both producer and verifier; the visual reading
   that produces the text IS the verification. No second-agent step
   needed.

For all four paths, the canonical sibling lands at `<same-stem>.txt`
adjacent to the source. The validator's `extraction_type: ocr-scan`
or `extraction-lossy` flag tells `extract_source_text` to prefer the
sibling over the underlying PDF text layer. The sibling itself is a
manifest entry (with its own sha256 — integrity backstop matching the
parent PDF entry's).

**Per-quote contributor discipline when an OCR-scan source's `.txt`
sibling hasn't been produced yet.** A new OCR-scan source may enter
the corpus before a contributor produces its clean-text sibling — the
validator falls back to `pdftotext` output of the OCR'd PDF in that
case, and OCR character-corruptions (`telated` for `related`,
`compatrtmented` for `compartmented`, `bigalow` for `bigelow`) pass the
verbatim-quote check because both the quote text and the source extract
carry the same corruption. The check is mechanically correct but reader-
misleading — confirmation against the OCR-corrupted extract is not
confirmation against the original document. Two contributor steps,
both required, when authoring a quote from such a source:

1. **Log each artifact as a `naming_quirks` entry** with resolution
   `preserve-as-sic-in-quotes` — observed form, canonical form, source
   path, and a note explaining the variance (`OCR artifact`, `auto-
   caption typo`, etc.). Multiple artifacts from one source produce
   multiple entries (one per observed→canonical mapping).
2. **Preserve the source form verbatim in `quote.text`.** Silent
   substitution of the canonical form would make the verbatim-quote
   check fail AND erase the source-form-as-archived discipline. When
   the canonical form needs to appear in prose elsewhere, wrap a
   backtick-bracket path on the canonical target — e.g., `"lockie
   Martin" [`/organizations/lockheed-martin`]` — the prose-drift check
   strips the bracket wrap before tokenizing, so the source-verbatim
   token matches against source while the canonical wrap provides
   navigability.

Reader-visibility is automatic from there (per BACKLOG B1 M2). The
Phase II body renderer emits a `## Source-Form Notes` section near
the foot of every node body (just before `## Associated Nodes`) that
tables every `naming_quirks` entry whose resolution is
`preserve-as-sic-in-quotes`. Columns: Source Form, Canonical, Source,
Note. The section is auto-suppressed when no such entries exist on
the artifact. A reader encountering a source-form token in quoted
text has a reference table directly on the node body — no separate
prose flag required. Adding a one-sentence prose flag in
`credibility_notes` / `description` remains optional when the
source-form pattern is particularly load-bearing for a specific
evidentiary claim (the Grusch q157 + PPD-19 cases are examples), but
is not the primary reader-visibility mechanism.

After registering the naming_quirks entries, re-grep the source
extract for additional artifact patterns matching those already
logged — drafting the registrations often surfaces artifacts not
caught in the initial scan.

The discipline is a per-quote workaround, not a substitute for
producing the `.txt` sibling. Once the sibling exists and the manifest
entry's `extraction_type` is set to `ocr-scan`, the validator extracts
from the sibling rather than the corrupted PDF text layer; the
naming_quirks entries continue to record the original artifacts as
provenance and continue rendering via the Source-Form Notes section.

### Transcript provenance and audit discipline

Transcripts of speech sources split into two evidentiary classes by
how the audio-to-text transcription happened:

**Human-produced transcripts** (stenographic court reporting like
Alderson Court Reporting; outlet-published transcripts with human
editorial review against audio — NYTimes transcript service, Federal
News Network, broadcast transcripts where the outlet's process
includes audio confirmation). The human has already done the audio-
to-text confirmation. These are equivalent-footing primary sources —
the validator's substring match against the transcript file is
substantively meaningful, no additional audio verification required.
The `transcript_provenance` values `stenographic` and
`published-transcript` mark these classes.

**Auto-caption transcripts** (YouTube auto-captions, Otter.ai,
Whisper output, any other machine-generated caption file with no
human correction step). The caption file IS the machine extraction
of an underlying audio/video signal — structurally the same shape as
the OCR text layer of a scanned PDF. Failure mode: character-level
mis-transcription (`Bigalow` for `Bigelow`, `lockie Martin` for
`Lockheed Martin`, `Kurpatre` for `Kirkpatrick`, `Jim laty` for `Jim
Lacatski`). When both quote text and caption file carry the same
machine artifact, the verbatim-quote check passes trivially — the
textbook auto-caption blind spot. The `transcript_provenance` value
`auto-caption` marks these sources; the underlying audio/video is
the canonical original. Audit handling mirrors `ocr-scan`:

- **Known caption artifacts** registered as `naming_quirks` entries
  with resolution `preserve-as-sic-in-quotes` (same workflow as
  OCR-scan source-form preservation per
  `feedback_prose_drift_warnings_must_resolve.md` Category 3).
  Examples already in the corpus: `Bigalow`→`Bigelow`,
  `lockie Martin`→`Lockheed Martin`, `Jim laty`→`Jim Lacatski`,
  `alzando`→`Elizondo`.

- **Programmatic suspect-pattern scan** on caption files: same
  character-cluster heuristics that detect OCR mis-reads
  (`rt`↔`tr`, `cl`↔`d`, `rn`↔`m`, etc.) plus caption-specific
  patterns (single-syllable proper-noun mis-spellings, phoneme-
  substitution drift on uncommon names).

- **Audio confirmation** for any quote whose programmatic / contextual
  review surfaces an anomaly. For an auto-caption source with a
  documented track record of clean output across spot-checked
  passages, programmatic + naming_quirks discipline is substantively
  meaningful — the exception case parallels the
  ocr-scan-with-clean-extract pattern (validator's caption-file
  substring match suffices; document the verification approach in
  the manifest note).

- **Contributor-produced clean-text sibling** is the analog of the
  ocr-scan `.txt` sibling for auto-caption sources where systemic
  drift is observed. The sibling is a contributor transcription of
  the audio (or a human-corrected version of the caption file)
  with its own manifest entry + sha256; the `transcript_provenance`
  value moves from `auto-caption` to `human-corrected-caption` once
  the correction step is documented.

**Hybrid sources** — auto-caption files contributor-corrected
against audio playback — flag as `human-corrected-caption`. Once
corrected, equivalent-footing with stenographic and published-
transcript classes.

The five-value `transcript_provenance` enum is the schema layer
(see `manifest_entry.transcript_provenance_values` in
`schema.yaml`). The audit discipline above is the contributor layer.

### Type-specialized views of `quotes[]`

Each node type renders a filtered view of the same universal primitive:

- **Person** → `## Statements`, split by `observation_type` (Direct
  Observations / Other Statements) and sorted by `statement_date`.
- **Person (whistleblower)** → additionally `## Claim Inventory`, a
  render-time projection of quotes tagged `category: filed-claim`.
  A filter, not a separate data structure — the filed claim IS the
  quote.
- **Event (hearing)** → `## Key Testimony`, verbatim passages sorted
  by `statement_date`, surfacing evidentiarily-distinctive moments.
- **Document / transcript / media / organization / location** →
  `## Key Passages`, verbatim excerpts of what the source says about
  its subject.

### Hearing events as venues

An event is a venue, not a speaker. F.2a collapsed the prior `What The
Hearing Established` synthesis section into `Witnesses & Testimony`,
a cross-reference table pointing at each witness's transcript and
written-testimony nodes. What a hearing "established" is the verbatim
record those linked nodes carry; the event node navigates to them
rather than paraphrasing.

### Synthesis prose is labeled and drift-checked

Contributor-synthesis prose is limited to labeled synthesis surfaces
(`description`, `background`, `top_relevance`, `credibility_notes`)
and per-entry synthesis-content notes (`ownership_timeline.note`,
`key_personnel.note`, `vouching_chain.attestation`, etc.).
the prose-drift check tokenizes each of these against the
primary-source text and warns on every unmatched significant token
(errors at 100% vocabulary divergence).

### News articles and books

Stored as `document` nodes (kind `non-gov-doc`, doc_form `article` or
`book`). Credibility analysis of the author/publisher lives on the
author's person node or the publisher's organization node, not on the
document.

### Prose-drift discipline on synthesis surfaces

Nodes carry contributor-prose surfaces that sit alongside the verbatim
`quotes[]` content: per-node `description` / `background` /
`top_relevance` / `credibility_notes` paragraphs, and per-entry
synthesis content notes (`ownership_timeline.note`,
`top_scope_activity.note`, `key_personnel.note`, `contracts.note`,
`media_versioning.note`, `vouching_chain.attestation`). These are
labeled synthesis — they exist to frame the evidentiary content — but
the F.1c Fravor audit (2026-04-19) surfaced a real failure mode where
contributor prose introduces unstated premises, paraphrase drift, and
content widening even when every referenced quote is verbatim-clean.

`validate-research.py`'s prose-drift check verifies
that significant words in these prose fields appear in the referenced
primary-source text. The check is an impartial reporter — it flags
every unmatched token as a warning without classifying whether the
drift is "legitimate synthesis" or "real drift". The contributor
reviews each warning and asks: *does this unmatched token introduce
a fact or premise the source doesn't attest?* Errors fire only at
100% vocabulary divergence (complete mismatch — prose shares no
significant words with the source it claims to draw on), a
mathematical floor on pure fabrication rather than a stylistic
threshold. Below 100%, the validator makes no judgment; careful
contributor review is the quality gate.

The prose-drift check is explicitly scoped to synthesis prose (free-
prose fields and synthesis-content notes). Compact label cells (role
titles, short relationship descriptors, `timeline[].event`) and cross-
reference descriptor notes (`corroboration_items.note`,
`witnesses_testimony.note`, `org_relationships.note`,
`location_relationships.note`) are out of scope — token-match misfires
on those surfaces; fabrication there is Phase III semantic-review
territory.

### Free-prose density is source-driven

Templates and prompts do not impose paragraph or sentence count targets
on free-prose fields (`description`, `background`, `top_relevance`,
`credibility_notes`, synthesis-content `.note` fields). Contributors
populate each field with what archived primary sources support — no
more, no less.

Count targets ("1-2 paragraphs", "one paragraph", "2-4 sentences",
"~50 words per paragraph") create pressure that splits two ways under
real source variance: filler entries when the source doesn't support
the count, or hallucinated content when the model fills the gap from
training knowledge. The `pilot-failure-2026-04-17.md` postmortem
documents the failure mode this discipline exists to prevent. The
durable contributor memory `feedback_no_count_targets.md` codified
the rule for entry-list population; this section extends the same
rule to free-prose density.

Structural thresholds are different and remain in force. The finding-
node creation threshold (~200 words, 3+ entity nodes, or text about
to be written into 3+ different nodes per `meta/schema.yaml::types
.finding.creation_threshold`) governs WHEN analysis should move to a
different node, not HOW LONG a field's prose should be. Cross-
reference brevity — entity nodes citing a finding carry a brief
summary plus link back, with the canonical narrative living on the
finding node — is structural rather than length-prescribed.

Templates describe the WHAT of each field (subject, scope, what to
capture); they do not prescribe the HOW LONG. New templates and new
prompt sections follow the same rule.

### Date precision: orientation-grade in prose, field-precise in tables

Description prose carries orientation-grade dates anchored to semantic
events ("announced", "issued", "filed", "took office", "established").
Field-precise contract / period dates live in their structured surface
(Primary Contracts, Timeline, Key Personnel, Ownership Timeline) where
they are source-attested per row. Description should not duplicate
field-precise dates from a structured surface; if a date is in the
table, the description can refer to the event without re-stating the
field.

The two layers serve different roles. Description orients the reader
to the document or entity at narrative grade; the structured table is
the authoritative surface for field-level data. Eliminating duplication
removes a drift surface between the two and lets the layered-precision
principle work — three layers, three roles: description for landscape,
structured table for field-precise data, Key Passages for verbatim
source.

**Inverse case — multi-year contract `period_end`.** The "table is
authoritative" rule only works when the table actually carries the
field. Multi-year contract rows with explicit ordering-period end
dates in the source — typical of BPA, IDV, GSA-FSS, and other
indefinite-delivery vehicles — populate `period_end` from
`period_of_performance.end_date` when the source attests it, even
when the prose layer doesn't explicitly call out the end. Otherwise
the description's reference to the contract's establishment has no
structured-surface counterpart for the contract's closure, and the
layered-precision principle breaks for that class of contracts.

### Quote location refs: source-anchored, not extraction-anchored

Each quote in a research artifact carries a `source.location` field —
the navigation handle from the quote to its precise place in the cited
source. The handle is useful only if it remains correct across
re-extractions of the source and tight enough that following it lands
on the quote, not on the adjoining material.

`lines N-M` refs (where N and M are line numbers in a particular
pdftotext output of the source) violate both constraints. Line
numbers are properties of one extraction, not properties of the
source document — when the source is re-extracted (clean-text sibling
production for `ocr-scan` / `extraction-lossy` PDFs, tool change,
format conversion), the line numbers shift and the ref silently
misnavigates. The verbatim-quote check still passes because the
quote's bytes still appear *somewhere* in the source, but the
location ref no longer points at where they appear.

The canonical form anchors to properties of the source document
itself:

| Source shape | Canonical location form |
|---|---|
| Paginated PDF (hearing transcript, government report, written testimony) | `p. N, ¶M` |
| Unpaginated short document (HTML article, single-page memo) | `¶N` |
| Caption / audio / video transcript | `[MM:SS]` (or `[MM:SS]–[MM:SS]` for long quotes) |
| Multi-page document where paragraph anchors aren't available — either the document lacks paragraph structure, or `pdftotext -layout` collapses visually-distinct paragraphs on a page into a single block (in which case ¶1 would overstate the precision the extract can deliver) | `p. N` |
| FOIA email release with a contributor-produced `.txt` sibling carrying `DOCUMENT N — header` markers (e.g., `blackvault-foia-24-f-0894-aaro-vol-1-rollout-emails.txt`). Each `DOCUMENT` block is a discrete email or threaded exchange — analogous to a page but heavier, and stable across re-extractions because the markers live in the contributor-produced sibling rather than the underlying PDF text layer. | `Doc N` for single-email documents; `Doc N, Sender YYYY-MM-DD HH:MM` for multi-email threaded exchanges. The cover letter (if quoted) uses `Cover letter, ¶M`. Email metadata that doesn't fit the location anchor (recipient, subject, importance flags) moves to `context` / `significance` where it renders as reader-visible attribution. |
| The extract itself IS the intended reference (rare; e.g., extract carries content the source PDF lacks) | `lines N-M of the extract` (the `of the extract` qualifier is required) |

Plain `lines N-M` is not a valid permanent ref. Three layers serve
distinct roles: `source.path` names the archived file (the ground
truth); `source.location` navigates within that file using anchors
the file itself provides; line numbers in any one extraction are a
fourth, transient layer that depends on which extractor ran and when
— useful for debugging, never the right anchor for a permanent ref.

A location ref also has a tightness constraint: the range covers
the quote's bounds, no more, no less. Including adjoining material
(an interrupting speaker turn following the quote, a page footer
ending the page) makes the ref land on a region that mixes quote
with not-quote and defeats the navigation purpose. When converting
`lines N-M` to a canonical form, the contributor verifies the new
ref's range against the source page itself, not just against the
extract.

### Check naming

Validator checks are referenced across the codebase by **topic name**,
not by number. `the verbatim-quote check`, `the prose-drift check`,
`the chronological-ordering check`, etc. Names are stable across check
additions and retirements; numbered lists in module docstrings (if any)
exist only as at-a-glance summaries and are not referenced externally.

Rationale: positional numeric identifiers (`check #11`, `check #16`)
couple every external reference to ordering. Retiring a check then
forces either (a) a numbering gap with a placeholder, or (b) a mass
rename across ~60 cross-refs. Topic names decouple references from
position — retiring a check deletes the function and its refs; no
placeholder needed, no renumber required.

Discipline for check additions: give the new check a semantic topic
name (`cross-entity-consistency check`, `finding-rollup check`,
whatever fits) and use that name in any cross-doc reference. For
check retirements: delete the function + all topic-named refs
together; git log preserves the history.

Topic names are stable interfaces — renames ripple the same way any
API rename does (mass find-replace across refs). Pick names that
describe what the check verifies, not how it's implemented.

---

## Confirmed vs Flagged

Any structured section that mixes primary-source-supported entries with
secondary-source-only or unverified entries splits into `### Confirmed`
and `### Flagged` subsections.

- **Confirmed** — established from a primary source linked in the row
- **Flagged** — cited in secondary sources only; requires primary-source
  confirmation before treating as established

Empty Flagged subsections are omitted, not filled with placeholder text.
Presence of `### Flagged` with no rows is a schema violation; absence
indicates no flagged items.

The distinction records source quality, not truth. A Flagged item may
well be true; it hasn't been verified against a primary source yet.

---

## Sworn testimony vs claim verification

Testimony given under oath is a confirmed fact regardless of whether
the underlying claim is independently verified. These are two distinct
facts and must not be merged into a single statement.

**Correct**: "✅ Confirmed as sworn testimony — claim not independently verified"
**Incorrect**: "Claimed that..." (implies testimony is unconfirmed)
**Incorrect**: "Testified that X is true" (conflates testimony with verification)

When an authoritative body later denies a sworn claim, the denial is
logged as a separate dated entry. The sworn testimony row stays confirmed.
Both facts coexist because both are true.

Q&A testimony under oath carries the same evidentiary weight as prepared
written testimony. Oral and written versions of a witness's testimony are
preserved as independent primary records — the hearing transcript node
holds the oral record; the written testimony document node holds the
written record. Cross-entity comparison between the two (where a claim
appears and how the placements differ) is a synthesis finding and
belongs on a finding node, not on either primary record.

---

## Contradictions

Two markers distinguish evidentiary disagreement by the quality of
evidence on each side:

- **`⚠ Disputed — unknown`** — both parties assert opposing claims;
  neither has primary-source evidence beyond their own authority to
  speak. Document what each side says; link to both sources. The
  repository does not adjudicate.
- **`❌ Contradiction`** — positions directly contradict **and at
  least one side is backed by primary-source evidence**. Two shapes:
  (a) both sides have primary-source evidence that conflicts (e.g.,
  AARO HRR Vol I finding vs. a FOIA-released DIRD document);
  (b) one side has primary-source evidence, the other rests on
  self-attestation or on-record claim alone (e.g., DoD PA official
  denial vs. individual's self-reported role). In either shape, each
  source remains confirmed from its own origin; the primary-source
  asymmetry (if any) is noted in the row; the disagreement itself is
  the analytical finding.

When an authoritative source formally contradicts a confirmed claim, the
contradiction is documented on the **synthesis node where the
disagreement gains analytical meaning** — not on the source document
nodes themselves. Document nodes record each source's statement
verbatim in Key Passages; cross-document contradictions are a synthesis
finding, not a property of either document.

| Situation | Where |
|---|---|
| Post-event denial | `Node Versioning` on the relevant person / event / organization node |
| Institutional self-contradiction | `Credibility Notes` on the person / organization node |
| One document's statement contradicts another's | `Institutional Assessment` on the relevant organization node (when an agency finding contradicts a cited claim), or a finding node spanning the conflicting sources |
| Written vs. oral testimony divergence | Finding node spanning the two primary records (transcript + companion written testimony document) |
| Contested affiliation | `Flagged` subsection of `Affiliations` |

The Confirmed/Flagged binary is unchanged by contradictions —
"contradicted" is not a third status. Both sources remain confirmed
from their respective origins; the evidentiary disagreement is
documented separately.

---

## Finding nodes

Some patterns span multiple entities. When an analytical narrative about
a cross-entity pattern would otherwise be duplicated across 3+ entity
nodes, create a single `/findings/{slug}` node.

**Creation threshold:**
- Pattern spans 3+ entity nodes, OR
- Analytical narrative would exceed ~200 words in any single entity
  node's cell, OR
- The same text is about to be written into 3+ different nodes.

Below these thresholds, keep the analysis in the single most relevant
entity node. Don't create a finding for every pairwise cross-reference.

Entity nodes cited by a finding carry a brief summary + link back to
the finding, not the full narrative. The finding node is
the single canonical home for that pattern.

Findings are not verdicts. They document cross-entity patterns observed
in primary sources and flag the analytical questions each pattern
raises — without adjudicating intent or assigning responsibility.

---

## Neutrality

The repository documents observed facts from primary sources and does
not adjudicate intent, motivation, or compliance with norms external to
the documentary record. Analytical sections (Institutional Assessment,
Credibility Notes, findings) frame observations in neutral terms.

This principle is repository-wide. Individual nodes and sections do not
need to recite neutrality language per cell — the principle stated here
governs the entire repository.

---

## Versioning

Nodes are never closed and source data is never overwritten.

- **New source adds information** → add a new row with date and source
- **New source contradicts existing claim** → keep original with its
  source; add new claim in a separate row; link the two via
  `Superseded By` (formal correction) or `Contradicted By` (active
  disagreement)
- **Claim formally corrected** → `Superseded By` on the original — do
  not delete the original

Git log is the edit-history record. In-document changelogs are not
maintained — `git log --follow` on the node file is authoritative.

---

## Associated Nodes

Every node carries an `## Associated Nodes` section — a navigational
index of all cross-references grouped by target type (Events,
Documents, Transcripts, News, Organizations, People, Findings).

This section is auto-generated by `scripts/associate.py` from
`[`/path`]` link references in the node body. Do not hand-edit.

---

## Primary sources and archival

Every external URL cited in any node is archived locally in
`/sources/{category}/{filename}` and registered in
`/sources/manifest.yaml`. The local archive is the integrity guarantee;
the Internet Archive Wayback Machine submission (via
`scripts/archive.py`) is insurance.

Citations in prose are direct markdown links to the archived file or
the manifest entry, not prose references to manifest row numbers.

When a source is blocked or paywalled, the manifest entry records the
block status and the archival route (if any) is documented on the
entry. See `sources-access.md` for site-specific workarounds.

---

## Scope

The repository is a general-purpose primary-source investigation
toolkit. Its first instance documents UAP-related public-record
material, but the schema and structure are topic-neutral. Any
investigation grounded in primary sources — historical event, legal
case, policy decision, scientific controversy — can use the same
structure.

---

## Repository layout — content flat, tooling organized

Three tiers, each with a different organizing principle:

**Investigator-facing content** (flat by design):
`/people/`, `/organizations/`, `/documents/`, `/events/`, `/transcripts/`,
`/media/`, `/locations/`, `/findings/` each hold single-level `slug.md`
files. `/sources/` is flat within each category subdirectory. A
researcher looking for `/people/david-grusch.md` finds it one click in
— no `/people/whistleblowers/intelligence-community/david-grusch.md`
nesting. The frontmatter (archetype, kind, status) carries the
categorization that hierarchy would otherwise impose.

**Backend tooling** (`/scripts/`) is organized for engineering hygiene,
not researcher browsing. `/scripts/lib/` holds genuinely shared
cross-cutting helpers.

**Governance and structured-data backing** (`/meta/`) is organized
by role: `/meta/templates/`, `/meta/topic/`, `/meta/toolkit-notes/`,
`/meta/research/`. Research artifacts live under `/meta/research/`
because they are the contributor-edited Phase I working surface and
the agent-readable structured fact layer (per `AGENT.md`) — not
investigator-read narrative. Putting them with templates (mechanical
scaffolding) and schema (the spec they conform to) reflects what they
actually are: structured data backing the rendered nodes, not content
in their own right.

The flatness rule is about content the investigator reads, not about
files the toolkit maintainers and pipeline scripts edit. Don't
extrapolate the content-layer rule onto the tooling or governance
layer — and don't extrapolate organized-by-role onto the content
layer.

### Inside `/scripts/` — contributor-facing root vs gate-only `tests/`

`/scripts/` follows a three-tier sub-rule organized by caller, not by
content type. New scripts land at the tier that matches who invokes
them:

- **`/scripts/` root**: contributor-facing tools that contributors run
  directly during a build session. Includes the build pipeline
  (`new.py`, `extract-source.py`, `research-scaffold.py`,
  `build-from-research.py`, `associate.py`, `manifest.py`,
  `archive.py`, `transcribe.py`), validators that contributors run
  after edits (`validate.py`, `validate-research.py`,
  `review-coverage.py`), refresh utilities (`build-state.py`), and
  diagnostics (`check-vocab.py`, `normalize-locations.py`). A
  contributor's `ls scripts/` shows everything they might invoke.
- **`/scripts/checks/`**: per-check modules — every named validator
  check (verbatim-quote, prose-drift, chronological-ordering,
  manifest-checksums, iff-section, etc.) lives at
  `scripts/checks/{check_name}.py`. The three validators at the root
  are thin orchestrators that import + dispatch these via explicit
  step lists. Contributors don't usually invoke check modules
  directly (the orchestrators do), but each check is individually
  importable for unit-testing or single-check debugging. Shared
  scaffolding (`_research_utils.py` for entry-list checks) lives
  alongside as a private module.
- **`/scripts/tests/`**: gate-internal infrastructure that exists ONLY
  to support the pre-commit chain — the orchestrator (`pre-commit.sh`)
  plus its internal regression tests (`help-check.sh`, `smoke.sh`,
  `test_stopwords.py`). No contributor invokes these directly; the
  directory is the gate chain's private toolkit.
- **`/scripts/lib/`**: shared cross-cutting helpers (`_common.py`)
  imported by multiple scripts in both tiers above and by the per-
  check modules in `scripts/checks/`. Kept separate so the cross-
  script lockstep guarantee — the verbatim-quote check, prose-drift
  check, and description-drift check all extracting source bytes
  through the same `extract_source_text` and tokenizing through the
  same `STOPWORDS` set — is mechanical rather than comment-discipline-
  based. Also carries the markdown helpers (`parse_frontmatter`,
  `extract_h2_sections`, `extract_section`) and the
  `schema_version_compat_messages` helper that consolidates the
  schema-version compatibility check across content nodes, research
  artifacts, and governance-doc / template frontmatter.

The split is by caller, not by whether the pre-commit chain runs the
script. Most root-tier validators ARE gate-invoked — contributors
also run them frequently after edits. Diagnostics like
`check-vocab.py` and `normalize-locations.py` are NEVER gate-invoked
(they exit 0 on informational findings by design and so can't be
gates) but still live at root because contributors invoke them. New
scripts follow the rule: contributor invocation → root; gate-only
support code → `tests/`; shared helper code → `lib/`.

### Inside `/meta/` — root vs subdirs

`/meta/` itself follows a sub-rule that grew implicitly and is
codified here. New governance items land at the tier that matches
their character:

- **Root** (`meta/conventions.md`, `meta/schema.yaml`,
  `meta/sources-access.md`, `meta/BACKLOG.md`, `meta/roadmap.md`):
  stable governance specs and forward-looking work registers — the
  rules and the active agenda. A contributor consults these at
  session start or when something on the work queue applies.
- **`meta/toolkit-notes/`**: retrospectives, postmortems, technique
  docs, design records. Backward-looking lessons explaining *why* a
  current rule exists or *what was tried before*. A contributor
  consults these when understanding the history behind a current
  convention.
- **`meta/templates/`**: scaffolding templates, one per node type.
  Consumed mechanically by `scripts/new.py`; rarely read directly
  by contributors except when a new node type is being added.
- **`meta/topic/`**: topic-specific governance — the priority
  research queue, topic overview, corpus-specific addenda, in-
  progress contributor working notes.
- **`meta/research/`**: YAML research artifacts backing each content
  node — the structured fact layer. One artifact per content node
  (`meta/research/{slug}.yaml`); `target_node` declares the pointer
  to `/{type}/{slug}.md`. Edited by contributors during Phase I,
  consumed mechanically by `scripts/build-from-research.py` (Phase
  II) and validated by `scripts/validate-research.py`. Topic-
  specific in content but governance-neutral in shape — the schema
  governs the shape; the topic determines the entries.

The fork-boundary distinction is load-bearing: a contributor forking
the toolkit to a different investigation deletes `/meta/topic/`,
`/meta/research/`, and the content directories; everything else
under `/meta/` survives because everything else is topic-neutral
toolkit. Items therefore land at the right tier on first author —
topic-specific items in `/meta/topic/` (governance) or
`/meta/research/` (structured facts), toolkit-neutral items at
`meta/`-direct or in `meta/toolkit-notes/` per the rules-vs-lessons
distinction above.

`meta/README.md` is a friendly-face index of the directory's
contents; this section is the rule of record.
