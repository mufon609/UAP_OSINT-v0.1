# Build prompt — layered three-phase process

Paste into a Claude Code session to build **one node** under the layered
Investigation → Build → Review process. **One node per session** is the
hard rule established after the 2026-04-17 pilot failure (see
`meta/toolkit-notes/pilot-failure-2026-04-17.md`).

This prompt documents all three phases: **Phase I (Investigation)**,
**Phase II (Build)**, and **Phase III (Review)**.

**Phase II scope:** `build-from-research.py` supports **document,
person, event, transcript, media, organization, and location** node
types end-to-end. Only `finding` remains hand-authored pending F.7
(tracked in `meta/toolkit-notes/roadmap.md`).

---

## Hard rules

1. **One node per session.** Do not scaffold a second target while one
   is in-flight. The session ends when the one node has validated,
   been regenerated from its research artifact, passed coverage review,
   and been committed.

2. **Source-read-first.** Every claim and every quote must trace to
   text that was extracted from an archived source **in this session**.
   No claims from memory. No quotes from training knowledge.

3. **Phase discipline.** Phase I produces a populated research
   artifact. Phase II regenerates the node from the artifact.
   Phase III reviews coverage. Do not write node body content during
   Phase I. Do not update the research artifact during Phase II.

4. **Content versioning, not edit ceremony.** When new material
   contradicts or supersedes an existing entry, use `superseded_by` /
   `contradicted_by` / `corroborated_by` pointers — preserve the
   original entry and add the new one alongside. Edit history itself
   lives in git log / git diff, not in the artifact.

---

## Prerequisites

Before starting, confirm:

- The **target node** is known (path: `{type}/{slug}`, e.g.,
  `documents/written-testimony-fravor-2023`)
- The target node's **narrative file exists** as an empty scaffold
  (via `python3 scripts/new.py …`). Create it first if needed.
- All **primary sources are archived locally** in `sources/{category}/`
  and registered in `sources/manifest.yaml`. If new sources are needed,
  archive them via `python3 scripts/manifest.py add …` before Phase I
  begins.
- The research artifact is either **absent** (will be scaffolded in
  step 1 below) or **exists in initial-scaffold state** with no content
  (will be populated in this session).

If any prerequisite is unmet, stop and fix before proceeding.

---

## Phase I — Investigation workflow

### Step 1. Scaffold the research artifact (if not yet scaffolded)

```
python3 scripts/research-scaffold.py --target {type}/{slug} \
    --sources {comma-separated-source-paths-relative-to-sources/}
```

This creates `research/{slug}.yaml` with empty content sections.
A `rumors:` section is included only if the target node type is
`person`, `organization`, `event`, or `location`.

Validate the scaffold passed its structural checks:
```
python3 scripts/validate-research.py research/{slug}.yaml
```

Should exit 0 (passes, zero content but structurally valid).

### Step 2. Extract every primary source to plaintext

```
python3 scripts/extract-source.py --artifact research/{slug}.yaml
```

This writes `/tmp/scratch-{slug}-0.txt`, `/tmp/scratch-{slug}-1.txt`,
etc. — one per primary source. PDF metadata is printed to stdout for
immediate review (useful for populating `document_intrinsic`).

**Rule:** every subsequent Phase I step references these extracted
files. If a claim or quote is not traceable to text in a scratch file,
it does not belong in the research artifact.

### Step 3. Populate `document_intrinsic`

For each primary source, scan the extracted text for facts the
**document itself states about itself**:

- `internal_title` — title printed in the document
- `internal_date` — date printed inside (often absent; leave null if so)
- `classification` — marking on the document (`unclassified`, etc.)
- `classification_markings_on_document` — what's literally printed
- `authors_per_document` — list of names the document identifies as authors
- Other fields as appropriate per source type

These are **only things readable from the document's own content**.
PDF metadata from Step 2 (author/date from pdfinfo) can inform
`document_intrinsic` but PDF metadata is often set by authoring-software
boilerplate — verify against document content when using.

### Step 4. Populate `context_extrinsic`

Contextual metadata **from outside the document** — e.g., hearing date,
committee name, event node, submitted-to authority. Distinct from
`document_intrinsic` (hearing-date ≠ document-metadata — the hearing
date is external context, not a fact the document states about itself).

Fields used by `build-from-research.py` when rendering document nodes
(add the ones you have; omit the rest):

