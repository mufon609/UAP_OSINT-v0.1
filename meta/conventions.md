---
id: meta/conventions
type: meta
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

The repository **preserves**; it records what each source says verbatim
and does not clean, correct, or improve it. Source-form artifacts — OCR
errors, the document's own typos, garbled-but-legible scan regions — are
preserved as-is and flagged (`naming_quirks` / sic), never silently
fixed. Recovering the human-visible text of a garbled scan is
preservation; deleting or altering it is not.

---

## Relevance can be relational

An entity earns a node when it has a primary-source-documented connection
to the investigation's subject — and that connection may live in the
entity's *relationships* rather than in its own sources. An entity can be
load-bearing through documented ties — a shared parent organization, a
shared contractor, a sister-office / predecessor / successor
relationship, a named association in another party's record — even when
the entity's own primary sources never mention the subject at all. When
that is the case, the node captures two things: (1) the connecting
relationship(s), each attested by the source that establishes it — the
load-bearing core; and (2) enough basic, source-grounded context about
the entity for the connection to be legible, without sprawling into
detail unrelated to the investigation. The connection is documented
strictly to what the sources support, never beyond; any inference about
*why* it matters stays in the synthesis layer (findings / investigations)
and with the reader.

Corollary: an entity's relevance often cannot be judged from its own
source in isolation — it is judged against the connected record. The
build topology applies this at investigation time (see
`prompts/topology.md` — "Load-bearing-ness is judged in context").

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
verbatim-quote check fails any commit where a quote's `text` does not
appear in the extracted source. The check runs against the research
artifact's `quotes[]` directly — `text` + `source.path` are structured
fields, no rendered-output parsing involved. The rendered node body
inherits the verified quote text from the artifact by construction.
The enforcement is invisible to the reader by design. The validator
catches silent drift (a quote edited in an artifact months later that
no longer matches the source) and broken source references; it does
not, and cannot, perform trust on the reader's behalf.

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

**When a source gets a `.txt` sibling — the rule.** A `.txt` sibling
exists *if and only if* the source's default extraction is not a
faithful rendering of the original text — i.e. its `extraction_type`
is `ocr-scan` or `extraction-lossy`. A `text-native` source (clean
text layer, HTML, plain text) is rendered faithfully by `pdftotext` /
direct read and **never gets a sibling**: producing one is busywork
and adds a drift surface for no gain. The two non-text-native cases
are the "corrupted or image" pair — `ocr-scan` is a scanned image
(OCR reconstructed the text from page pictures), `extraction-lossy`
is a text-native PDF whose extracted *bytes* are wrong (not an image,
but corrupted at the content-stream / extraction layer). Sibling
existence keys on extraction faithfulness, not on file type.

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
extraction-lossy` sources — text-native PDFs whose extracted text is
**pervasively** unreliable for non-OCR reasons: stenographic-format
noise (inline line-number prefixes and page-footer triplets on every
line, as in court-reporter transcripts) or
systematic Unicode-mapping corruption across the document.
Evaluation of the Unicode-mapping failure mode (`11½`
encoded as byte `\x87` → U+2021 in the embedded font's CMap) confirmed
the corruption lives in the source PDF's content stream itself:
`pdftotext`, `mutool`, and `pypdf` all faithfully reproduce the same
bytes because the PDF tells every compliant reader that the glyph is
`‡`. Switching extraction tools is not a path forward.

**A sibling must be proportionate to the damage.** The recovery for a
*pervasively* corrupted extract is the contributor-produced clean
transcription, visually verified against the source page. But a clean,
natively-paginated text layer marred by only a *sparse, isolated*
glyph artifact — a single `11½`→`‡` in one passage of an otherwise
pristine transcript — does **not** warrant hand-transcribing the
document. That manufactures a large, drift-prone artifact to repair
one character. Such a
source stays `text-native`: `pdftotext` is the canonical extract
(natively paginated, so `p. N` resolves for free against its form
feeds), and the isolated glyph is handled at the point of use —
re-derive the affected quote, or add the specific Unicode-confusable
to `normalize_for_compare` — never by transcribing the whole document.
Reserve the sibling for extraction that is broken throughout; the test
is the OCR-producer / pervasive-noise signal below, not the presence
of any single bad character.

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
  when the extract looks clean. (Some PDFs have a clean extract
  despite OCR producer metadata; that's the
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
   despite OCR-suggesting producer metadata. Run `pdftotext -layout source.pdf`, diff
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
manifest entry (matching the parent PDF entry); it is **NOT** listed
in any artifact's `primary_sources[]` — the parent PDF is the
primary source, the sibling is only the extraction surface. Quotes
derive their verbatim text from the sibling but cite the PDF path in
`source.path`.

**The parent-in-`primary_sources[]` rule generalizes to every paired
sibling — OCR clean-text and speaker-attribution alike.** Both flavors
register as a manifest entry whose URL carries a fragment marker
distinguishing it from its parent — `#clean-text-transcription` for an
OCR sibling, `#speaker-attribution` for the speaker-attribution sibling
produced by `/prepare-transcript-sibling` (agent-based attribution
pipeline; the photo-identity-log machinery at
`scripts/tools/VIDEO-PIPELINE.md` is the conditional image-verification
backstop, not the spine). In both cases `primary_sources[]` lists the
**parent** (the PDF for an OCR-scan source, the auto-caption /
human-corrected-caption file for a label-less transcript), never the
sibling. The structural twist between the two flavors is what the
sibling does to its parent: the OCR sibling **replaces** the parent's
corrupt text layer (quotes derive verbatim text from the sibling); the
attribution sibling **coexists with** the parent, adding the speaker-
attribution layer (a YAML indexed by line range into the source file —
see `meta/schema-speaker-attribution.yaml`) that
`validate-research.py` matches `speaker_id` against (the
`speaker_attribution_consistency` check, which resolves each quote's
`[MM:SS]` anchor to the covering turn) while the auto-caption file
remains the verbatim source `validate.py` matches `quote.text` against. The fragment-marker pattern is the manifest's
signal that an entry is a sibling, not a parent.

**Sibling-production method standard.** The four paths above are
interchangeable on fidelity, but they are NOT interchangeable on
*uniformity*: the VLM (vision-language model) path runs through the
model provider's *generative* content-safety filter — a platform-level
guardrail on the model's output, entirely separate from this
repository's topic scope and editorial rules. It can fire unpredictably
mid-transcription, and its trigger is opaque: in practice it has blocked
one source while transcribing another of comparable subject matter
cleanly, so it does NOT track this repository's topic scope and is never
a signal about a source's relevance. The one predictable case is content
the model's policy treats as sensitive to *reproduce* — plainly CBRN /
weapons-design-sensitive material reliably trips the generative filter,
which is why such a source skips the VLM step (pre-screen below). A
dedicated OCR engine
does text *recognition*, not generation, so it is filter-immune and
uniformly applicable. The standard method
ladder for every OCR-scan / extraction-lossy sibling:

0. **Pre-screen — plainly CBRN / weapons-design-sensitive?** Judge from the
   title / table of contents. If so, **skip the VLM step and start at the OCR
   engine** (step 2): a model reproducing such a passage as its own tokens
   hard-terminates on the content filter, wasting the attempt. The
   `/prepare-ocr-sibling` skill applies this route check first.
1. **Default — VLM page-image read** (path 3): highest fidelity on
   degraded scans (contextual glyph restoration, equation/table
   handling). Use whenever it completes.
2. **Filter fallback — a dedicated OCR engine** (path 2), filter-immune:
   **Tesseract 5** (`sudo apt install tesseract-ocr`; rasterize with the
   already-present `pdftoppm`) as the free/local default, or a **cloud
   Document-OCR API** (Google Document AI / Azure Document Intelligence)
   for higher fidelity on math / Greek / layout. The chosen engine is a
   project dependency for completing the OCR-scan corpus.
3. **Manual transcription** (path 4): last resort for short documents an
   engine mangles.

