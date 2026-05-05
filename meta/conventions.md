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
equivalent-footing sources once confirmed. The inclusion bar does
not vary by medium: every quote, whether extracted from a PDF, an
HTML page, a stenographic transcript, or a captioning file, must
appear in the cited source. No marker variant, no different
verification path, no renderer special-casing.

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
(`description`, `background`, `uap_relevance`, `credibility_notes`)
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
`uap_relevance` / `credibility_notes` paragraphs, and per-entry
synthesis content notes (`ownership_timeline.note`,
`uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
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

Entity nodes cited by a finding carry a short summary (1–3 sentences) +
link back to the finding, not the full narrative. The finding node is
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

Investigator-facing content layers are flat by design:
`/people/`, `/organizations/`, `/documents/`, `/events/`, `/transcripts/`,
`/media/`, `/locations/`, `/findings/`, and `/research/` each hold
single-level `slug.md` (or `slug.yaml`) files. `/sources/` is flat
within each category subdirectory. A researcher looking for
`/people/david-grusch.md` finds it one click in — no `/people/whistleblowers/intelligence-community/david-grusch.md` nesting.
The frontmatter (archetype, kind, status) carries the categorization
that hierarchy would otherwise impose.

Backend tooling (`/scripts/`, `/meta/`, `/tests/`) is organized for
engineering hygiene, not researcher browsing. `/scripts/lib/` holds
genuinely shared cross-cutting helpers; `/meta/templates/`,
`/meta/topic/`, `/meta/toolkit-notes/` group governance docs by role.
The flatness rule is about content the investigator reads, not about
files the toolkit maintainers edit. Don't extrapolate the
content-layer rule onto the tooling layer — and don't extrapolate
tooling-layer organization onto the content layer.