- `display_title` — node H1 title and Summary-table Title row
- `hearing_date` — Summary-table Hearing Date row
- `primary_source_url` — original upstream URL
- `quote_attribution` — string used as each Key Passage's
  "Attributed to" field (typically `"{Speaker}, {occasion}, {date}"`)
- `provenance` — list of custody-chain steps; each step is a dict with
  `step`, `date`, `entity`, `verified` keys. Rendered as the
  Provenance table (gov-doc nodes only). **`date` values use ISO
  format (`YYYY-MM-DD`)** — the renderer passes them through verbatim;
  ISO keeps provenance sortable and unambiguous across documents.

### Step 5. Populate `description` (and other free-prose fields)

A 1-3 paragraph prose summary that renders as the node's `##
Description` section on document / transcript / media / event /
organization / finding / location nodes. Every factual claim in the
description should be traceable to a specific artifact entry (quote or
document-intrinsic field). Treat it as a synthesis of the structured
fields below, not as new evidentiary content.

**Person artifacts — `description` is optional and not rendered.**
The person body renderer (`render_body_person`) emits Background,
UAP Relevance, and Credibility Notes from dedicated prose fields;
it never calls `render_description`. Any content in a person
artifact's `description` is unrendered. Either leave the field empty
(or absent — validator is type-conditional) or use it as a brief
index-level summary that never reaches the node body. Evidentiary
prose for a person node belongs in `background` / `uap_relevance`
/ `credibility_notes`. Each of those is scanned by the prose-drift
check (see Step 10) against the pooled primary-source vocabulary.

Future plan (tracked in `BACKLOG.md`): move to agent-generated
descriptions so the evidentiary-derivation invariant is enforced
mechanically. For now: hand-write with discipline — across every
free-prose field, not just `description`.

### Step 6. Populate `quotes` (bounded agent task T2)

**Agent task T2:**
- **Input:** extracted plaintext scratch file(s)
- **Output:** YAML fragment of `quotes:` entries, each with:
  - `id` (q1, q2, q3, …)
  - `text` (literal block `|` preserving exact line structure)
  - `source` (`path` + `location`, e.g., `location: "¶2"` or `"line 807"`)
  - `significance` (one-line note on why the quote matters)
  - `context` — e.g., "opening statement" / "Q&A" / "appendix" /
    "written testimony, House Oversight Committee". **Required on
    person artifacts** (the renderer composes it into the Attributed-to
    line of the verification block); optional on document / transcript
    / media where the source document itself carries the context.
  - `observation_type` (`direct` | `relayed`) — **required on person
    artifacts**. `direct` = first-hand sensory observation by the person
    (e.g., Fravor's "I saw a Tic Tac"). `relayed` = anything else the
    person asserted — things heard, inferred, read, published,
    relayed from others. Drives the Statements section split (Direct
    Observations vs Other Statements). Ignored on non-person artifacts.
  - `statement_date` (`YYYY-MM-DD`; `YYYY-MM` or `YYYY` tolerated) —
    optional. On person artifacts, drives the Statements section's
    chronological sort within each subsection (earliest first). On
    hearing-event artifacts, drives Key Testimony sort.
  - `category` (optional free-text tag) — e.g., `filed-claim` on
    whistleblower artifacts so the Claim Inventory renderer can filter.
  - Standard lifecycle fields (id, added_date).

**Discipline:**
- Every quote is copy-pasted from the extracted text — not typed, not
  rephrased, not composited.
- Multi-line quotes use YAML literal block (`|`) so original line
  breaks are preserved character-for-character.
- **Paragraph references are counted from the extracted scratch file,
  not from memory.** An extraction-based count is the authoritative
  anchor, not pre-existing prose.
- Quote text must match source exactly except for surrounding
  quotation marks (which are not part of the quoted content).
- **HTML entity preservation.** When quoting from HTML sources
  (press releases, congressional committee pages, news articles),
  pdftotext / the `.html` reader preserves HTML entities verbatim in
  the scratch file — `&nbsp;` between sentences, `&#39;` for
  apostrophes, `&amp;` for ampersands. The mechanical verbatim-quote
  check compares byte-for-byte, so the quote text in the artifact
  must include the literal entities. Either: (a) preserve the entity
  in the `text` field, or (b) shorten the quote span to avoid the
  entity. Do not silently convert entities to their decoded
  characters.