**Fidelity discipline for OCR-engine output — preserve, don't strip or
fix.** An OCR engine renders body prose reliably but mangles regions
that are hard to recognize mechanically yet legible to a human
(struck-through classification banners, equations, Greek / subscripts,
degraded figure labels, third-party distribution inserts). Do NOT delete
or mechanically "correct" these — deleting loses information a human can
read off the source image, and altering the document's own words erases
the source-form record. The sibling stays faithful and complete: the
engine's clean prose stands; regions it garbles are left in place; the
document's own typos are preserved sic. **When a quote is drawn from a
region carrying a special or garbled glyph — a superscript / subscript,
Greek, math symbol, or isotope (He³, 10¹³), which an OCR engine drops to
a baseline digit or to `?` — that passage MUST be checked against the
source page image before the quote is finalized.** The verbatim-quote
gate compares quote↔sibling, never sibling↔document, so it cannot catch a
glyph mangled identically in both. Distinguish the two cases that check
resolves: the **document's own** non-canonical form — a real printed typo
(`lithographycal`, `Tokomak`) — is carried verbatim into `quote.text` and
logged as a `naming_quirks` entry (`preserve-as-sic-in-quotes`); an **OCR
mangle** of a glyph the document rendered correctly (He³ → `He?`) is
**corrected** to the document's reading in both the sibling and the quote,
never logged as sic, because it is not the source's form. Draw verbatim
quotes from the clean prose.

