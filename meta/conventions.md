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
  when the extract looks clean. (One PDF in the Phase F corpus audit had
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
   despite OCR-suggesting producer metadata (the Phase F corpus
   audit surfaced one such case). Run `pdftotext -layout source.pdf`, diff
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

**Silent-sibling lookup.** `extract_source_text` finds a `.txt`
sibling by *path stem*, not by manifest registration. A
`<same-stem>.txt` file adjacent to the source PDF gets used by the
validator's verbatim-quote check whenever the parent PDF's manifest
entry has `extraction_type: ocr-scan` or `extraction-lossy`,
regardless of whether the sibling itself has a manifest entry. The
discipline: file and manifest entry are created together. A
sibling-on-disk-but-not-in-manifest is a silent dependency —
quote-verification depends on a file pre-commit has no sha256
integrity guarantee for, and deleting the file (e.g., as "orphan
cleanup") silently breaks the build by reverting extract output to
the PDF's unusable text layer. Register the sibling at the moment of
creation, and treat the manifest-paths verifier (`scripts/tools/manifest.py
verify-paths`) plus pre-commit as the only safe orphan-cleanup gate
for sibling files.

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

Reader-visibility is automatic from there — the Phase II body
renderer emits a `## Source-Form Notes` section near
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

**Caption-tick timestamps in `quotes[].text`.** YouTube-caption source
files (produced by `scripts/tools/transcribe.py`) carry a `[MM:SS]`
marker on every caption line — one tick per 2–5 seconds of speech.
The validator's `normalize_for_compare` (in `lib/_common.py`) strips
`[MM:SS]` and `[H:MM:SS]` markers from BOTH the quote text and the
extracted source before substring comparison, so the verification
check is timestamp-blind. The contributor convention:

- Write each quote as one continuous single-line prose string in
  YAML (single-quoted scalar style; never `|` literal block which
  preserves caption-line breaks as rendered newlines).
- Include AT MOST ONE leading `[MM:SS]` anchor at the start of each
  quote, matching the source line where the quote's first content
  word appears. Reader clicking the anchor lands on the start of the
  quote, not several seconds in.
- Drop all intermediate timestamps from quote text. They normalize
  away at comparison time, so preserving them adds visual noise (a
  15-second quote could carry 9–15 intermediate ticks) without
  evidentiary value.
- Auto-caption typos stay verbatim — handle via `naming_quirks` per
  the per-quote contributor discipline above; don't silently correct.

The source file in `sources/transcripts/` keeps every caption tick
(that's its primary-source form). Stripping happens at the artifact
authoring layer for readability, and at the normalization layer for
verification.

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
  its subject — sorted by `statement_date` (see "Key Passages
  ordering" below).

### Transcript quotes carry structural speaker attribution

On a transcript artifact, the speaker of each quote is a structural
reference, not contributor prose. Every entry in `quotes[]` carries
`speaker_id` (required on transcript artifacts; enforced by
`scripts/checks/quotes.py`), pointing at one of the artifact's
`speakers[*].id` values. The renderer's attribution block emits a
`Speaker` row above `Attributed to`, populated from the matched
speakers entry — `Name ([`/people/slug`])` when the speaker has a
`node_link`, or just `Name` when not (anonymized audience members,
unidentified panelists).

The bright line: `context` carries circumstance prose (venue, format,
neighboring exchange — "opening statement", "Q&A exchange with Rep.
Burchett", "Lacatski continuing his prepared statement"); `speaker_id`
carries who-said-it. Two contributors authoring quotes from the same
source can disagree on circumstance phrasing without diverging on the
attribution — the structural reference is what validates and renders.

Three failure modes the structural reference closes:

- **Prose-attribution drift.** Different sessions could disagree on
  who said line 2:00 of a podcast and both be wrong with no mechanical
  check. The `quotes` check now fails when `speaker_id` doesn't
  resolve to a real `speakers[].id`.
- **Re-author ambiguity.** Six months later a contributor re-reading
  the artifact had to re-trace the diarize + frame + baseline merge
  to recover the speaker assignment. The structural reference makes
  the assignment self-documenting.
- **Renderer inconsistency.** Hand-formatted Attributed-to strings
  varied in how they named speakers ("Lacatski" vs "Dr. James
  Lacatski" vs "Dr. Lacatski"). Mechanical lookup from `speakers[]`
  produces one consistent rendered form per identity.

The accompanying `speaker_baseline_consistency` check
(`scripts/checks/speaker_baseline_consistency.py`) catches the next
link of the chain: every `speakers[].node_link` that points at
`/people/{slug}` should have a baseline at
`sources/photo-identity-log/baselines/{slug}/` so video-pipeline
tools (`scripts/tools/detect-faces.py`,
`scripts/tools/stitch-transcript.py`) can mechanically resolve the
speaker on future videos.

### Statements speaker-attribution — quotes BY the person, not ABOUT

A person artifact's `quotes[]` section carries verbatim statements *by*
the subject — the speaker is the node's subject. Quotes by other
parties about the subject do not belong in Statements; they belong on
the speaker's own artifact and on the subject's structured cross-
reference surfaces (`affiliations[].note`, `relationships[].note`,
`program_involvement[].note`, `timeline[]` rows) with the speaker's
source cited.

The bright lines:

- **First-person utterance.** "I saw a Tic Tac"; "I was the cofounder
  of …"; a press-release quote attributed to the subject. Belongs in
  Statements.
- **Co-authored academic publications.** The subject is named in the
  author byline and the passage is collectively-authored prose.
  Belongs in Statements when the substantive content is the subject's
  own research, position, or institutional claim (1974 Targ + Puthoff
  Nature abstract reporting SRI experimental results: yes). May be
  skipped when the byline is the only subject-relevant fact and the
  passage's substance is technical content unrelated to the subject
  as a person (1991 Targ et al. lidar abstract about windshear
  detection: byline establishes affiliation, but the prose isn't
  meaningful as a Targ statement). Either way, the publication itself
  remains the primary-source attestation of the affiliation — captured
  via the corresponding `affiliations[]` / `timeline[]` row pointing
  at the paper.
- **Self-attestation on the subject's own publication** (personal
  website, signed bio, authored book). Belongs in Statements even when
  written in third person — the subject is the publisher.
- **Quotes by others about the subject.** A reporter narrating, a
  voucher attesting, a supervisor describing the subject. *Not*
  Statements. Capture via `relationships[].note`, `program_involvement[].note`,
  `affiliations[].note`, or `timeline[]` on the subject's artifact,
  citing the third party's source. If the speaker has their own
  artifact, the same quote belongs in that speaker's `quotes[]`.

Borderline calls — corporate filings the subject signed, interview
transcripts where the host asks leading questions, ghostwritten op-eds
under the subject's byline — should be resolved by asking *whose voice
the source records*. When the voice is the subject's (even with
others' assistance), it's a Statement. When the voice is the
attesting third party (even when about the subject), it's a cross-
reference.

### Key Passages ordering

Chronological-by-`statement_date` is the corpus default for every
quote-bearing section that surfaces source content as a list:
person `## Statements`, hearing `## Key Testimony`, and the
universal `## Key Passages` on documents / transcripts / media /
organizations / locations. The renderer sorts ascending by
`statement_date` when populated; entries without `statement_date`
fall through to artifact-entry order (the order they appear in the
research artifact's `quotes[]` list).

**Population convention.** `statement_date` should be populated
whenever the source attests a date. Per-type guidance:

- **People / organizations / events / transcripts**: virtually every
  quote has an attested date (the speaker's testimony, the
  organization's press release, the hearing date, the broadcast
  date). Populate; partial population produces mixed ordering that
  surprises readers.
- **Documents**: most documents have publication or signing dates;
  populate when attested. Quotes from undated material (e.g., a
  reference document with no edition date in source) legitimately
  omit `statement_date`.
- **Locations**: source quotes about a location may have no semantic
  date anchor (geological description, ownership-history narrative
  spanning years, etc.); artifact-entry order is the acceptable
  default when no date is meaningful.

When a contributor faces partial population on an artifact — some
quotes with dates, some without — choose one: either populate every
attestable quote and accept artifact-entry order for the legitimately
date-less ones (renders the dated ones chronologically with the
undated trailing in artifact-entry order), or leave the field blank
on all quotes to render the whole section in artifact-entry order.
Mixed population is the failure mode the convention exists to
prevent.

**In-header epistemic-hedge pattern.** Chronological ordering can
promote a low-evidentiary-weight quote to position 1 simply because
it's earliest. When a quote's evidentiary weight is meaningfully
below the median for its artifact — claim-of-record, self-attested,
secondary-source, contested — the `significance` H3 header carries
an explicit hedge phrase so readers see the epistemic framing before
they read the quote text. Examples:

- "DeLonge email to Podesta — claim-of-record regarding McCasland,
  Roswell material, and Wright-Patterson AFB (claim made by DeLonge;
  not independently verified)"
- "Self-attested capacity, contested by AARO record"
- "Claim-of-record — secondary-source attestation only"

The hedge appears in the H3 header where readers see it BEFORE
reading the blockquote. The TTSA artifact's q5 DeLonge-Podesta email
is the surfacing case: chronological promotion to position 1 (over
later SEC filings) risked the ordering being read as an epistemic
endorsement; the hedge phrase keeps the order chronological but
inoculates against that reading. No schema change; contributor
discipline at the `significance` field.

### Hearing events as venues

An event is a venue, not a speaker. The prior `What The Hearing
Established` synthesis section is collapsed into `Witnesses & Testimony`,
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
contributor prose introduces a real failure mode: unstated premises,
paraphrase drift, and content widening even when every referenced
quote is verbatim-clean.

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

The contributor review also asks a second question: *does the prose
read as natural English?* Iterating against `check-vocab.py` until
every significant token passes can produce stilted constructions —
a source-attested participle stretched to substitute for an absent
finite verb (`is containing` instead of `contains`), source-attested
compound nouns where a single synthesis word would read better.
Source-vocabulary discipline applies token-by-token; English-grammar
discipline applies to the rendered prose. When the two collide,
restructure the sentence — don't ship the broken phrasing.

The prose-drift check is explicitly scoped to synthesis prose (free-
prose fields and synthesis-content notes). Compact label cells (role
titles, short relationship descriptors, `timeline[].event`) and cross-
reference descriptor notes (`corroboration_items.note`,
`witnesses_testimony.note`, `org_relationships.note`,
`location_relationships.note`) are out of scope — token-match misfires
on those surfaces; fabrication there is Phase III semantic-review
territory.

**Zero warnings on scoped fields is the target.** Acknowledging a
warning as "legitimate synthesis vocabulary" and leaving it in place
defeats the check — converts an evidentiary precision tool into a
stylistic nag. Every warning drives to one of two outcomes:

- The prose is rewritten to use source vocabulary exactly, OR
- The source-vs-prose variance is captured as structured evidentiary
  data (a `naming_quirks` entry, a `rumors[]` entry, a `timeline[]`
  row, a `quotes[]` entry — pick the surface that carries the
  variance's evidentiary meaning).

**Resolution paths for common warning shapes:**

1. **Word-form variant** (`preparing` vs source `prepare`,
   `staying` vs source `stay`, `flying` vs source `flown`):
   rewrite prose to use the source morphology. "Was flown by" is
   not awkward — it's what the source says.

2. **Paraphrase or synonym substitution** (source `Statement` →
   prose `written testimony`; source `took` → prose `captured`):
   rewrite to use source vocabulary. Repo filenames like
   `written-testimony-*.md` are repo-internal conventions; they
   don't license substituting those conventions into content
   prose. The wrapped link path renders canonically regardless of
   the surrounding prose token.

3. **Source-form vs canonical-form naming variance** (source `Lue`
   vs canonical `Luis`; source `Keane` vs canonical `Kean`;
   source `Bigalow` vs canonical `Bigelow`): wrap the source form
   in the canonical link path — e.g., `Lue Elizondo
   ([`/people/luis-elizondo`])`. The prose-drift check strips the
   wrap before tokenizing, so the source token matches against
   source while the canonical wrap provides navigability. Log the
   variance in `naming_quirks` with a resolution that captures its
   evidentiary meaning (alias-of-record, OCR artifact, auto-caption
   typo, formal-vs-informal). For recurring source variants (2+
   instances), the frequency makes it alias-of-record rather than
   typo; the note should say so. See "Per-quote contributor
   discipline" above for the full OCR / auto-caption workflow.

4. **Hyphenated compound vs two-word form** (`mental-health` vs
   `mental health`, `intelligence-committee` vs `intelligence
   committee`): rewrite to match source token form. The tokenizer
   treats `mental-health` as one compound token; `mental health`
   as two. Source attestations almost always use two-word form;
   hyphenation is synthesis drift.

5. **Date tokens** (`2023-07-26` vs `July 26, 2023`): use the
   form that appears in source. Testimony transcripts spell out
   `July 26, 2023`; hyphenated ISO dates are contributor
   vocabulary unless source uses that form (some FOIA letter
   headers do).

6. **Genuinely-necessary contributor vocabulary** — if a word
   truly isn't in source and has no source synonym, either (a)
   the sentence is making an inference the source doesn't
   directly attest, in which case the inference drops or moves to
   a structured evidentiary field with its own source attribution;
   or (b) the word is a category-label (enum value, Category
   column entry, structural descriptor) that shouldn't appear in
   free prose anyway.

A warning remaining on a clean artifact after this review is a
deliberate, documented decision — recorded in the relevant
`naming_quirks` note, `rumors` entry, or the commit message — not
an unwritten "contributor reviewed and accepted" assumption.

### Density is source-driven

Templates and prompts do not impose count targets on artifact content.
This applies uniformly to two surfaces:

- **Entry lists.** `quotes`, `entities_referenced`, `naming_quirks`,
  `rumors`, `affiliations`, `relationships`, `corroboration_items`,
  `program_involvement`, `publication_record`, `vouching_chain`,
  `participants`, `witnesses_testimony`, `timeline`, `key_personnel`,
  `org_relationships`, `contracts`, `media_versioning`, and any
  other entry-list section the schema defines.
- **Free-prose fields.** `description`, `background`, `top_relevance`,
  `credibility_notes`, and synthesis-content `.note` fields.

Contributors populate each surface with what archived primary sources
support — no more, no less. The source produces the count. If a
section ends up with one entry, that's correct. If it ends up with
fifty, that's correct. Validators don't check counts; they check
each entry's traceability to source.

Count targets ("aim for ~10 quotes", "1-2 paragraphs",
"approximately 6-10 substantive entries", "2-4 sentences",
"~50 words per paragraph") create pressure that splits two ways under
real source variance: filler entries when the source doesn't support
the count, or hallucinated content when the model fills the gap from
training knowledge. The contributor surface that introduces a count
target is the surface where these failure modes originate — the rule
applies prospectively to template authoring, prompt drafting, and
scope-at-session-start.

Comparison framings also count as targets and should be avoided:
"this section seems sparse", "comparable nodes have N entries; this
one has fewer — anything to add?". Only flag specific entries that
look unsupported by source; never flag aggregate counts.

Structural thresholds are different and remain in force. The finding-
node creation threshold (~200 words, 3+ entity nodes, or text about
to be written into 3+ different nodes per `meta/schema.yaml::types
.finding.creation_threshold`) governs WHEN analysis should move to a
different node, not HOW LONG a field's prose should be. Cross-
reference brevity — entity nodes citing a finding carry a brief
summary plus link back, with the canonical narrative living on the
finding node — is structural rather than length-prescribed.

Templates describe the WHAT of each field (subject, scope, what to
capture); they do not prescribe the HOW LONG or HOW MANY. New
templates and new prompt sections follow the same rule.

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

### Validator design — impartial reporting

Validator checks surface drift signals impartially. They do not bake
in category-tuned thresholds that encode editorial judgment about
which fields are "allowed" more drift, which sources are "more
suspect," or which patterns are "expected noise." Bias-dressed-as-
pragmatism is the failure mode this rule exists to prevent.

Favored shapes:

- **Impartial reporting.** Warn on each signal; let the contributor
  judge per-case.
- **Mathematical floors.** 100% divergence, 0% match, presence /
  absence — these are observations, not judgments. The prose-drift
  check's error threshold lives at 100% vocabulary divergence (no
  shared significant tokens with source) precisely because that's
  a mathematical floor on pure fabrication, not a stylistic
  threshold.
- **Single uniform rules across field types.** When a rule fires
  differently on different fields, the validator has implicitly
  categorized the fields; that categorization IS the bias.

Disfavored shapes:

- Differentiated thresholds calibrated from "expected noise levels"
  observed in specific fields.
- Error cutoffs based on percentage thresholds below 100% — those
  are stylistic judgments.
- Code or doc language like "synthesis-heavy fields tolerate higher
  unmatched rates" — that's the categorization, made explicit.

Noise-reduction extensions (stemming, whitelists, n-gram adjacency)
must apply uniformly across all scoped fields; scoping a noise-
reduction technique to "fields we expect to be synthesis-heavy"
reintroduces the category judgment in a different layer.

This is the validator-side discipline. The contributor-side
discipline (resolve every warning structurally, don't rationalize
them away) lives in "Prose-drift discipline on synthesis surfaces"
above. The two pair: impartial signal → rigorous response.

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

## Source priority — anchoring when multiple sources attest

When multiple primary sources attest a fact about a subject (rank,
role, capacity, sequence of events, framing of significance), the
contributor anchors on the source closest to the subject's own
first-person attestation:

1. **Subject's own verbatim words** — highest authority for facts
   about themselves. First-person statements, self-published bios,
   filings the subject signed.
2. **Other primary witnesses' attestations** — first-hand observers
   describing the subject. Direct testimony from someone who was
   present.
3. **Media narrator / outlet framing** — lowest priority. The
   outlet's editorial summary or characterization is one step
   removed from the witness's own words.

This applies whether or not sources strictly disagree — the hierarchy
governs which source to cite as the anchor for any fact, not only
which to "believe" in a contradiction.

How to apply per case:

- **Facts about the subject** (rank, role, identity, motivation,
  internal state during an event): prefer the subject's verbatim
  quotes. Fall back to primary witnesses, then outlet framing.
- **Facts about external events the subject observed** (radar
  acquisitions, what other personnel did, command structure):
  prefer whichever primary source has direct attestation —
  typically the institutional source (military document,
  after-action report) over witness recall.
- **When outlet narrator says X but the subject's own quote says
  Y:** anchor on Y. Record the narrator divergence in
  `naming_quirks` if recurring or material; otherwise in the
  relevant entry's `note` field.
- **When a primary witness attests something about the subject
  that the subject hasn't themselves attested:** cite the witness's
  attestation as the source, marking observation_type appropriately.
- **Don't synthesize across sources to produce a "best of both"
  composite fact.** Pick one source as the anchor; if the alternate
  carries material content, capture it as a separate entry with its
  own source attribution and let the divergence stand.

This rule complements [Contradictions](#contradictions) below — the
hierarchy decides which source the contributor anchors on; the
Contradictions framing decides how the divergence itself is documented
when sources directly conflict.

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
| Source-form disagreement (two sources attest opposing forms of the same fact, contributor does not adjudicate) | `naming_quirks` entry with `resolution: disputed`; auto-rendered as `## Preserved Disagreements` near the foot of the node body |

The Confirmed/Flagged binary is unchanged by contradictions —
"contradicted" is not a third status. Both sources remain confirmed
from their respective origins; the evidentiary disagreement is
documented separately.

---

## Rumors — circulating claims without primary-source backing

Person / organization / event / location artifacts carry an optional
`rumors[]` section recording widely-circulated public-record claims
the repository has positioned on but not yet anchored to a verbatim
primary-source quote. Two statuses, two reader-visible render
surfaces:

- `not-primary-source-established` — the claim circulates in public
  discourse (Wikipedia, third-party biographies, news coverage,
  organizational PR) but no primary attestation has been archived in
  this repository. Renders as a `## Public-Record Claims Without
  Primary Source` section. Reader sees both the claim and the
  repository's stance: "we know this circulates; we haven't sourced
  it." Investigator note in the entry captures what would graduate
  the rumor to a quote (e.g., "when the IRVA bio is re-archived from
  Wayback, graduate r3").

- `primary-source-disputed` — primary sources in the archive
  actively refute the claim. Renders as a `## Primary-Source
  Contradictions` section. The contradiction itself is the
  evidentiary finding; the note field carries the refutation text.

Both surfaces serve dual purposes — fabrication-prevention for future
contributor sessions ("we already considered this; don't re-introduce
it without a source") and reader-visible transparency ("here's
what's circulating and how we evaluated it"). When a primary source
eventually anchors a `not-primary-source-established` rumor, graduate
it to a `quotes[]` entry citing the new source and delete the rumor
entry — `git log --follow` preserves the rumor history.

Rumors are NOT a third evidentiary tier. The Confirmed / Flagged
binary still applies to the structured-table content of the node;
rumors are a separate catalogue of circulating-but-unanchored
claims, distinct from both confirmed facts and structured-Flagged
secondary-source-only entries.

---

## Three-layer evidentiary architecture

The repository carries three distinct evidentiary layers. Each has a
different role; the layers' boundaries are load-bearing for the
discipline.

### Entity nodes — facts

Entity nodes (people, organizations, documents, events, transcripts,
media, locations) carry **facts**: single-source attestations,
including load-bearing facts that name other entities. The fact
"Grusch on JRE #2065 named Lockheed Martin as the contractor he
provided to the ICIG" is a fact about Grusch — it lives on his
person node and on the JRE transcript node and (because it's load-
bearing for Lockheed Martin) on the Lockheed Martin organization
node. Same primary source; three entity-side fact records. None of
them speculates beyond what the source attests.

Entity nodes keep cross-node links, `## Associated Nodes`, structural
cross-references (Affiliations rows pointing at orgs, Speakers
pointing at persons, transcript `derived_from`, etc.), and prose-
section references to other entities where the primary source
attests them. Those are facts, not findings.

### Finding nodes — multi-source patterns

A finding documents a **pattern that becomes visible only by reading
multiple primary sources together**. No single source attests the
pattern; the synthesis-of-reading-together produces information not
present in any constituent attestation. Multi-source convergence
(or divergence on a single question) is what makes it a finding,
not the number of entities it touches.

Findings cite primary sources DIRECTLY via `evidence[].source.path`,
never entity-node markdown files. The `attestor_path` field on each
evidence row captures who attested; the citation itself goes to the
source.

Findings duplicate primary-source content from entity nodes BY
DESIGN. If a finding cites material the relevant entity node
doesn't yet attest, the entity node is updated first (primary
source confirmed + archived) before the finding can use it. The
`finding-source-in-entity-node` check enforces this directionally:
every `quotes[].source.path` on a finding artifact must appear in
at least one entity-type research artifact's `primary_sources[]`.
Findings can't introduce sources the entity layer doesn't already
attest.

Findings DO NOT REFERENCE the investigations that consume them —
directional contract enforced by the `finding_no_investigation_refs`
check. Findings stay cluster-neutral so they can be cited from
multiple investigations.

Entity nodes (person / organization / document / event / transcript /
media / location) DO NOT REFERENCE findings or investigations —
symmetric directional contract enforced by the
`entity_no_finding_or_investigation_refs` check. Facts flow up to the
synthesis layer; the synthesis layer does not flow back into the
fact substrate. The Ryder person node attesting that he was named in
the SD004 statement is a fact; pointing the Ryder node at the
finding that synthesizes the multi-source authorship-chain pattern
would invert the flow. Findings and investigations are discoverable
from the priority queue, the research-queue cross-references, and
inter-finding / inter-investigation paths — not from the entity
layer pointing at them.

Findings are not verdicts. They document the multi-source pattern
and stop there — what the convergence establishes, what it doesn't
establish, where it diverges. Hypothesis evaluation belongs on
investigation nodes.

### Investigation nodes — speculation-tolerant hypothesis evaluation

An investigation pursues an open question or hypothesis by consuming
findings and entity-node facts. Investigations are
**speculation-tolerant** — the layer where hypotheses are evaluated
against the primary-source record. Per-hypothesis status verdicts
capture the current evidentiary standing as free-text phrases
("Substantiated as allegation on record"; "Not established by
primary sources"; etc.).

Investigations link to and summarize findings via `cited_findings[]`
and per-hypothesis `sources[]` rollups; findings do not link back.
Investigations build cases — proving, disproving, or further
pursuing the question.

Investigation prose surfaces (hypothesis_evaluation, best_current_answer,
counter_evidence, open_questions, closure_path) are NOT subject to
the prose-drift check (speculation by design). Instead, the
`investigation_hypothesis_citation` check requires each
hypothesis subsection to carry a non-empty `sources[]` rollup
naming the findings or entity-node anchors the contributor drew on.

### Bright line — fact vs finding

A **fact** = a single attestation from a single primary source. Lives
on the relevant entity nodes (speaker's node, named-subject's node,
document / transcript / event node where attested). May reference
other entities (because the source names them) but doesn't synthesize
across sources.

A **finding** = a pattern that becomes visible only when multiple
primary sources are read together. No single source establishes the
pattern; the synthesis is the cross-source convergence (or
divergence on a single question).

Grusch on JRE naming Lockheed = fact (one source, one statement).
Lockheed's consistent refusal to deny across three Liberation Times
moments over 16 months = finding (three sources, the pattern is the
consistency). Lacatski authoring SD004 page 1 (anonymous in SD004,
named in Elizondo QFR, entered into House record) = finding (three-
source chain establishing authorship).

### Promotion thresholds

An open question or caveat below the investigation threshold stays
structurally encoded on the entity node — empty period_end fields
with prose hedges, naming_quirks with `resolution: disputed`, etc.
Don't track sub-investigation items in a workflow surface; the
entity node is the canonical record of what the corpus knows.

An open question becomes an investigation when it picks up ANY of:
active pursuit (someone gathering primary sources to answer it),
cross-entity scope (≥2 entity nodes), competing answers being
weighed (≥2 hypotheses with primary-source backing on different
sides), or analytical content requiring sustained evaluation
(≥ ~100 words).

A finding is justified when the multi-source convergence pattern
emerges — typically when 3+ independent sources converge on (or
diverge on) a single question. The pattern-shape is what matters,
not the entity count.

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

This section is auto-generated by `scripts/build/associate.py` from
`[`/path`]` link references in the node body. Do not hand-edit.

---

## Primary sources and archival

Every external URL cited in any node is archived locally in
`/sources/{category}/{filename}` and registered in
`/sources/manifest.yaml`. The local archive is the integrity guarantee;
the Internet Archive Wayback Machine submission (via
`scripts/tools/archive.py`) is insurance.

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

### Inside `/scripts/` — five tiers by caller / role

`/scripts/` is organized by caller and role rather than by file type.
Every script lives in exactly one of five subdirectories — no Python
script sits directly in `/scripts/` itself. New scripts land at the
tier that matches who invokes them and what role they play:

- **`/scripts/build/`**: the build pipeline + the validators that gate
  each phase. Contributor-facing — contributors invoke these directly
  during a build session. The orchestrators
  (`build-from-research.py`, `validate.py`, `validate-research.py`,
  `review-coverage.py`) plus scaffolders (`new.py`,
  `research-scaffold.py`), Phase I extraction (`extract-source.py`),
  post-build housekeeping (`associate.py`, `build-state.py`).
  Per-type renderer modules dispatched by
  `build-from-research.py` live under `/scripts/build/renderers/`
  (one module per node type plus `_common.py` and `_universal.py`).
- **`/scripts/tools/`**: standalone utilities, integrations, and
  diagnostics — also contributor-facing but not part of the
  scaffold → render → validate transformation pipeline. The
  manifest CLI (`manifest.py`), Wayback submission (`archive.py`),
  YouTube transcription (`transcribe.py`), and read-only contributor
  diagnostics (`check-vocab.py`, `coverage-suggest.py`, `normalize-locations.py`).
- **`/scripts/checks/`**: per-check modules — every named validator
  check (verbatim-quote, prose-drift, chronological-ordering,
  manifest-checksums, iff-section, etc.) lives at
  `scripts/checks/{check_name}.py`. The three validators under
  `scripts/build/` are thin orchestrators that import + dispatch
  these via explicit step lists. Contributors don't usually invoke
  check modules directly (the orchestrators do), but each check is
  individually importable for unit-testing or single-check debugging.
  Shared scaffolding (`_research_utils.py` for entry-list checks)
  lives alongside as a private module.
- **`/scripts/tests/`**: gate-internal infrastructure that exists ONLY
  to support the pre-commit chain — the orchestrator (`pre-commit.sh`)
  plus its internal regression tests (`help-check.sh`, `smoke.py`,
  `test_stopwords.py`, `file-size-check.sh`, `cookies-check.sh`). No
  contributor invokes these directly; the directory is the gate chain's
  private toolkit.
- **`/scripts/lib/`**: shared cross-cutting helpers (`_common.py`)
  imported by scripts in `build/` and `tools/` and by the per-check
  modules in `checks/`. Kept separate so the cross-script lockstep
  guarantee — the verbatim-quote check, prose-drift check, and
  description-drift check all extracting source bytes through the
  same `extract_source_text` and tokenizing through the same
  `STOPWORDS` set — is mechanical rather than comment-discipline-
  based. Also carries the markdown helpers (`parse_frontmatter`,
  `extract_h2_sections`, `extract_section`) and the
  `schema_version_compat_messages` helper that consolidates the
  schema-version compatibility check across content nodes, research
  artifacts, and governance-doc / template frontmatter.

The split between `build/` and `tools/` is along produces/transforms
vs assists. `build/` contains scripts that scaffold, render, or
validate the repository content layer (the pipeline that produces
node bodies from artifacts, plus the validators that gate each
phase). `tools/` contains standalone utilities that don't transform
content — they sync the manifest, archive sources, download
transcripts, or report read-only diagnostic information.

New scripts follow the rule: contributor invocation transforming
content → `build/`; contributor invocation that's utility /
integration / diagnostic → `tools/`; per-check module → `checks/`;
gate-only support code → `tests/`; shared helper code → `lib/`. The
no-loose-scripts rule (every script in exactly one subdir) keeps the
top of `scripts/` scannable as five role-labeled directories rather
than a flat heap.

### Inside `/meta/` — root vs subdirs

`/meta/` itself follows a sub-rule that grew implicitly and is
codified here. New governance items land at the tier that matches
their character:

- **Root** (`meta/conventions.md`, `meta/schema.yaml`,
  `meta/sources-access.md`, `meta/BACKLOG.md`, `meta/roadmap.md`):
  stable governance specs and forward-looking work registers — the
  rules and the active agenda. A contributor consults these at
  session start or when something on the work queue applies.
- **`meta/toolkit-notes/`**: validator issue-log (auto-appended by
  the validator orchestrators). Reserved for any future retrospective
  or technique notes — backward-looking lessons live here when they
  surface. Empty of `.md` content at present.
- **`meta/templates/`**: scaffolding templates, one per node type.
  Consumed mechanically by `scripts/build/new.py`; rarely read directly
  by contributors except when a new node type is being added.
- **`meta/topic/`**: topic-specific governance — the priority
  research queue, topic overview, corpus-specific addenda, in-
  progress contributor working notes.
- **`meta/research/`**: YAML research artifacts backing each content
  node — the structured fact layer. One artifact per content node
  (`meta/research/{slug}.yaml`); `target_node` declares the pointer
  to `/{type}/{slug}.md`. Edited by contributors during Phase I,
  consumed mechanically by `scripts/build/build-from-research.py`
  (Phase II) and validated by `scripts/build/validate-research.py`.
  Topic-
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

---

## Comments describe code, not refactor history

Code comments describe what a function or script does and any
non-obvious why — invariants, layering rules, surprising behavior.
They do not carry refactor history. Specifically forbidden in comments:

- BACKLOG identifiers (`per BACKLOG C21`, `closes BACKLOG #3`)
- Commit hashes (`migrated at af5f789`, `per commit 60bb88d`)
- Dated audit notes (`2026-05-05 audit surfaced ...`,
  `corrected during this session`)
- Phase / cluster markers (F.5b, D.4, C17)
- Section blocks: `Origin: introduced at ...`, `Migration: ...`,
  `Anchor pattern: ...`
- "Previously X was Y; now Z" reframings of how the code evolved
- "Mirror X exactly" sync-discipline reminders for code that has
  since been centralized

The PR description and commit message are where the *why we changed
it* lives. The code comment is where the *why it is the way it is*
lives, and only when that why is non-obvious from the identifiers
and structure.

### NO BANDAIDS rule

Any issue found during an audit either gets fixed immediately or
filed in BACKLOG for later. Never document the issue as a comment
in the affected code (`// known issue: X never fires under
condition Y`). The choices are: fix-now (preferred for mechanical
issues, missing checks, hygiene gaps) or BACKLOG-and-track (for
design questions, convention-level changes, items needing user
consensus). Comments are not a third option.

The carrying-cost concern is concrete. Comments referencing closed
BACKLOG entries become stale pointers when the entry is removed.
"Origin / Migration / Anchor pattern" docstrings accumulate as
refactor cycles compound, eventually drowning the description of
what the code currently does.

### BACKLOG lifecycle discipline

The goal is to REMOVE items from BACKLOG, not accumulate annotations
referencing them. When a BACKLOG entry closes:

- Delete the entry's block from `meta/BACKLOG.md` in full. No
  retirement marker, no placeholder, no renumber. The commit that
  ships the closure carries the implementation diff and a commit
  message that describes what shipped — that is the canonical
  record. `git log --grep <ID> -- meta/BACKLOG.md` retrieves it.
- IDs within a section are positional and not reused. Before
  assigning a new ID, check git log for the largest historical ID
  in the target section (`git log --all -p -- meta/BACKLOG.md |
  grep -oE '\b<SECTION>[0-9]+\b' | sort -V -u | tail -1`); the new
  entry takes the next unused number so historical references via
  `git log` stay unambiguous.
- Sweep code comments that referenced the closed entry's
  identifier — either delete the comment entirely (if the entry's
  resolution is now reflected in the code itself) or rewrite to
  describe current behavior without the BACKLOG anchor.
- This sweep is part of closing the entry, not follow-up work.

Open BACKLOG entries follow the same describe-current-state rule.
The entry text describes the work to be done and why it matters —
forward-looking, prescriptive. It does NOT carry "Surfaced from",
"introduced by audit X on date Y", commit hashes pinning when the
need was identified, or other past-work narrative. Where the
audit / session / commit that surfaced the work lives is in git
log, retrievable via `git log --grep <ID>` once the entry is named
in any commit message. The entry itself describes only the work.

Same rule extends to retirement of validator checks, deletion of
renderer dispatch branches, removal of conventions sections, and
removal of obsolete templates: the file should describe current
state and pending work, not past evolution. Git log carries the
evolution.

### What TO keep in comments

Functional descriptions of what the code does, plus non-obvious
why notes that anchor on still-live concepts:

- `meta/conventions.md` section names (the convention is the
  durable contract)
- `meta/schema.yaml` field paths
  (`schema.yaml::types.research-artifact.conditional_keys`)
- `meta/roadmap.md` mentions when scoping a "not yet implemented"
  check
- Layering invariants (e.g., "presence-guard, not truthy — opens a
  gap with `frontmatter_required` if loosened")

Anchor comments on durable concepts. Avoid anchoring on transient
ones (specific commits, dated audits, phase markers).