- **OCR artifact preservation.** FOIA'd PDFs often contain OCR damage
  — dropped characters (`ovember` for `November`, `AGE CY` for
  `AGENCY`), hyphen-split line breaks (`fulfi lled` for `fulfilled`),
  unexpected capitalization (`identifYing`), transposed letters
  (`Unidenlified` for `Unidentified`), and typos (`chaner` for
  `charter`). The scratch file shows exactly what the validator sees;
  quote text must match those artifacts byte-for-byte. Do not
  "correct" the source in the quote; log the divergence as a
  `naming_quirk` if the artifact is meaningful (name misspelling,
  alternate form worth preserving).
- **Wrap paths outside quoted spans.** When adding
  `[`/path/to/entity`]` wraps alongside entities named inside a
  double-quoted span in prose fields (description / background /
  credibility_notes), place the wrap OUTSIDE the closing quote, not
  inside. Inside-quote wraps get stripped by the description-drift
  check, leaving orphan `()` that breaks the substring match. Ex:
  `Name ([`/people/...`])  "quoted source text…"` (wrap before
  the quote) — NOT — `"Name ([`/people/...`]) quoted source text…"`
  (wrap inside).

**Key Testimony / Key Passages selection — substantive over
procedural** (applies to event and transcript artifacts). The Key
Testimony section of a hearing event (and the analogous Key Passages
section of a hearing transcript) should highlight distinctive
evidentiary moments — the claims that make this hearing worth
archiving — not procedural scaffolding. Avoid selecting:
- Convening / adjournment / gavel timings (already captured by
  `event_intrinsic.start_time` / `end_time` and the Timeline section)
- Oath administration ("Please raise your right hand…") and witness
  affirmations ("I do") (already captured by
  `witnesses_testimony[].oath_status: sworn`)
- Routine procedural exchanges (recognizing a Member, yielding time,
  submitting for the record) unless the procedural act itself is
  evidentiarily novel (e.g., unanimous-consent to classify)

Prefer quotes that surface: the specific factual claims witnesses
assert, the strongest corroborations or contradictions between
witnesses, the most-cited moments from post-hearing press coverage,
the moments where a Member articulates a bipartisan frame or closing
assessment that's quotable beyond the hearing itself. Procedural
evidentiary weight lives in the structural fields; free the Key
Testimony section to be the highlights reel.

**Event-level Key Testimony may duplicate transcript/document Key
Passages.** An event stands as a self-contained highlights reel —
investigators landing on the event node expect to see what was said
without clicking through. Quote overlap with the witness-specific
transcript or document nodes is acceptable and expected; the
renderer does not deduplicate across nodes.

### Step 7. Populate `entities_referenced` (bounded agent task T3)

**Agent task T3:**
- **Input:** extracted plaintext + populated `quotes`
- **Output:** YAML fragment of `entities_referenced:` — one entry per
  unique named entity (person, organization, document, event, location,
  finding) mentioned anywhere in the source or in the quotes.
  Each entry:
  - `id` (e1, e2, …)
  - `entity_type` (person | organization | document | event | location | finding)
  - `name` (display name)
  - `wrap_path` (canonical repo path, e.g., `/people/jay-stratton`)
  - `context_summary` (one-line note on how this entity appears in the source)
  - `references` (list of `{quote_id: qN}` — every quote that mentions
    this entity)
  - Standard lifecycle fields

**Discipline:**
- Deduplicate: one entry per entity across the whole artifact. If
  Stratton appears in ¶8 and also in a quote from ¶9, one entity entry
  with both references.
- `wrap_path` uses canonical name form even if the source uses a typo
  (the typo goes into `naming_quirks`, not here).
- **Do not include the artifact's own subject.** `entities_referenced`
  lists entities OTHER than the node's subject. Person nodes don't
  self-wrap; including the subject (e.g., David Fravor on
  `/people/david-fravor`) creates a spurious Stub-linking check
  failure. The subject's identity is carried by the node body itself
  (Identity section on person; equivalent surfaces elsewhere). The
  `review-coverage.py` Stub-linking check auto-filters self-references,
  so a mistaken self-entry will not error out, but the convention is
  to omit it.

### Step 8. Populate `naming_quirks` (bounded agent task T4)