**Provenance + verification are mandatory regardless of method.** Record
the production method (VLM / Tesseract / cloud-OCR / manual) in the
sibling's manifest note. Verify before canonical: an independent agent
session for VLM / clean output; **contributor (human) page-by-page
review for OCR-engine output** (the path-2 reviewer — also the robust
choice when an independent-agent verifier would itself hit the content
filter on the source's images). The recorded method keeps per-sibling
fidelity transparent and lets the method improve over time without
re-litigation.

**Silent-sibling lookup.** `extract_source_text` finds a `.txt`
sibling by *path stem*, not by manifest registration. A
`<same-stem>.txt` file adjacent to the source PDF gets used by the
validator's verbatim-quote check whenever the parent PDF's manifest
entry has `extraction_type: ocr-scan` or `extraction-lossy`,
regardless of whether the sibling itself has a manifest entry. The
discipline: file and manifest entry are created together. A
sibling-on-disk-but-not-in-manifest is a silent dependency —
quote-verification depends on a file the manifest doesn't record,
and deleting the file (e.g., as "orphan
cleanup") silently breaks the build by reverting extract output to
the PDF's unusable text layer. Register the sibling at the moment of
creation, and treat the manifest-paths verifier (`scripts/tools/manifest.py
verify-paths`) plus pre-commit as the only safe orphan-cleanup gate
for sibling files.

**Per-quote contributor discipline when an OCR-scan source's `.txt`
sibling hasn't been produced yet.** *(Scope: the `/build` pipeline
produces the verified sibling **before** the Worker — step 4b, "OCR-scan
sibling readiness"; build-protocol → source-read-first — so a correctly
run `/build` does not reach this state. But that is role discipline, not
a hard gate: the verbatim-quote check is structurally blind to a
sibling-less OCR quote (it passes — see below), so this discipline is the
safety net whenever a quote does reach the artifact before its sibling —
an out-of-pipeline manual edit, an `/augment`, or a `/build` where step 4b
was skipped.)* A new OCR-scan
source may enter the corpus before a contributor produces its clean-text
sibling — the
validator falls back to `pdftotext` output of the OCR'd PDF in that
case, and OCR character-corruptions (`telated` for `related`,
`compatrtmented` for `compartmented`, `appatently` for `apparently`) pass the
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
   backtick-bracket path on the canonical target — e.g., `"acme
   widgits" [`/organizations/acme-widgets`]` — the prose-drift check
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
evidentiary claim, but
is not the primary reader-visibility mechanism.

After registering the naming_quirks entries, re-grep **the passages
you are quoting** for additional artifact patterns matching those
already logged — drafting the registrations often surfaces artifacts
not caught in the initial scan.

Scope that re-grep to quoted text (and the `significance` / `location`
that frame a quote). A `preserve-as-sic-in-quotes` entry exists to
annotate a source form the reader **encounters on the node**, so its
`observed` form must appear somewhere the reader meets it — inside a
quote, or in the heading / locator describing one. Do **not** sweep
the entire source extract and log every OCR typo: an incidental
misspelling sitting in body text you never quote has no on-node
referent, and the entry then renders as a correction to nothing — an
*orphan* source-form note. Scan fidelity as a whole is recorded by the
manifest entry's `extraction_type` (`ocr-scan` / `extraction-lossy`),
not by one `naming_quirks` row per source typo. **Source-Form Notes
stays strictly grounded — it carries no orphans.** Resolve every
ungrounded `preserve-as-sic-in-quotes` entry one of two ways: an
incidental source typo in body text you never quote is **dropped**
(scan fidelity is the `extraction_type`'s job, above); a deliberate
non-canonical variant kept for navigation / identity resolution — an
auto-caption name mangling, an idiosyncratic source abbreviation whose
specific instance you did not quote — is **reclassified
`off-node-variant`**, which renders in the node's separate
`## Name Variants` section (see *Off-node variants* below) rather than
Source-Form Notes. At audit time `scripts/tools/coverage-suggest.py`
and the `review-coverage.py` grounding gate flag any ungrounded
`preserve-as-sic-in-quotes` entry — a hard signal, no longer a
judge-each carve-out.

The discipline is a per-quote workaround, not a substitute for
producing the `.txt` sibling. Once the sibling exists and the manifest
entry's `extraction_type` is set to `ocr-scan`, the validator extracts
from the sibling rather than the corrupted PDF text layer; the
naming_quirks entries continue to record the original artifacts as
provenance and continue rendering via the Source-Form Notes section.

### A source naming an entity under a non-canonical form — flag it, stub it

The `preserve-as-sic-in-quotes` mechanism above is not only for OCR
corruption and caption typos. It applies equally when a source names a
known entity — a person, organization, program, or place — under a
**non-canonical form**: an idiosyncratic abbreviation, a former name, or
a misspelling. Such a reference is handled three ways at once, all
required:

1. **Preserve the source form verbatim in `quote.text`** — never silently
   substitute the canonical form. The source form lives **only** inside
   verbatim quotes (and the `location` / `significance` that describe them).
   Every *synthesized* surface the repo authors in its own voice —
   `display_title`, `quote_attribution`, the `description` prose,
   cross-reference labels, and the canonical node name — uses the **canonical**
   form (say, "Advanced Materials Research Program (AMRP)"). The repo never
   adopts a source's idiosyncratic abbreviation as its own label: a
   `display_title` that reads "AMR Program" instead of "AMRP" is the deeper
   version of this defect — the variant leaking out of the verbatim layer into
   the repo's own naming. The quote still carries "AMR Program" verbatim and is
   still flagged (below); canonicalizing the synthesized surfaces does not
   remove that need, it just stops the variant from masquerading as the repo's
   chosen name.
2. **Register a `naming_quirks` entry** mapping the observed source
   form → canonical name + source path. Choose the resolution by
   whether the variant is quoted on this node: when the source form
   appears in a quote (or its heading / locator), use
   `preserve-as-sic-in-quotes` and it renders in `## Source-Form
   Notes`; when the entity is stub-linked but its variant form is not
   quoted on the node, use `off-node-variant` and it renders in
   `## Name Variants` (see *Off-node variants* below). Either way the
   variance is catalogued and the canonical is carried navigationally.
3. **Carry the canonical entity navigationally** — a stub cross-reference
   to its canonical `/{type}/{slug}`, **even when that node is not yet
   built** (per *Cross-reference paths to unbuilt nodes — use a stub,
   never null*). In prose, wrap the source-verbatim form with the
   canonical bracket path so the prose-drift check still matches the
   source token — e.g. `Advanced Materials Research (AMR) Program
   [`/organizations/amrp`]`.

The failure mode this closes: a source's own abbreviation reads as
legitimate document text, so it slips past the OCR-artifact radar (it is
not a corruption), and because its canonical node isn't built there is no
name-match to trigger a cross-reference — so the reference is dropped and
the variance goes unflagged. **An entity referenced under a variant form
is not glossed over because its node doesn't exist yet; it is stubbed and
flagged.**

### Off-node variants — catalogued, not on the node

`off-node-variant` is the `naming_quirks` resolution for a non-canonical
form the source attests but that **does not appear in any quote on the
node** — an auto-caption mangling of a name, an OCR variant, or an
entity abbreviation whose specific instance you catalogued for
navigation / identity resolution but did not quote. It is the
deliberate counterpart to an orphan: the same not-on-node shape, but
declared rather than accidental.

Such entries render in their own `## Name Variants` section (Variant
Form → Canonical → Source), parallel to how `disputed` renders in
`## Preserved Disagreements`. This keeps `## Source-Form Notes`
strictly grounded — every row there is a form the reader meets in
quoted text — while the off-node catalogue (caption manglings kept for
speaker-identity resolution; entity variants that are stub-linked but
not quoted) stays reader-visible and greppable without polluting the
grounded table. Choose the resolution by one test: **does the
`observed` form appear in quoted text (or the heading / locator
framing a quote) on this node?** Yes → `preserve-as-sic-in-quotes`
(Source-Form Notes). No, but worth keeping for navigation →
`off-node-variant` (Name Variants). Neither — an incidental typo of no
navigational value → drop the entry.

### Transcript provenance and audit discipline

Transcripts of speech sources split into two evidentiary classes by
how the audio-to-text transcription happened:

**Human-produced transcripts** (accredited stenographic court
reporting; outlet-published transcripts with human editorial review
against audio — a national news outlet's or wire service's transcript
service, broadcast transcripts where the outlet's process
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
mis-transcription (`Halverson` for `Halvorsen`, `acme widgits` for
`Acme Widgets`, `Petrakis` for `Petrakos`, `Dan ricco` for `Dan
Rizzo`). When both quote text and caption file carry the same
machine artifact, the verbatim-quote check passes trivially — the
textbook auto-caption blind spot. The `transcript_provenance` value
`auto-caption` marks these sources; the underlying audio/video is
the canonical original. Audit handling mirrors `ocr-scan`:

- **Known caption artifacts** registered as `naming_quirks` entries
  (same workflow as OCR-scan source-form preservation).
  Resolution by the grounding test above: a mangling that appears in a
  quoted passage on the node is `preserve-as-sic-in-quotes` (renders in
  Source-Form Notes); a mangling catalogued for speaker-identity
  resolution but not present in any on-node quote is `off-node-variant`
  (renders in Name Variants — see *Off-node variants* above).

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
  with its own manifest entry; the `transcript_provenance`
  value moves from `auto-caption` to `human-corrected-caption` once
  the correction step is documented.

**Hybrid sources** — auto-caption files contributor-corrected
against audio playback — flag as `human-corrected-caption`. Once
corrected, equivalent-footing with stenographic and published-
transcript classes.

The five-value `transcript_provenance` enum is the schema layer
(see `manifest_entry.transcript_provenance_values` in
`schema.yaml`). The audit discipline above is the contributor layer.

**Speaker attribution: source format selects the method.** Provenance
classifies *text* fidelity; it also determines *how speakers are known*. A
transcript's speaker labels are either carried by the source or absent — and
the absent case must be *reconstructed against the recording*, never inferred
from text alone. Inferring a speaker from textual cues (register, who-
addresses-whom, question-then-answer shape) is a hypothesis, not a
conclusion: it is the exact process that produces misattributions — a line
delivered by one participant assigned to the other, or a two-party exchange
collapsed onto one speaker. Speaker attribution on a label-less source is
**confirm-against-source** — the audio/video analog of the verbatim
source-read-first rule.

- **Labeled sources** (`stenographic`, `published-transcript`, and
  `human-corrected-caption` where the corrector preserved labels): speakers
  come from the source's own attribution. Populate `speakers[]` and each
  quote's `speaker_id` directly from the labels; the substring-verify check
  already covers the text. No diarization or face work.

- **Label-less sources** (`auto-caption`, Whisper output — words and
  timestamps but no speaker labels): the speaker of every quote must be
  reconstructed and confirmed against the recording. Select the method by
  what the source provides:
    - *Video with visible faces* → the **image path** (preferred). Extract
      frames at each quote's timestamp (`extract-frames.py`), match faces
      against the persistent baseline registry (`detect-faces.py`; register a
      baseline first when a speaker has none), and **confirm by eye** —
      seeing the mouth move, or the non-speaker shown listening, against a
      registered face is a stronger identity check than telling similar
      voices apart by ear. A human verifies the frames before a `speaker_id`
      is trusted.
    - *Audio-only* (no usable faces) → resolve speakers from **content**, via
      the agent text-pass (`/prepare-transcript-sibling`): anchor each turn to
      a name using a self-introduction, one participant naming another, or the
      dominant speaker on a known monologue, and confirm against both sides of
      every turn boundary. A turn the text genuinely can't settle takes the
      mixed-exchange form below; never guess from a transition cue alone.
    - *Genuinely unresolvable boundary* (overlapping turns, or a handoff the
      recording can't cleanly settle) → the **mixed-exchange** form:
      `speaker_id` as a list of 2+ ids (`[s1, s2]`), rendering a `Speakers —
      mixed exchange` row. It marks the boundary honestly without fabricating
      a split; use it only when the turns are genuinely not separable, not to
      skip attribution work where they are.

When an attribution issue surfaces, route it to the proper tool, never an
ad-hoc workaround: a source recording missing from the checkout → re-fetch
with `download-video.py` (its bytes are gitignored; the manifest is the
record); a speaker with no baseline → `detect-faces.py register`; a caption
mis-transcription, or a name the machine spelled inconsistently (e.g.
`Lauren`↔`Lawrence`) → a `naming_quirks` entry; a frame match that doesn't
clearly resolve → human frame-verification or the mixed-exchange form.

The per-method tool sequence and its dependency prerequisites — and the rule
that a *missing but needed* dependency (the `.venv-face` dlib stack, browser
cookies, a face baseline) must stop the run with a remedy, while a
satisfied-or-unneeded one proceeds — live in
`scripts/tools/VIDEO-PIPELINE.md`.

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

Every quote surface above renders its blockquote through one shared helper
(`renderers/_common.py::_render_blockquote`) that **reflows soft-wrap
newlines** — quote text copied verbatim from a YAML `|` literal block keeps
the source's physical ~80-col line-wrapping, which the helper rejoins into one
`> ` line per paragraph at display time, preserving blank-line paragraph
breaks and list-item structure. So a contributor may author quote text as a
`|` block (fidelity to the source's layout) without producing a blockquote
broken mid-sentence; verification is unaffected (the verbatim-quote check
normalizes whitespace).

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
neighboring exchange — "opening statement", "Q&A exchange with a
committee member", "the witness continuing his prepared statement"); `speaker_id`
carries who-said-it. Two contributors authoring quotes from the same
source can disagree on circumstance phrasing without diverging on the
attribution — the structural reference is what validates and renders.

Three failure modes the structural reference closes:

- **Prose-attribution drift.** Different sessions could disagree on
  who said line 2:00 of a podcast and both be wrong with no mechanical
  check. The `quotes` check now fails when `speaker_id` doesn't
  resolve to a real `speakers[].id`.
- **Re-author ambiguity.** Six months later a contributor re-reading
  the artifact had to re-trace the frame + baseline match to recover
  the speaker assignment. The structural reference makes the
  assignment self-documenting.
- **Renderer inconsistency.** Hand-formatted Attributed-to strings
  varied in how they named speakers ("Halvorsen" vs "Dr. Jane
  Halvorsen" vs "Dr. Halvorsen"). Mechanical lookup from `speakers[]`
  produces one consistent rendered form per identity.

The accompanying `speaker_baseline_consistency` check
(`scripts/checks/speaker_baseline_consistency.py`) catches the next
link of the chain: every `speakers[].node_link` that points at
`/people/{slug}` should have a baseline at
`sources/photo-identity-log/baselines/{slug}/` so the video-pipeline
tools (`scripts/tools/detect-faces.py`,
`scripts/tools/spot-check-attribution.py`) can mechanically resolve the
speaker on future videos.

### Statements speaker-attribution — quotes BY the person, not ABOUT

A person artifact's `quotes[]` section carries verbatim statements *by*
the subject — the speaker is the node's subject. Quotes by other
parties about the subject do not belong in Statements; they belong on
the speaker's own artifact and on the subject's structured cross-
reference surfaces (`affiliations[]`, `relationships[]`,
`program_involvement[]`, `timeline[]` rows) with the speaker's
source cited.

The bright lines:

- **First-person utterance.** "I saw the object"; "I was the cofounder
  of …"; a press-release quote attributed to the subject. Belongs in
  Statements.
- **Co-authored academic publications.** The subject is named in the
  author byline and the passage is collectively-authored prose.
  Belongs in Statements when the substantive content is the subject's
  own research, position, or institutional claim (a co-authored
  journal abstract reporting the subject's experimental results: yes).
  May be skipped when the byline is the only subject-relevant fact and
  the passage's substance is technical content unrelated to the subject
  as a person (a co-authored technical paper on an unrelated topic:
  byline establishes affiliation, but the prose isn't meaningful as a
  statement by the subject). Either way, the publication itself
  remains the primary-source attestation of the affiliation — captured
  via the corresponding `affiliations[]` / `timeline[]` row pointing
  at the paper.
- **Self-attestation on the subject's own publication** (personal
  website, signed bio, authored book). Belongs in Statements even when
  written in third person — the subject is the publisher.
- **Quotes by others about the subject.** A reporter narrating, a
  voucher attesting, a supervisor describing the subject. *Not*
  Statements. Capture via a `relationships[]`, `program_involvement[]`,
  `affiliations[]`, or `timeline[]` row on the subject's artifact,
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

- "Self-attested capacity, contested by the official record"
- "Claim-of-record — secondary-source attestation only"

The hedge appears in the H3 header where readers see it BEFORE
reading the blockquote. A chronologically-promoted low-weight quote
can otherwise be read as an epistemic endorsement; the hedge phrase
keeps the order chronological but inoculates against that reading.
No schema change; contributor discipline at the `significance` field.

### Hearing events as venues

An event is a venue, not a speaker. Hearings carry a `Witnesses &
Testimony` cross-reference table pointing at each witness's transcript
and written-testimony nodes. What a hearing "established" is the verbatim
record those linked nodes carry; the event node navigates to them
rather than paraphrasing.

### Key Testimony selection — substantive over procedural

The hearing-event `## Key Testimony` section (and the analogous
`## Key Passages` on a hearing transcript) highlights the distinctive
evidentiary moments that make the hearing worth archiving — not
procedural scaffolding. Skip what a structured field already captures:
convening / adjournment / gavel timings (`event_intrinsic.start_time` /
`end_time` + Timeline), oath administration and "I do" affirmations
(`witnesses_testimony[].oath_status: sworn`), and routine procedural
exchanges (recognizing a Member, yielding time, submitting for the
record) — unless the procedural act is itself evidentiarily novel (e.g.
unanimous consent to classify). Prefer the specific factual claims
witnesses assert, the strongest corroborations or contradictions between
witnesses, the most-cited post-hearing press moments, and a Member's
quotable bipartisan or closing frame. Procedural weight lives in the
structural fields; the Key Testimony section is the highlights reel.

Event-level Key Testimony may overlap the witness-specific transcript or
document Key Passages, and that is expected: an event stands as a
self-contained highlights reel an investigator can read without clicking
through, and the renderer does not deduplicate across nodes.

### Contributor prose is labeled and drift-checked

Contributor prose sits on labeled synthesis fields (`description`,
`background`, `top_relevance`, `credibility_notes`) plus the
whistleblower `vouching_chain.attestation`. The prose-drift check
tokenizes each against the primary-source text and errors on every
unmatched significant token: synthesis prose must use source
vocabulary.

### News articles and books

Stored as `document` nodes (kind `non-gov-doc`, doc_form `article` or
`book`). Credibility analysis of the author/publisher lives on the
author's person node or the publisher's organization node, not on the
document.

### Prose-drift discipline on synthesis surfaces

Nodes carry contributor-prose surfaces that sit alongside the verbatim
`quotes[]` content: per-node `description` / `background` /
`top_relevance` / `credibility_notes` paragraphs, and the whistleblower
`vouching_chain.attestation`. These are labeled synthesis that frames
the evidentiary content, and contributor prose introduces a real
failure mode: unstated premises, paraphrase drift, and content widening
even when every referenced quote is verbatim-clean.

`validate-research.py`'s prose-drift check verifies
that significant words in these prose fields appear in the referenced
primary-source text. Every unmatched token is an ERROR (commit-
blocking): synthesis prose carries no licence to introduce vocabulary
the cited sources don't attest, so token-level presence/absence is a
mathematical floor applied uniformly to every scoped field and node
type. The contributor resolves each flagged token by asking — *does
this token introduce a fact or premise the source doesn't attest?* —
and then either rewriting to source vocabulary or relocating the
variance to a structured evidentiary field (below). There is no warn
tier and no "below threshold" tolerance: an ungrounded token in
synthesis prose is a defect, not a per-case judgment.

The contributor review also asks a second question: *does the prose
read as natural English?* Iterating against `check-vocab.py` until
every significant token passes can produce stilted constructions —
a source-attested participle stretched to substitute for an absent
finite verb (`is containing` instead of `contains`), source-attested
compound nouns where a single synthesis word would read better.
Source-vocabulary discipline applies token-by-token; English-grammar
discipline applies to the rendered prose. When the two collide,
restructure the sentence — don't ship the broken phrasing.

The prose-drift check is explicitly scoped to contributor synthesis
prose. Compact label / descriptor cells (role titles, short
relationship descriptors, `timeline[].event`, the corroboration
`confirms` cell) are out of scope — token-match misfires on those
surfaces; fabrication there is Phase III semantic-review territory.

**Zero ungrounded tokens on scoped fields — a hard gate, not a
target.** Calling a flagged token "legitimate synthesis vocabulary"
and leaving it in place is exactly the rationalization the error
blocks; an evidentiary precision tool is not a stylistic nag. Every
flagged token drives to one of two outcomes:

- The prose is rewritten to use source vocabulary exactly, OR
- The source-vs-prose variance is captured as structured evidentiary
  data (a `naming_quirks` entry, a `timeline[]`
  row, a `quotes[]` entry — pick the surface that carries the
  variance's evidentiary meaning).

**Resolution paths for common error shapes:**

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

3. **Source-form vs canonical-form naming variance** (source `Sue`
   vs canonical `Susan`; source `Halverson` vs canonical
   `Halvorsen`; source `Petrakis` vs canonical `Petrakos`): wrap the
   source form in the canonical link path — e.g., `Sue Halvorsen
   ([`/people/susan-halvorsen`])`. The prose-drift check strips the
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

There is no "documented residual" exemption: a flagged token cannot
remain on the artifact. It is resolved at the root — reworded, or
relocated to a structured evidentiary field whose own source
attribution carries the variance (a `naming_quirks` entry for a
source-form vs canonical-form name, and so on). A token that is absent only because
of an extraction artifact (e.g. an HTML element-boundary concatenation,
or a PDF page-number footer/header wedged into a page-spanning quote) is
fixed at the extraction layer, never accepted as a standing error.

**The pool is the node's own source TEXT — extrinsic metadata is not
credited.** The prose-drift pool is built from the node's `primary_sources[]`
text only; it deliberately does NOT include `document_intrinsic` values,
`naming_quirks.canonical`, or `context_extrinsic`. Crediting metadata
vocabulary would let words the source itself never states into the description
prose — inverting the gate's purpose. A fact attested only *extrinsically* —
by a separate source, or by structured metadata, rather than by this node's own
primary-source text — therefore cannot be asserted in this node's `description`
prose. Carry it navigationally instead: a cross-reference link to the node or
source that *does* attest it, plus a structured field (`context_extrinsic`,
`naming_quirks`) that records it out of the prose-drift scope. Example: a
document whose author line is `(b)(6)`-redacted on the source but identified
in a separate agency index — the author is carried by the link
(`[/people/…]`, `[/documents/{agency-index-slug}]`) and held in
`context_extrinsic`, never named in the description prose.
The document's own `authors_per_document` records the redaction verbatim
(`['[redacted per FOIA (b)(6)]']`) and stops — never substitute the
externally-attested name into this document's intrinsic authorship; that name is
a fact of the *attesting* source's node, reached by the cross-reference.
`check-vocab.py` surfaces the nearest source forms for an absent token (a
morphology variant or typo), but it never credits metadata either — the floor
is the same.

**Corollary — a document `description` summarizes CONTENT, not provenance.** The
recurring cost when grounding a document node's `description` is the *provenance
trap*: drafting the document's date, control number, classification, series
membership, or authorship into the description prose. That metadata lives on the
cover / title page, not in the document's content prose, so the prose-drift pool
(content text) never contains its vocabulary (`dated`, `redacted`, `producer`,
`series`, an author name) — each such token then fails the gate, and the fix is
always to *relocate*, not rephrase (the Document Summary table + Key Passages
already render the provenance). Draft the `description` from the document's own
substantive content — what it argues, finds, or proposes, in its own words — and
let the structured surfaces carry the provenance. Check-vocab correctly
returns "absent, no suggestion" for the provenance tokens, which is itself
the signal to relocate rather than reword.

### Density is source-driven

Templates and prompts do not impose count targets on artifact content.
This applies uniformly to two surfaces:

- **Entry lists.** `quotes`, `naming_quirks`,
  `affiliations`, `relationships`, `corroboration_items`,
  `program_involvement`, `publication_record`, `vouching_chain`,
  `participants`, `witnesses_testimony`, `timeline`, `key_personnel`,
  `org_relationships`, `contracts`, `media_versioning`, and any
  other entry-list section the schema defines.
- **Free-prose fields.** `description`, `background`, `top_relevance`,
  and `credibility_notes`.

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

**Density governs count, not capture.** The rule bars count *targets*;
it does not license declining to capture a class of source material the
source actually carries. Whether the source has a reference list to
record in `cited_works`, whether a passage is a load-bearing quote,
whether a contradiction is attested — those are source-*presence*
questions, answered by reading the source, not density questions. The
misread to refuse is "these references aren't load-bearing, so leave
`cited_works` empty": a source-attested reference list is captured
*because the source carries it* (the passage rubric below names
References as a capture category). For `cited_works` specifically, the
empty-state ambiguity is closed by the three-state affirmation below
(`cited_works: NONE | IGNORED | non-empty list`) — a bare `[]` is
rejected outright, so the contributor cannot quietly drop a captured
list on "not load-bearing" grounds. Density governs only how many
entries a captured list then yields. The same holds for every
required-but-emptyable source-anchored section: an empty list is
correct only when the source genuinely lacks that material, never as a
discretionary skip.

### `cited_works` affirmation — three-state discipline

`cited_works` is required on every document artifact, and must take one
of three valid shapes — never a bare `cited_works: []`. The empty list
was historically ambiguous (it meant BOTH "source carries no reference
list" AND "source carries one but nobody captured it yet"); the
affirmation closes that ambiguity by recording the contributor's
positive judgment in the artifact.

- **`cited_works: NONE`** — the source carries no formal reference
  list at all. Executive orders, news items, hearing transcripts,
  short documents whose argument doesn't cite outside work. Renders a
  one-line `## References` affirmation: *Source carries no reference
  list.* Greppable across the corpus via
  `grep -l '^cited_works: NONE$' meta/research/*.yaml`.

- **`cited_works: IGNORED`** — the source HAS a reference list, but
  the contributor judged it low-value and deliberately did not capture
  it. Release valve, *not* a routine skip path: the discretionary
  judgment is recorded reader-visibly (the rendered node carries a
  one-line `## References` affirmation: *Source's reference list
  deliberately not captured (low-value).*) and is greppable via
  `grep -l '^cited_works: IGNORED$' meta/research/*.yaml`. The value
  exists so the structural gate doesn't become a productivity block
  on edge cases; it is observed and tuned retroactively — if it
  accumulates on documents that arguably should be captured, the
  contract tightens (typed sub-enum, required justification field,
  or removal). The `cited_works_uncaptured` cross-check deliberately
  does NOT warn on `IGNORED` because signal-in-source is the
  *expected* state there.

- **non-empty list of `cited_work_entry`** — the source carries a
  reference list and it is captured below. Renders the full
  `## References` entries view. The bibliographic split fields
  (`citation_key` / `author` / optional `year` / `title`) are the
  authorship-network dimension (recurring cited authors across the
  corpus); `citation_verbatim` is the fidelity anchor that the
  `cited_works` check substring-matches against the source.

The `cited_works_uncaptured` check is the cross-check on a false
`NONE` affirmation: it WARNS when `cited_works: NONE` is set but a
reference-list signal is detected in the source's extracted text — a
likely-wrong affirmation that the contributor should re-verify (then
either capture the entries or flip to `IGNORED`). It is a backstop,
not the primary gate; the structural three-state machine carries the
load.

Structural thresholds are different and remain in force. The finding-
node creation threshold (~200 words, 3+ entity nodes, or text about
to be written into 3+ different nodes — see "Bright line — fact vs
finding" below) governs WHEN analysis should move to a
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

**Open `period_end` — ongoing vs. ended-but-undated.** An absent `period_end`
renders as just `{start}` (and an absent `period_start` as `– {end}`); it is
**not** read as "ongoing." Both a still-current role and a role known to have
ended on an unattested date legitimately lack a `period_end`, so the end-status
lives in the entry's `role` / descriptor text, not the period field: a role
known to have ended with no attested end date says so (e.g. "…; ended, end date
unattested"); a genuinely current role says "present" / "ongoing" in its
descriptor. The inverse — an attested "active-by" year used as `period_start`
when the true start is unattested — carries the same kind of role-text caveat
(e.g. "…the article-attested active-by year, not a confirmed start"). A
structured `period_*` sentinel or `ongoing` flag was considered and declined:
adding schema + renderer machinery for this edge case is over-engineering, and
the role text is the source-grounded surface that already carries the
distinction.

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
| Text-native paginated PDF (hearing transcript, government report, written testimony) whose `pdftotext` extract carries native form-feed page breaks | `p. N, ¶M` |
| Unpaginated short document (HTML article, single-page memo) | `¶N` |
| Caption / audio / video transcript | `[MM:SS]` (or `[MM:SS]–[MM:SS]` for long quotes) |
| Multi-page document where paragraph anchors aren't available — either the document lacks paragraph structure, or `pdftotext -layout` collapses visually-distinct paragraphs on a page into a single block (in which case ¶1 would overstate the precision the extract can deliver) | `p. N` |
| OCR-scan / extraction-lossy PDF whose canonical extract is a clean-text `.txt` sibling (markerless — see below) | A **descriptive content anchor** drawn from the document's own structure: a named block, section title, or reference entry — e.g. `title-page identity block`, `Administrative Note`, `section "Deuterium as the Preferred Nuclear Rocket Fuel"`, `References, entry [8]`. **Not** `p. N` — the sibling carries no page markers, so a physical-page integer can be neither read off the extract nor verified. |
| FOIA email release with a contributor-produced `.txt` sibling carrying `DOCUMENT N — header` markers. Each `DOCUMENT` block is a discrete email or threaded exchange — analogous to a page but heavier, and stable across re-extractions because the markers live in the contributor-produced sibling rather than the underlying PDF text layer. | `Doc N` for single-email documents; `Doc N, Sender YYYY-MM-DD HH:MM` for multi-email threaded exchanges. The cover letter (if quoted) uses `Cover letter, ¶M`. Email metadata that doesn't fit the location anchor (recipient, subject, importance flags) moves to `context` / `significance` where it renders as reader-visible attribution. |
| The extract itself IS the intended reference (rare; e.g., extract carries content the source PDF lacks) | `lines N-M of the extract` (the `of the extract` qualifier is required) |

**`p. N` is the physical page** — the page a PDF viewer's counter shows,
equivalently the Nth form-feed-delimited block of the `pdftotext` extract. It
is *not* the printed page number a composite document carries on its face: a
cover letter, a questions attachment, an unnumbered first page, or roman
front matter (`p. ii`) all push the printed number out of step with the
physical page, and the printed number is not mechanically recoverable from the
extract. Anchoring to the physical page makes the ref both reproducible (open
the PDF to page N) and verifiable. `extract-source.py` writes `--- page N ---`
markers at the form-feed boundaries so the physical page is read straight off
the scratch, and the `quote_location_page` check enforces it: every `p. N`
quote must sit on physical page N (the check splits the extract on form feeds
and confirms the quote text is on the cited page). The check covers every
section that carries a `p. N` ref: a **quote**'s `text` and a **naming-quirk**'s
verbatim `observed` token are both verified to be ON page N. A **timeline**
entry's `event` is a contributor paraphrase, not verbatim source text, so only
page *existence* is mechanically checkable there (page N must exist); a
timeline `p. N` that is off by a few has no verbatim anchor and rests on
contributor care.

Two companion checks enforce the ref's *form* regardless of extraction type:
`location_format` errors on a roman-numeral page ref (`p. ii`) or a `printed
p. N` dual annotation wherever a `p. N` is used (physical pages are integers;
the convention is physical-only with a node-level stated note, which the
document renderer emits), and `pdf_page_count` errors when a document's declared
`pages` ≠ the source PDF's `pdfinfo` page count. Both run on every artifact,
sibling-backed sources included.

For an **OCR-scan / extraction-lossy source** the canonical extract is the
contributor's `.txt` sibling — a clean, full-text-searchable transcription that
carries **no synthetic page markers**. *Never manufacture page structure in a
sibling* (the insert / front-matter handling is a `/prepare-ocr-sibling`
production detail; whatever a sibling transcribes, it is never delimited by an
inserted page break).

Because the sibling is markerless, a quote drawn from it does **not** carry a
`p. N` physical-page ref. A page integer can be neither read off the extract nor
verified: `quote_location_page` confirms `p. N` **only where the source's own
extraction yields form feeds natively** (text-native PDFs via `pdftotext`) and
skips a sibling-backed source **by design**. Instead the `source.location` is a
**descriptive content anchor** drawn from the document's own structure — a named
block, a section title, or a reference entry (e.g. `title-page identity block`,
`Administrative Note`, `section "Deuterium as the Preferred Nuclear Rocket
Fuel"`, `References, entry [8]`). The content anchor *is* the navigation handle
— the sibling is full-text-searchable and the PDF's pages are navigable in any
viewer — and, unlike an unverifiable `p. N`, it cannot silently drift onto the
wrong page. Page-precision was the only thing a sibling `p. N` ever offered and
it was never checked; a content anchor is self-locating and honest about what
the markerless extract supports. (Sibling-backed nodes built under the earlier
convention may still carry `p. N` refs; those remain valid — the form checks
still pass — and are not mass-migrated.)

A source that genuinely has no PDF pages uses a non-page anchor: an HTML filing
or single-page memo uses `¶N` / a section heading, an audio/video transcript
uses `[MM:SS]`, and a FOIA email release uses `Doc N` (its `DOCUMENT N` markers —
intrinsic document-collection structure, the one place a marker is *content*,
not manufactured pagination). A page-spanning quote on a text-native PDF sits on
no single page and fails the check — split it at the boundary (below).

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

**Page-spanning quotes split at the page boundary.** When a single passage runs
across a printed-page boundary, the page footer + page number + next-page header
sit wedged in the middle of the extracted text. Rather than teach the
verbatim-quote check to strip that boilerplate — which is one keystroke away
from masking the real content mismatches the check exists to catch — split the
passage into two adjacent Key Passages at the boundary, each anchored to its own
page (`p. N`, then `p. N+1`). Each quote is then ≤ one page, so no
footer/header/page-number boilerplate falls inside a quote and the verbatim
check matches cleanly. `normalize_for_compare` strips caption timestamps,
markdown block-quote markers, dashes, and whitespace (plus the conservative
form-feed-adjacent page-number strip at extraction time); it is deliberately
*not* extended to recognize page footers/headers, because boilerplate-stripping
a quote would weaken the one exactness the verbatim gate is for.

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

- **Presence/absence floors.** 100% divergence, 0% match, a token
  present-or-absent in source — these are observations, not stylistic
  judgments. The prose-drift check errors on per-token presence /
  absence: every significant token must appear in the referenced
  source, and any that doesn't is a defect — the purest uniform floor,
  binary and per token, with no aggregate percentage in between.
- **Single uniform rules across field types — including severity.**
  When a rule fires differently on different fields, the validator has
  implicitly categorized the fields; that categorization IS the bias.
  This extends to severity: a signal that is definitionally a defect
  (an ungrounded token in synthesis prose) is an ERROR on every scoped
  field and node type — not a warning on some and an error on others.
  Warn level remains appropriate only where the signal is a genuine
  per-case judgment the contributor must weigh, not a defect.

Disfavored shapes:

- Differentiated thresholds calibrated from "expected noise levels"
  observed in specific fields.
- Aggregate percentage cutoffs ("tolerate up to N% unmatched") — those
  smuggle a stylistic tolerance in as a number; the grounding floor is
  per-token presence/absence, not a percentage.
- Code or doc language like "synthesis-heavy fields tolerate higher
  unmatched rates" — that's the categorization, made explicit.

Noise-reduction extensions (stemming, whitelists, n-gram adjacency)
must apply uniformly across all scoped fields; scoping a noise-
reduction technique to "fields we expect to be synthesis-heavy"
reintroduces the category judgment in a different layer.

This is the validator-side discipline. The contributor-side
discipline (resolve every flagged token structurally, don't
rationalize it away) lives in "Prose-drift discipline on synthesis
surfaces" above. The two pair: uniform gate → rigorous resolution.

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
  an agency report's finding vs. a FOIA-released document);
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

A person stating opposing things across their own statements ("I did" /
"I didn't") is NOT a cross-source contradiction and stays on the person
node: under the `claim_group` grouping of `## Statements` (see
`quote_entry.claim_group`), the two statements sit adjacently in the same
claim group as separate verbatim quotes — both shown, no marker, no
finding. The grouping is pure organization of a single entity's own
statements; it carries no `❌`/`⚠` and no `/findings/` link. Cross-entity
contradictions (one source vs. a *different* entity's source) remain a
finding per the table above — that boundary is unchanged.

The Confirmed/Flagged binary is unchanged by contradictions —
"contradicted" is not a third status. Both sources remain confirmed
from their respective origins; the evidentiary disagreement is
documented separately.

---

## Comparability standard — same source-anchored treatment across a family

Two nodes of the same kind get built in different sessions by different
workers, and a source-anchored section one of them carries can quietly go
missing on the other — not because the second node's sources lack the material,
but because no one checked. One member of a family may carry a `## Source-Form
Notes` section its sources support while a peer that should be checked for the
same class of material never was — and nothing in the build or audit flow asked
whether it should. That gap is the failure this standard closes.

**The principle.** Members of a comparable node family receive the same
*source-anchored treatment*. When one member carries a source-anchored optional
section or dimension, every peer is obliged to be checked — at build time and at
audit time — for the same class of material against its own archived sources.
The standard governs the *checking*, never the *output*: presence stays
content-driven. A peer emits the section if and only if its sources support it.
A node whose sources attest no non-canonical name form correctly carries no
`## Source-Form Notes` section, and that is not a defect.

**Family axes.** "Comparable" means same `type`, and within type the same
`archetype` (people) or `kind` (organizations, documents, events) — the grouping
the schema already uses to decide conditional sections. No separate "family"
field exists or is needed. The `gov` organizations are one family; the
`eyewitness` people another.

**In scope — source-anchored surfaces only.** The treatment that must converge
is the evidentiary handling of source material, which surfaces as the optional
sections rendered by `scripts/build/renderers/_universal.py` plus the document
`cited_works` dimension:

- `## Source-Form Notes` (`naming_quirks[].resolution: preserve-as-sic-in-quotes`)
- `## Preserved Disagreements` (`naming_quirks[].resolution: disputed`)
- `## References` (document `cited_works` — UNIVERSAL on documents via the
  three-state affirmation NONE / IGNORED / list, see "cited_works
  affirmation" above; the comparability question shifts from "does the peer
  carry the section?" to "is the affirmation correct against the peer's
  source?")

**Out of scope — synthesis prose, and the lighter-surface node types.** The
synthesis fields (`description`, `background`, `top_relevance`,
`credibility_notes`, free-prose timeline) are never convergence candidates;
their shape is the contributor's judgment of one node's evidence, not a
cross-node obligation. Likewise the deliberate decision that document /
transcript / event / media / location nodes omit synthesis-heavy sections to
minimize prose-drift surface is correct and is not a divergence to "fix."

**This is not a count target.** Read this standard alongside `### Density is
source-driven` above. That section forbids comparison framings like "comparable
nodes have N entries; this one has fewer — anything to add?" This standard does
not reopen them. It operates one level up, on *presence-class* — whether a peer
treats a category of source material at all — not on entry counts. The correct
response to a surfaced asymmetry is to re-check the lagging node's sources for
the same class of material, and to add an entry only if a source attests it.
"Peer X has this section; add entries until this node matches" is exactly the
pressure the density rule prohibits, and it stays prohibited.

### Document-corpus extraction — the passage rubric

The same principle governs *within* a document corpus, where the unit of
divergence is not a section but a category of passage. Commissioned-program
documents built one per session drift to wide ranges in extraction density
when each worker judges "load-bearing" afresh with no shared selection rule.
The rubric below replaces that judgment with a category checklist, so density
falls out of consistent selection rather than becoming a target in its own
right.

**Slug convention for a serially-released corpus.** A node in a numbered set of
released documents (e.g. a FOIA-released set) is slugged
`{corpus}-{release#}-{short-title}` with NO date: siblings then sort and
cross-reference by release number, and inbound stub references reconcile to
that one form. The date lives in `internal_date` / the manifest, not the slug.

Every node in such a corpus captures, where the source contains it:

- **Provenance / front matter** — title, author(s), preparing organization,
  date, contract/administrative markings.
- **Thesis and scope** — the document's stated purpose and the boundary of what
  it surveys.
- **Each major section's finding** — the load-bearing claim or result of every
  numbered section, not only the summary. This is the category most often
  dropped; capturing it is what levels an under-extracted node up.
- **Methods / approach** — how the work the document characterizes was or would
  be done, where the source describes it.
- **Conclusions / recommendations** — the document's closing assessment and any
  recommended next steps.
- **Acknowledgements** — named contributors and collaborating institutions (an
  authorship-network signal).
- **References** — the formal citation list, captured as `cited_works[]` (see
  the document-artifact schema), not as `quotes[]`.

`scripts/tools/coverage-suggest.py` is the forward-coverage aid: it surfaces
substantive source paragraphs that no quote references, which the contributor
reads against this rubric to find a section finding that was skipped. The rubric
names what must be *considered*; the source still decides what is *present*. It
is not a quote-count target — a short document with few sections yields few
quotes, and that is correct.

---

## Three-layer evidentiary architecture

The repository carries three distinct evidentiary node layers sitting on
the source substrate. Each has a different role; the boundaries are
load-bearing for the discipline.

### Tier model and linking contract

Counting the source substrate, the architecture is **four tiers**.
References run **downward** — a node may reference a *lower* tier, never a
*greater* one — with exactly one same-tier exception (entity ↔ entity). This
is the directional contract: facts flow up to synthesis; synthesis never
flows back into the fact substrate.

| Tier | Node types | May reference | Must NOT reference |
|---|---|---|---|
| **1 — Sources** | archived files under `sources/` | — (the evidentiary floor; it is referenced *by* nodes and references nothing) | anything |
| **2 — Entity** | person · organization · document · event · transcript · media · location | Tier 1 (sources) **and Tier 2 (other entity nodes, laterally)** | Tier 3 (findings), Tier 4 (investigations) |
| **3 — Findings** | finding | Tier 1 (sources) + Tier 2 (entity nodes) | Tier 3 (other findings), Tier 4 (investigations) |
| **4 — Investigations** | investigation | Tier 1 + Tier 2 + Tier 3 (findings) | Tier 4 (other investigations) |

Two consequences are worth stating outright:

- **Same-tier links exist only at Tier 2.** Entity nodes cross-reference
  each other — Affiliations → org, Speakers → person, Participants → person,
  transcript `derived_from` → event — and that lateral web is the navigational
  fabric (`## Associated Nodes`). The synthesis tiers do not cross-link at
  their own level: a finding never references another finding (it stays
  cluster-neutral, citable from multiple investigations), and an investigation
  never references another investigation.
- **Nothing references a Tier-4 investigation.** It is the top of the
  iceberg — discoverable from the priority queue and inter-node paths, never
  by a lower tier pointing up at it.

A reference *up* a tier — an entity node naming a finding, a finding naming
an investigation — inverts the flow and is a defect **even in prose, even
when the target exists**: a bare-slug prose mention ("the {slug} finding")
is the same violation as a `/findings/…` path. Four checks enforce the
contract directionally, each catching both the path form and the bare-slug
form (via the finding/investigation node-slug index, `ctx.synthesis_slugs`):
`entity_no_finding_or_investigation_refs` (Tier 2 → 3/4),
`finding_no_investigation_refs` (Tier 3 → 4), `finding_no_finding_refs`
(Tier 3 → 3, same-tier), and `investigation_no_investigation_refs`
(Tier 4 → 4, same-tier). The same-tier checks exclude the node's own slug,
so a self-reference in `id` / `target_node` is not a violation.

### Entity nodes — facts

Entity nodes (people, organizations, documents, events, transcripts,
media, locations) carry **facts**: single-source attestations,
including load-bearing facts that name other entities. The fact
"witness W on transcript T named organization O as the contractor
they reported to investigators" is a fact about W — it lives on
W's person node, on T's transcript node, and (because it's
load-bearing for O) on O's organization node. Same primary source;
three entity-side fact records. None of
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

A witness on a single podcast naming a contractor = fact (one source,
one statement). A company's consistent refusal to deny across three
news outlets' inquiries over a year = finding (three sources, the
pattern is the consistency). A person authored a document
anonymously (named in a separate filing, entered into the public
record) = finding (three-source chain establishing authorship).

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

### Cross-reference contract for interview-derived testimony

When a node cites long-form media appearances as primary-source
evidence — podcasts, broadcasts, panels, conference talks,
streamed interviews — three classes of entity must appear as
`[`/path`]` body wraps somewhere in the node (typically inside the
corresponding `timeline[].event` text):

- **Venue** — the organization that hosts or distributes the
  appearance (a podcast or video show → `/organizations/{slug}`;
  a foundation's symposium → `/organizations/{slug}`).
- **Host / interviewer / moderator** — the person conducting the
  appearance (the show's host on each episode, the panel moderator
  at a symposium). Structurally distinct from the subject of the
  appearance.
- **Transcript-to-be** — the transcript node where the verbatim
  evidence will live, wrapped with its forward-looking path even
  before the transcript node is built. The broken-link registry
  surfaces the unbuilt transcript as a Phase 2 build candidate.

The body wrap is the load-bearing mechanism: `[`/path`]` wraps drive
the broken-link registry (the Priority Build Queue) and the
auto-generated `## Associated Nodes` section, both of which read the
rendered body. `coverage-suggest.py` flags source content not
reflected in the node; contributor judgment decides what is
load-bearing vs. incidental.

### Cross-reference paths to unbuilt nodes — use a stub, never null

A structured cross-reference path field — `affiliations[].organization_path`,
`relationships[].person_path`, a program / event path, any `[`/path`]` the
renderer wraps — takes the canonical `/{type}/{slug}` path **even when that
node doesn't exist yet**. A stub path is the correct value, not `null` and
not a blank: the renderer wraps it as a navigable `[`/path`]`, which joins
the broken-link registry (the Priority Build Queue) and the auto-generated
`## Associated Nodes` index. A `null` / blank path renders an empty cell
that surfaces in neither — the attested affiliation or relationship then
never becomes a build candidate and isn't navigable, dropping a real
cross-reference on the floor. For example, an institutional actor's prior
affiliation with another organization takes `/organizations/{slug}` even
with no such node built. Same body-wrap-is-load-bearing mechanism as above.

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

### Manifest shape — URL is canonical, artifacts are renderings

`sources/manifest.yaml` models each source URL as one entry. The URL
is the canonical thing being archived; the `artifacts` list under it
records each archived rendering of the URL's content.

URL-level fields describe the source itself:

- `url` — the canonical source URL
- `status` — `archived` | `403-blocked` | `402-blocked` | `pending`
- `archive_status` — 2-bit indicator: bit 0 = locally archived
  (status==archived AND artifacts non-empty); bit 1 = Wayback present
- `wayback_date` — Wayback snapshot date when bit 1 is set
- `wayback_skip: true` — URL is structurally unarchivable to Wayback
  (synthetic deep-links, session-bound URLs)
- `note` — description of the source itself

Artifact-level fields describe one archived rendering:

- `format` — `pdf` | `html` | `txt` | `audio` | `image` | `video` | `transcript`
- `path` — relative path under `sources/`
- `archived_date` — date this rendering was downloaded
- `extraction_type` — `text-native` | `ocr-scan` | `extraction-lossy`
  (applies to PDF; drives same-stem `.txt` sibling preference)
- `transcript_provenance` — `stenographic` | `published-transcript` |
  `human-corrected-caption` | `auto-caption` | `unknown` (applies to
  `format: transcript`)
- `note` — description of this specific rendering (extraction
  caveats, transcription corrections, etc.)

**Dual-artifact pattern.** A source URL whose content has been
archived twice — most commonly an audio/video URL with both the
underlying media and a derived transcript — gets ONE URL entry with
TWO entries in its `artifacts` list (e.g., `format: video` + `format:
transcript`). The transcript's `transcript_provenance` records how it
was produced from the underlying media; readers and tools can walk
the renderings under a URL to find the right one to verify against.

**`manifest.py add` semantics.** `manifest.py add URL --path PATH
--format FMT` creates a new URL entry on first call, appends a new
artifact to the existing URL entry on subsequent calls (different
paths under the same URL). Idempotent when the (URL, path) tuple
already matches an existing artifact. Errors loudly if the supplied
path is already registered under a different URL (path uniqueness
across the whole manifest).

**Invariants** enforced by
`scripts/checks/manifest_artifact_shape.py`:

1. Every URL is unique (one entry per source URL).
2. Every artifact path is unique across the whole manifest (no two
   URLs claim the same archived file).
3. `artifacts` is non-empty when `status == archived`.
4. `artifacts` is empty (or absent) when `status != archived`.

---

## Scope

The repository is a general-purpose primary-source investigation
toolkit; the schema and structure are topic-neutral. Any
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
researcher looking for `/people/{slug}.md` finds it one click in
— no `/people/{archetype-category}/{sub-category}/{slug}.md`
nesting. The frontmatter (archetype, kind, status) carries the
categorization that hierarchy would otherwise impose.

**Backend tooling** (`/scripts/`) is organized for engineering hygiene,
not researcher browsing. `/scripts/lib/` holds genuinely shared
cross-cutting helpers.

**Governance and structured-data backing** (`/meta/`) is organized
by role: `/meta/templates/`, `/meta/topic/`, `/meta/research/`. Research artifacts live under `/meta/research/`
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

### Inside `/scripts/` — six tiers by caller / role

`/scripts/` is organized by caller and role rather than by file type.
Every script lives in exactly one of six subdirectories — no Python
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
  Tools with environmental prerequisites (binaries, env vars, Python
  modules, browser session state) verify those prerequisites at
  `main()` entry rather than deferring the check until first use.
  Existing patterns vary by tool (`preflight()` in `download-video.py`,
  `ensure_tools()` in `extract-frames.py`, `_import_deps()` in
  `detect-faces.py`, inline checks at `main()` entry elsewhere); the
  load-bearing rule is fail-fast with a contributor-friendly install
  hint, not a uniform function name.
- **`/scripts/checks/`**: per-check modules — every named validator
  check (verbatim-quote, prose-drift, chronological-ordering,
  manifest-files-present, iff-section, etc.) lives at
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
  `test_stopwords.py`, `skills-check.sh`, `file-size-check.sh`,
  `cookies-check.sh`). No
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
  `extract_h2_sections`, `extract_section`).
- **`/scripts/scratch/`**: contributor landing zone for in-progress
  exploratory queries against the corpus — one-off scripts that
  answer questions like "which manifest entries lack X," "count
  nodes where archetype = Y," "find videos on disk not in the
  manifest." Contents are gitignored (`.gitignore` tracks only
  itself); the directory exists so new sessions have a known home
  for ad-hoc scripts. When a query class repeats across sessions,
  graduate it to `tools/` as a proper subcommand or standalone tool
  — the scratch tier is the bridge between zero-investment inline
  scripting and the first-class CLI surface, not a permanent home.

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
gate-only support code → `tests/`; shared helper code → `lib/`;
in-progress exploratory query → `scratch/`. The no-loose-scripts
rule (every script in exactly one subdir) keeps the top of
`scripts/` scannable as six role-labeled directories rather than a
flat heap.

### Inside `/meta/` — root vs subdirs

`/meta/` itself follows a sub-rule that grew implicitly and is
codified here. New governance items land at the tier that matches
their character:

- **Root** (`meta/conventions.md`, `meta/schema.yaml`,
  `meta/sources-access.md`, `meta/BACKLOG.md`, `meta/roadmap.md`):
  stable governance specs and forward-looking work registers — the
  rules and the active agenda. A contributor consults these at
  session start or when something on the work queue applies.
- **`meta/templates/`**: scaffolding templates, one per node type.
  Consumed mechanically by `scripts/build/new.py`; rarely read directly
  by contributors except when a new node type is being added.
- **`meta/topic/`**: topic-specific governance — the priority
  research queue, topic overview, in-progress contributor working
  notes.
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
`meta/`-direct.

`meta/README.md` is a friendly-face index of the directory's
contents; this section is the rule of record.

---

## Working notes are a report, not a residue

An agent's — or contributor's — analysis, intermediate reasoning, and
findings are a **deliverable**: handed to the user, or returned up the
build pipeline as a handoff. They are never persisted into the
repository's durable surfaces. The repo records *what the sources say*
and *what the code does*; it does not record the working process that
produced either.

Three durable surfaces, three places working notes must not land:

- **Node bodies.** A rendered node (`people/*.md`, `organizations/*.md`,
  …) is renderer output, regenerated from its `meta/research/` artifact;
  it carries source-anchored content, not an agent's commentary about how
  that content was assembled. The `block_node_body_edit.sh` hook enforces
  this mechanically — bodies are not hand-edited at all.
- **Code comments.** Comments describe what the code does and the
  non-obvious why, not who changed it or what an audit found — see
  `### NO BANDAIDS rule` and `### What TO keep in comments` below.
- **Stray files.** No scratch notes, status logs, or "summary of this
  session" files committed to the tree.

Where the record actually lives: **git history** owns the narrative of
what changed and why (commit messages, PR descriptions), and
`meta/BACKLOG.md` owns deferred work — see `### BACKLOG lifecycle
discipline`. An issue found mid-session is fixed now or filed in BACKLOG;
it is never left behind as a comment or a node-body aside.

For build work specifically, this is the mechanism the role pipeline
already runs on: each role returns a handoff stub to the orchestrator
rather than writing shared state (`prompts/topology.md`), and
`meta/memory.md` records the drive-builds-through-the-topology discipline
that keeps it that way.

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
  retirement marker, no placeholder. The commit that ships the closure
  carries the implementation diff and a message describing what
  shipped — that is the canonical record.
- IDs are positional working labels, NOT stable identifiers. A new
  entry takes the lowest section number not currently in use, so
  numbers **recycle**; when a section — and ultimately the whole
  BACKLOG — is cleared, numbering restarts from 1. An ID therefore
  must never appear outside `meta/BACKLOG.md`: not in code, docs,
  prompts, commit messages, or `git log` searches. Reference the
  work, never the ticket.
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
- schema field paths — `meta/schema.yaml` for node types, or
  `meta/schema-research-artifact.yaml` for artifact fields (e.g.
  `schema-research-artifact.yaml::conditional_keys`, merged into
  `types.research-artifact` at parse time)
- `meta/roadmap.md` mentions when scoping a "not yet implemented"
  check
- Layering invariants (e.g., "presence-guard, not truthy — opens a
  gap with `frontmatter_required` if loosened")

Anchor comments on durable concepts. Avoid anchoring on transient
ones (specific commits, dated audits, phase markers).