**Agent task T4:**
- **Input:** extracted plaintext + populated `quotes`
- **Output:** YAML fragment of `naming_quirks:` — one entry per
  observed spelling/naming oddity that differs from canonical form.
  Each entry:
  - `id` (nq1, nq2, …)
  - `observed` (as written in source)
  - `canonical` (corrected form)
  - `location` (where in source)
  - `source_path` (manifest path of the source)
  - `resolution` (one of: `preserve-as-sic-in-quotes`, `use-canonical`,
    `disputed`, `unresolved`)
  - `note` (optional)
  - Standard lifecycle fields

**Discipline:**
- If a typo is found in a passage that appears as a verbatim quote
  in `quotes`, the quote preserves the typo and the naming_quirk
  resolution should be `preserve-as-sic-in-quotes` so rendered node
  prose knows to use canonical form outside the quote.

### Step 9. Populate `rumors` (bounded agent task T5, conditional)

**Only when target node type is `person`, `organization`, `event`, or
`location`.** Document nodes, transcripts, media, and findings do not
carry a rumors section.

**Agent task T5:**
- **Input:** everything populated so far + knowledge of
  widely-circulating claims about the entity
- **Output:** YAML fragment of `rumors:` — widely-reported claims that
  circulate in public discourse but are either unconfirmed or refuted
  by the artifact's primary sources. Each entry:
  - `id` (r1, r2, …)
  - `claim` (the circulating claim as prose)
  - `status` — one of:
    - `not-primary-source-established` — no primary source attests;
      artifact-only fabrication-prevention record. Does not render.
    - `primary-source-disputed` — primary sources actively refute the
      rumor. Renders into a `## Primary-Source Contradictions`
      section on the node body; the `note` field is the primary-
      source refutation text.
  - `observed_sources` (optional: list of where the rumor circulates
    — renders as the "Circulates in" line for disputed rumors)
  - `note` (optional — for disputed rumors this is the refutation;
    for not-established it's contributor context)
  - Standard lifecycle fields

**Discipline:**
- A rumor is a widely-circulated claim without primary-source backing
  in this artifact. Its presence here is a fabrication-prevention
  mechanism: "this is a widely-believed claim; don't re-fabricate it
  into the node without finding a source."
- When a primary source eventually confirms a `not-primary-source-
  established` rumor, graduate it to a real `quotes[]` entry with the
  source, and delete the rumor (git log preserves it). Don't keep
  stale confirmed rumors.
- When primary sources refute a rumor, set `status: primary-source-
  disputed` and populate `note` with the refutation text — the
  renderer surfaces it to investigators.

### Step 10. Validate the research artifact

```
python3 scripts/validate-research.py research/{slug}.yaml
```

Must exit 0 before leaving Phase I. Any errors must be corrected by
going back to the appropriate step above.

**YAML `#` comment-truncation warnings.** If the validator emits a
warn of the form `line N: value contains \` #\` followed by
substantive content`, an unquoted scalar value in the artifact
contains a `space #` sequence — YAML silently treats everything after
`#` as a comment and truncates the scalar. Common triggers: prose
referring to "Issue #3", "channel #23", numeric ordinals
like "serial #42". Fix: quote the entire value (single or double
quotes), OR rewrite without the `#`, OR use a YAML literal block (`|`)
if the content already spans multiple lines.

**Prose-drift check warnings — review before leaving Phase I.**
The validator runs a token-drift check across contributor-synthesis
prose fields on every renderer-supported type (top-level free prose:
`description`, `background`, `uap_relevance`, `credibility_notes`;
per-entry synthesis content notes: `ownership_timeline.note`,
`uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
`media_versioning.note`, `vouching_chain.attestation`). See
`PROSE_FIELDS_BY_TYPE` / `PROSE_ENTRY_FIELDS_BY_TYPE` in
`validate-research.py` for the per-type scope. It flags every
significant word in a scoped prose field that doesn't appear in the
referenced primary-source text.

**Validator behavior — impartial reporter.** The check surfaces every
unmatched token as a warning. The validator makes no classification
about whether an unmatched token is "legitimate synthesis" or "real
drift" — that's the contributor's call per field. Errors fire only
at 100% vocabulary divergence (complete mismatch — prose shares no
significant words with the source it claims to draw on), a
mathematical floor on pure fabrication. Below 100%, the validator
reports without judgment.

**Contributor policy — resolve every warning structurally** (per
durable memory `feedback_check16_warnings_must_resolve.md`). Each
warning requires real resolution, not synthesis-acceptance:

- **Free-prose synthesis fields** (`description`, `background`,
  `uap_relevance`, `credibility_notes`) — zero warnings is the target.
  Resolve each unmatched token by either (a) rewriting to use source
  vocabulary exactly, or (b) capturing the source-vs-prose variance
  as structured evidentiary data (naming_quirks, rumors, a timeline
  entry, a new quote). Rationalizing warnings as "legitimate synthesis
  vocabulary" defeats the check.
- **Per-entry synthesis content notes** — `ownership_timeline.note`,
  `uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
  `media_versioning.note`, and `vouching_chain.attestation`. These
  are multi-sentence narrative / analytical prose about an event /
  transaction / role / derivation; zero warnings is the target, same
  resolution paths as free-prose fields.
- **Structural labels + cross-reference descriptor notes** are NOT
  scanned by the prose-drift check. This includes role titles, short relationship
  descriptors, `timeline[].event`, `use_status`, `activity`, and the
  `.note` fields on cross-reference entries (`corroboration_items`,
  `witnesses_testimony`, `org_relationships`,
  `location_relationships`) that describe *why/how a cross-reference
  exists*. Token-matching is a poor instrument for compact multi-
  source labels and meta-descriptors. Fabrication in these cells is
  caught by Phase III semantic review, not the prose-drift check.

Common categories of warnings and how they resolve:

- **Word-form variants** (source "prepare" vs prose "preparing";
  source "flown" vs prose "flying") → rewrite to source morphology
  on in-scope fields (free-prose + `.note`).
- **Repo-conventional naming** (source "Statement" vs prose "written
  testimony"; source "took" vs prose "captured") → rewrite to source
  vocabulary on free-prose fields. Repo filename conventions
  (`written-testimony-*.md`) do not license substituting those
  conventions into content prose.
- **Source-vs-canonical naming variance** (source "Lue Elizondo" vs
  canonical "Luis Elizondo"; source "Keane" vs canonical "Kean") →
  two-step: use source form in prose wrapped in the canonical link
  path (`Lue Elizondo ([`/people/luis-elizondo`])`); log the variance
  in `naming_quirks` with a note on what it means (alias-of-record
  for 2+ instances; typo for isolated misspellings). The prose-drift
  check strips the wrap before tokenizing.
- **Acronym expansion / collapse** (source "To The Stars Academy" vs
  prose "TTSA") → use source form or introduce canonical alongside
  first occurrence with explicit parenthesis.
- **Hyphenated compounds** (source "90 second" vs prose "90-second")
  → match source.
- **Typographic dashes** (em-dash `—` and en-dash `–`) — no action
  needed. `extract_significant_tokens` normalizes U+2014 and U+2013
  to ASCII hyphen before tokenization, matching the conversion that
  `validate.py:normalize_for_compare` already does for the verbatim-
  quote check. Prose written with ASCII hyphen (`F-18`) tokenizes
  identically to source rendered with en-dash (`F–18`). Applies to
  the prose-drift check only; verbatim-quote text still needs to
  match the source character byte-for-byte (the verbatim-quote check
  has its own normalization path).

For every warning, ask: *does this unmatched token introduce a fact
or premise the source doesn't attest?* If yes, the prose field needs
tightening. If no — the resolution is still to rewrite to source
vocabulary on free-prose fields (or document the variance
structurally).

### Phase I complete

At this point you have a structurally-valid, content-populated
research artifact. The narrative node is still an empty scaffold. **Do
not populate the node body in Phase I.**

---

## Phase II — Build

Deterministic transformation from research artifact → populated node
body. No creative writing in Phase II. Every line in the node body
traces to a research-artifact entry.

**Scope:** document, person, event, transcript, media, organization,
and location node types. Only `finding` remains hand-authored —
follow `meta/conventions.md` and draw exclusively from the populated
research artifact. Renderer extension tracked in
`meta/toolkit-notes/roadmap.md` (F.7).

### Step 1. Regenerate the node from its research artifact

```
python3 scripts/build-from-research.py research/{slug}.yaml
```

This:

1. Pre-flight: re-runs `validate-research.py` on the artifact and
   aborts if the artifact isn't structurally clean.
2. Renders each required H2 section from artifact data. Sections
   differ by node type:

   **Document nodes:**
   - `## Document Summary` — from `document_intrinsic` +
     `context_extrinsic` + `primary_sources[0]`
   - `## Description` — from `description`
   - `## Provenance` (gov-doc only) — from `context_extrinsic.provenance`
   - `## Key Passages` — from `quotes` (verification block per quote).
     Document nodes' sole evidentiary layer — no `## What This
     Establishes` table (see `meta/conventions.md` "Document nodes vs
     synthesis nodes").

   **Person nodes:** (order follows `render_body_person`)
   - `## Identity` — from `document_intrinsic` (full_name, aliases,
     nationality, profession)
   - `## Background` — from `background` prose field
   - `## UAP Relevance` — from `uap_relevance` prose field
   - `## Affiliations` (Confirmed/Flagged split) — from `affiliations[]`,
     sorted by `period_start`
   - `## Statements` (Direct Observations / Other Statements split) —
     from `quotes[]` filtered by `observation_type` and sorted by
     `statement_date`
   - `## Timeline` — from `timeline[]` (chronological, Category column)
   - `## Relationships` (Confirmed/Flagged split) — from `relationships[]`
   - Archetype-specific section (dispatched by frontmatter `archetype`):
     eyewitness → `## Corroboration` (from `corroboration_items[]`);
     whistleblower → `## Claim Inventory` (render-time view of quotes
     tagged `category: filed-claim`); institutional-actor →
     `## Program Involvement` (from `program_involvement[]`); reporter →
     `## Publication Record` (from `publication_record[]`, sorted by
     date)
   - `## Credibility Notes` — from `credibility_notes` prose field
   - **Whistleblower only:** `## Vouching Chain` — from
     `vouching_chain[]` (standalone section rendered after Credibility
     Notes, not part of the archetype-dispatcher)

   **Event nodes:**
   - `## Event Summary` — fact table from `event_intrinsic`. Kind-
     specific row lists are inline in `render_event_summary` (hearing
     vs encounter) — see the function for exact labels and order.
     Empty values skipped.
   - `## Description` — from `description`
   - `## Participants` — from `participants[]`. Hearings: sub-sections
     by `capacity` (Witnesses — Eyewitness Testimony / Whistleblower
     Testimony / Institutional Testimony / Committee Members) +
     Flagged rollup. Encounters: flat Confirmed/Flagged table.
   - `## Timeline` — from `timeline[]`
   - **Hearing-only:** `## Key Testimony` (verbatim `> blockquote` +
     verification-block pairs from `quotes[]`, sorted by
     `statement_date`) + `## Witnesses & Testimony` (cross-reference
     table from `witnesses_testimony[]` — witness / oath status /
     transcript / written testimony)
   - **Encounter-only:** `## Corroboration` (from `corroboration_items[]` —
     same shape as eyewitness person)

   **Transcript nodes:**
   - `## Publication Record` — fact table from `context_extrinsic`.
     Kind-specific row lists are inline in
     `render_transcript_publication_record` (hearing vs other) — see
     the function for exact labels and order. The `Source Medium`
     row and the `Underlying Media Node` / `Underlying Document` row
     auto-populate from frontmatter (`source_medium` /
     `derived_from`); the Underlying row label adapts based on
     whether `derived_from` points at `/media/` or `/documents/`.
     Empty values skipped.
   - `## Summary` — from `description` (render-time field→section
     rename: `description` stays the universal top-level field while
     the rendered section name fits transcript semantics).
   - `## Speakers` — from `speakers[]` (Name / Role / Node Link
     columns).
   - `## Key Passages` — from `quotes[]`, sorted by `statement_date`
     with natural-sort tie-break on id (q1 before q10); H3 per quote
     using `significance` field.

   **Media nodes:**
   - `## Media Summary` — fact table from `document_intrinsic` +
     `context_extrinsic` + `primary_sources[0]` + manifest sha256
     lookup. Row list is inline in `render_media_summary` — see the
     function for exact labels and order. The Duration/Dimensions row
     label adapts to what's populated (combined when both present,
     either alone otherwise — typical for video / audio / photo
     respectively). Empty values skipped.
   - `## Description` — from `description`
   - `## Provenance` — from `context_extrinsic.provenance`
   - `## Media Versioning` — conditional; emits when artifact has
     entries OR frontmatter has `derivation_of` set. From
     `media_versioning[]` (Aspect / Parent / This / Source / Note).
     Placeholder row when `derivation_of` is set + entries empty
     (validator warns non-blockingly).
   - `## Key Passages` — from `quotes[]`. Flexible `source.location`
     strings: timestamp (`0:23-0:45`), timestamp + in-frame coordinate
     (`HUD bottom-right, 0:12`), or spatial-only (`upper-right
     corner`). Section is permitted empty when the source has no
     extractable speech or visible text.

   **Organization nodes:**
   - `## Overview` — fact table from `document_intrinsic` per-kind
     keys. Per-kind row order from `_ORG_OVERVIEW_ORDER_BY_KIND`
     (`gov` / `gov-contractor` / `private`); row labels from
     `_ORG_OVERVIEW_LABELS`. The `gov` key set covers agency/office
     fields plus military-unit and military-service sub-shape fields.
     See `build-from-research.py` for exact field lists. Empty values
     skipped.
   - `## Description` — from `description`
   - `## Key Personnel` (Confirmed/Flagged split) — from
     `key_personnel[]`, sub-grouped by `leadership_class` (Directors /
     Deputy Leadership / Other Named Personnel); empty sub-subsections
     suppressed; sorted by `period_start` within each sub-group.
   - `## Key Passages` — from `quotes[]` (verbatim excerpts about the
     org; parallels document Key Passages but subject-about-org
     rather than doc-as-subject).
   - **gov-contractor only:** `## Primary Contracts` — from
     `contracts[]` chronologically by `period_start`, with
     deliverables sub-list per entry.
   - `## Timeline` — from `timeline[]` (chronological)
   - `## Relationships` (Confirmed/Flagged split) — from
     `org_relationships[]`

   **Location nodes:**
   - `## Overview` — fact table from `document_intrinsic` location
     keys. Row order from `_LOCATION_OVERVIEW_ORDER`; row labels from
     `_LOCATION_OVERVIEW_LABELS`. Status row sourced from frontmatter
     (not `document_intrinsic`) and rendered as the final row. Rows
     with empty values skipped.
   - `## Description` — from `description`
   - `## Ownership Timeline` — from `ownership_timeline[]`,
     chronological by `period_start`. Columns: `Period | Owner |
     Use / Status | Source`.
   - `## UAP-Scope Activity` — from `uap_scope_activity[]`,
     chronological by `period_start`. Columns: `Period | Activity |
     Source`. When entries have `actor_paths` populated, the wraps
     are appended inline to the Activity cell with an em-dash
     separator (no separate column).
   - `## Key Passages` — from `quotes[]` (verbatim excerpts about the
     location; parallels document / organization Key Passages but
     subject-about-location). H3 per quote using `significance`.
   - `## Relationships` (Confirmed/Flagged split) — from
     `location_relationships[]`. Columns: `Entity | Relationship |
     Node Link`. Heterogeneous `entity_path` (people / organizations
     / events / media / adjacent locations / findings).

   **All renderer-supported types** close with:
   - `## Primary-Source Contradictions` — **conditional, person /
     event / organization / location only.** Emits when the artifact
     has any `rumors[]` entry with `status: primary-source-disputed`.
     Each disputed rumor renders as an H3 with its `claim` text, a
     `Circulates in:` line (from `observed_sources`), and a
     `Primary-source refutation:` line (from `note`). Omitted when
     no disputed rumors exist or the node type doesn't carry rumors
     (document / transcript / media).
   - `## Associated Nodes` — placeholder; filled by `associate.py`
     (auto-generated from body `[`/path`]` links)

3. Preserves the node's existing frontmatter verbatim.
4. Writes the regenerated body to `{type}/{slug}.md`, overwriting the
   previous body.
5. Invokes `scripts/associate.py {node}` to rewrite Associated Nodes.
6. Post-build: re-runs `validate.py` on the regenerated node (quote
   verbatim check, section structure, etc.). Exits non-zero if
   validation fails.

Use `--dry-run` to render to stdout without writing. Use
`--no-validate` to skip pre-flight and post-build validators (for
debugging only — never when committing).

### Step 2. Read the regenerated node

After regeneration, open the node file and read it top-to-bottom.
The validators check structure; they do not check that a human would
read the node and find it coherent. If anything looks wrong
(misrendered field, bad table alignment, missing content the artifact
should have produced), the fix goes into the **artifact**, not the
node. Re-run `build-from-research.py` and re-read.

### Phase II complete

The node passes `validate.py` (including mechanical quote-verbatim
verification against the archived source). No hand-edits to the node
body have been made. Every line traces to a research-artifact entry
or to the frontmatter.

---

## Phase III — Review

Mechanical consistency checks between the regenerated node and its
research artifact. Runs last — assumes Phase I and Phase II have passed.

### Step 1. Run the coverage checker

```
python3 scripts/review-coverage.py research/{slug}.yaml
```

The script runs four mechanical checks:

1. **Coverage check** — every artifact `quotes[].text` appears in the
   node body (whitespace/punctuation normalized).
2. **Boundary check** — the node body (outside `## Associated Nodes`)
   matches what `build-from-research.py --dry-run` would regenerate
   from the current artifact. Divergence means the artifact drifted
   from the node, or the node was hand-edited.
3. **Stub-linking check** — every `entities_referenced[].wrap_path`
   appears as a `[`/path`]` link in the node body.
4. **Description-drift check** — every significant token in the node's
   `## Description` section appears in the artifact's grounding text
   (source + `context_extrinsic` + `document_intrinsic` +
   `naming_quirks.canonical` + `entities_referenced.name`). Catches
   fabricated entities and abbreviation expansions that don't trace
   to grounding.

Must exit 0. Fix failures by updating the **artifact** (add the missing
quote / entity, correct description prose to match grounding) and
re-running `build-from-research.py` to resync. Never hand-edit the
node to silence a coverage error.

### Step 2. Semantic review (agent-assisted)

Mechanical checks catch structural drift but not narrative coherence —
whether the Description reads cleanly, whether the Key Passages
collectively tell a coherent evidentiary picture.

After `review-coverage.py` passes, read the regenerated node
top-to-bottom. For any issue: fix the **artifact**, not the node.
Re-run `build-from-research.py` and `review-coverage.py`.

No dedicated prompt for this pass yet — planned as a bounded agent
task (T7) in a later increment.

### Phase III complete

All four mechanical checks pass, and a human read of the regenerated
node surfaces no semantic issues. Ready to commit.

---

## End-of-session procedure

### Renderer-supported types (document, person, event, transcript, media, organization, location)

1. `python3 scripts/validate-research.py research/{slug}.yaml` — must pass
2. `python3 scripts/build-from-research.py research/{slug}.yaml` — must
   complete cleanly (includes post-build `validate.py`)
3. `python3 scripts/review-coverage.py research/{slug}.yaml` — must pass
   (Coverage / Boundary / Stub-linking / Description-drift — all four checks)
4. Read the regenerated node top-to-bottom; fix any issues in the
   **artifact** (not the node) and re-run steps 2–3
5. Run the full pre-commit chain before committing:
   ```
   bash tests/pre-commit.sh
   ```
   All five gates must pass (help-check, smoke, validate, validate-research,
   build-state).
6. `python3 scripts/build-state.py --update` if the commit adds, removes,
   or changes the status of a node (refreshes the CLAUDE.md build-state block)
7. Commit the research artifact + regenerated node + any manifest
   changes in one focused commit (one node per session — hard rule)

### Pending-renderer type (finding)

Until the F.7 renderer ships:

1. `validate-research.py` passes on the populated artifact
2. Hand-author the node body per `meta/conventions.md`, drawing
   exclusively from artifact entries (no training-knowledge claims)
3. `validate.py` passes; run `associate.py` to regenerate Associated Nodes
4. Run `bash tests/pre-commit.sh` — all five gates green before commit

`review-coverage.py` currently skips finding artifacts with a notice;
full coverage review unlocks when the F.7 renderer lands.

---

## Bounded-agent-task summary

Each task has clear I/O and can be run as a focused agent invocation:

| Task | Input | Output |
|---|---|---|
| T2 — Extract quotes | Plaintext | YAML `quotes:` fragment |
| T3 — Identify entities | Plaintext + quotes | YAML `entities_referenced:` fragment |
| T4 — Naming quirks | Plaintext + quotes | YAML `naming_quirks:` fragment |
| T5 — Rumors (conditional) | Everything above + external context | YAML `rumors:` fragment |

Tasks are **composable** (T3 can use T2's output). They are
**validated by humans** before being merged into the research artifact.
They are **bounded** — each task produces a specific YAML fragment, not
free-form content.

---

## What NOT to do

- Do not populate node body content during Phase I.
- Do not write quotes from memory — extract from scratch file.
- Do not rephrase source text in quotes (only paraphrase in
  `significance` or `context_summary` fields).
- Do not create a research artifact for a node that doesn't exist yet.
- Do not hand-edit `entities_referenced[].references` after agents
  populate — let the references field reflect what the quotes
  actually contain.
- Do not skip the validator. `validate-research.py` errors are
  commit-blocking.
