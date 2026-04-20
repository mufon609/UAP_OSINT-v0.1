# Build prompt — layered three-phase process

Paste into a Claude Code session to build **one node** under the layered
Investigation → Build → Review process. **One node per session** is the
hard rule established after the 2026-04-17 pilot failure (see
`meta/toolkit-notes/pilot-failure-2026-04-17.md`).

This prompt documents all three phases: **Phase I (Investigation)**,
**Phase II (Build)**, and **Phase III (Review)**.

**Phase II scope (as of F.3b, 2026-04-19):** `build-from-research.py`
supports **document, person, event, and transcript** node types end-
to-end. Media, organization, location, and finding nodes are still
hand-authored from the research artifact pending their renderer
sub-phases (F.4 → F.7; tracked in `meta/toolkit-notes/roadmap.md`).
Until those ship, build unsupported types by hand following
`meta/conventions.md`.

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

4. **Append-only research artifacts.** Never delete entries. Use
   `superseded_by` / `contradicted_by` / `corroborated_by` to preserve
   history. New material arrives via a new iteration entry, not by
   overwriting old entries.

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

This creates `research/{slug}.yaml` with empty content sections and an
initial iteration entry (`i0`). A `rumors:` section is included only if
the target node type is `person`, `organization`, `event`, or
`location`.

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
`document_intrinsic` per the Step-A/B/C Flag 1 fix (hearing-date ≠
document-metadata).

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
Description` section. Every factual claim in the description should
be traceable to a specific artifact entry (claim, quote, or
document-intrinsic field). Treat it as a synthesis of the structured
fields below, not as new evidentiary content.

**Person artifacts carry three additional free-prose fields** beyond
`description`: `background`, `uap_relevance`, and `credibility_notes`.
These render into the matching H2 sections on person nodes and are
scanned by check #16 (prose-drift token check — see Step 12). All
four person-artifact prose fields are held to the same source-vocabulary
discipline.

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
  - Standard lifecycle fields (id, added_date, added_by_iteration: i0,
    audit_cadence_days: 365)

**Discipline:**
- Every quote is copy-pasted from the extracted text — not typed, not
  rephrased, not composited.
- Multi-line quotes use YAML literal block (`|`) so original line
  breaks are preserved character-for-character.
- **Paragraph references are counted from the extracted scratch file,
  not from memory.** The D.5 pilot corrected a ¶7/¶8 error in a
  hand-authored node this way; an extraction-based count is the
  authoritative anchor, not pre-existing prose.
- Quote text must match source exactly except for surrounding
  quotation marks (which are not part of the quoted content).

**Key Testimony / Key Passages selection — substantive over
procedural** (applies to event and transcript artifacts; lesson from
Cluster B 2023-07-26 hearing-event pilot, 2026-04-20). The Key
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

### Step 7. Populate `claims` (bounded agent task T1)

**Scope note.** `claims: []` under every current renderer. Rationale
is type-specific but the outcome is uniform:

- **Document-type nodes** — the document IS the fact record, and its
  evidentiary content is verbatim source passages in `quotes`. The
  contributor-prose claim layer was eliminated post-Step-D because
  every "fine drift" class the mechanical checks couldn't catch
  (dropped qualifiers, synonym rephrases, word substitutions)
  originated in claim prose. With claims gone, nothing can drift.
- **Person-type nodes** — the F.1b renderer emits Identity, Background,
  UAP Relevance, Affiliations, Statements (verbatim quotes), Timeline,
  Relationships, archetype-specific sections, and Credibility Notes.
  Evidentiary content flows through `quotes` (Statements section,
  Claim Inventory for whistleblowers via category filter) and
  structured list fields; `claims[]` is not rendered.
- **Event-type nodes** — the F.2b renderer emits Event Summary,
  Description, Participants, Timeline, Key Testimony (hearing only;
  from `quotes`), Witnesses & Testimony (hearing only; from
  `witnesses_testimony`), Corroboration (encounter only; from
  `corroboration_items`). `claims[]` is not rendered for either kind.

Since no current renderer emits `claims[]`, any claim populated in a
renderer-supported artifact will fail the review-coverage Coverage
check (the claim.statement won't appear in the node body). Leave
`claims: []` on all artifacts until a future renderer consumes them.

Populate `quotes` comprehensively instead — verbatim source passages
carry the evidentiary load across all currently-supported types.

For **unsupported types** (transcript, media, organization, location,
finding) awaiting their renderer sub-phases, the hand-authored node
body may still carry `## What This Establishes` or equivalent claim
sections per `meta/conventions.md`. When the renderer sub-phase for
that type ships, the claim layer's fate will be decided there (same
shape as the post-Step-D elimination for documents, or preservation as
synthesis cross-reference surfaces). The claim-requirements below
apply only to hand-authored unsupported types:

**Agent task T1 (non-document artifacts):**
- **Input:** extracted plaintext + populated `quotes`
- **Output:** YAML fragment of `claims:` entries, each with:
  - `id` (c1, c2, c3, …)
  - `statement` (one sentence; atomic factual claim the source establishes)
  - `sources` (list — paths + locations; **must include `quote_ref`** on
    at least one source)
  - `evidentiary_type` — one of `sworn-testimony` | `documented` |
    `cited` | `secondary`
  - `independently_verifiable` (optional)
  - Standard lifecycle fields

**Discipline (non-document artifacts):**
- Every claim must be anchored by `quote_ref`. If no existing quote
  supports it, add the quote first.
- Claim prose tokens must appear in the source (`review-coverage.py`
  check B).
- Limits: mechanical checks catch additions and fabrications; they do
  NOT catch dropped qualifiers or synonym rephrases. Phase III Step 2
  (semantic review) is required.

### Step 8. Populate `entities_referenced` (bounded agent task T3)

**Agent task T3:**
- **Input:** extracted plaintext + populated `quotes` + `claims`
- **Output:** YAML fragment of `entities_referenced:` — one entry per
  unique named entity (person, organization, document, event, location,
  finding) mentioned anywhere in the source or in the claims/quotes.
  Each entry:
  - `id` (e1, e2, …)
  - `entity_type` (person | organization | document | event | location | finding)
  - `name` (display name)
  - `wrap_path` (canonical repo path, e.g., `/people/jay-stratton`)
  - `context_summary` (one-line note on how this entity appears in the source)
  - `references` (list of `{quote_id: qN}` or `{claim_id: cN}` — every
    quote or claim that mentions this entity)
  - Standard lifecycle fields

**Discipline:**
- Deduplicate: one entry per entity across the whole artifact. If
  Stratton appears in ¶8 and also in a quote from ¶9, one entity entry
  with both references.
- `wrap_path` uses canonical name form even if the source uses a typo
  (the typo goes into `naming_quirks`, not here).

### Step 9. Populate `naming_quirks` (bounded agent task T4)

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

### Step 10. Populate `research_gaps` (bounded agent task T5)

**Agent task T5:**
- **Input:** everything populated so far + any contextual knowledge
  about what readers might expect vs what's in the source
- **Output:** YAML fragment of `research_gaps:` — concrete
  investigation pathways raised by this source (things it hints at but
  doesn't resolve; references to other sources worth cross-checking;
  unresolved naming questions; etc.)
  Each entry:
  - `id` (rg1, rg2, …)
  - `statement` (the question/gap in one sentence)
  - `methodology` (how to resolve — be specific, not "research more")
  - `resolved: false` (on initial build)
  - Standard lifecycle fields

**Discipline:**
- Every gap is actionable. "Archive the report Fravor mentions as
  'available on the internet'" is actionable; "Investigate UAP further"
  is not.
- Naming quirks with unresolved resolution automatically imply a
  research gap; record separately so the research_gap can be independently
  tracked/closed.
- Keep `methodology` concise (one or two sentences). The renderer
  concatenates `statement — methodology` into a single Open-Questions
  line; long multi-sentence methodologies produce unwieldy lines.
  If the methodology truly needs a paragraph of explanation, capture
  that in a linked finding node or in the target node's Description,
  and leave the research_gap methodology as the actionable pointer.

### Step 11. Populate `rumors` (bounded agent task T6, conditional)

**Only when target node type is `person`, `organization`, `event`, or
`location`.** Document nodes, transcripts, media, and findings do not
carry a rumors section.

**Agent task T6:**
- **Input:** everything populated so far + knowledge of
  widely-circulating claims about the entity
- **Output:** YAML fragment of `rumors:` — widely-reported claims that
  circulate in public discourse but lack primary-source backing in this
  artifact. Each entry:
  - `id` (r1, r2, …)
  - `claim` (the circulating claim as prose)
  - `status` (one of: `not-primary-source-established`,
    `primary-source-identified`, `primary-source-disputed`)
  - `observed_sources` (optional: where the rumor circulates)
  - `primary_source_search` (optional: where we've looked, or where to look)
  - `note` (optional)
  - Standard lifecycle fields

**Discipline:**
- A rumor is a claim that WOULD go into `claims` if a primary source
  existed. Its presence here is a fabrication-prevention mechanism:
  "this is a widely-believed claim; don't re-fabricate it into the
  node without finding a source."
- When a primary source eventually surfaces for a rumor, status
  changes to `primary-source-identified`, a new claim entry is added,
  and the rumor entry is kept as audit history.

### Step 12. Validate the research artifact

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
referring to "check #11", "Issue #3", "channel #23", numeric ordinals
like "serial #42". Fix: quote the entire value (single or double
quotes), OR rewrite without the `#`, OR use a YAML literal block (`|`)
if the content already spans multiple lines. F.4c surfaced this on
a research_gap methodology field; the pre-parse check was added to
prevent silent content loss.

**Prose-drift check #16 warnings — review before leaving Phase I.**
On person and event artifacts, the validator runs a token-drift check
across contributor-authored prose fields (top-level: `description`,
`background`, `uap_relevance`, `credibility_notes`; per-entry:
`timeline[].event`, `affiliations[].role`, `relationships[].relationship`,
`corroboration_items[].note`, `participants[].role`, and so on per
`PROSE_FIELDS_BY_TYPE` / `PROSE_ENTRY_FIELDS_BY_TYPE` in
`validate-research.py`). It flags every significant word in a prose
field that doesn't appear in the referenced primary-source text.

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
  as structured evidentiary data (naming_quirks, rumors, a
  research_gap, a timeline entry, a claim). Rationalizing warnings as
  "legitimate synthesis vocabulary" defeats the check.
- **Timeline event cells** (`timeline[].event`) — exempt from cosmetic
  source-morphology warnings (active/passive voice swaps, honorific
  substitutions) when the source-match edit reduces readability
  without adding precision. Real factual drift in a timeline cell
  (premise shift, fabrication, mis-attribution) still requires
  correction.
- **Other per-entry label fields** — contextual; consult user when
  unsure whether the timeline-style exemption applies.

Common categories of warnings and how they resolve:

- **Word-form variants** (source "prepare" vs prose "preparing";
  source "flown" vs prose "flying") → rewrite to source morphology
  on free-prose fields; exempt on timeline cells.
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
  for 2+ instances; typo for isolated misspellings). Check #16
  strips the wrap before tokenizing.
- **Acronym expansion / collapse** (source "To The Stars Academy" vs
  prose "TTSA") → use source form or introduce canonical alongside
  first occurrence with explicit parenthesis.
- **Hyphenated compounds** (source "90 second" vs prose "90-second")
  → match source.

For every warning, ask: *does this unmatched token introduce a fact
or premise the source doesn't attest?* If yes, the prose field needs
tightening. If no — the resolution is still to rewrite to source
vocabulary on free-prose fields (or document the variance
structurally). The F.1c Fravor audit (commit `f67f6e8`) and F.2c
Nimitz audit (commit `305407d`) both demonstrated the
iteration-correction pattern driven by this discipline.

### Phase I complete

At this point you have a structurally-valid, content-populated
research artifact. The narrative node is still an empty scaffold. **Do
not populate the node body in Phase I.**

---

## Phase II — Build

Deterministic transformation from research artifact → populated node
body. No creative writing in Phase II. Every line in the node body
traces to a research-artifact entry.

**Scope (as of F.3b):** document, person, event, and transcript node
types. For media, organization, location, and finding, Phase II is
still manual — follow `meta/conventions.md` and draw exclusively from
the populated research artifact. Renderer extension is tracked per-
type in `meta/toolkit-notes/roadmap.md` (F.4 → F.7).

### Step 1. Regenerate the node from its research artifact

```
python3 scripts/build-from-research.py research/{slug}.yaml
```

This:

1. Pre-flight: re-runs `validate-research.py` on the artifact and
   aborts if the artifact isn't structurally clean.
2. Renders each required H2 section from artifact data. Sections
   differ by node type:

   **Document nodes** (D.3):
   - `## Document Summary` — from `document_intrinsic` +
     `context_extrinsic` + `primary_sources[0]`
   - `## Description` — from `description`
   - `## Provenance` (gov-doc only) — from `context_extrinsic.provenance`
   - `## Key Passages` — from `quotes` (verification block per quote).
     Document nodes' sole evidentiary layer — no `## What This
     Establishes` table (see `meta/conventions.md` "Document nodes vs
     synthesis nodes").

   **Person nodes** (F.1b):
   - `## Identity` — from `document_intrinsic` (full_name, aliases,
     nationality, profession)
   - `## Background` / `## UAP Relevance` / `## Credibility Notes` —
     from respective free-prose fields
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
     tagged `category: filed-claim`) + `## Vouching Chain` (from
     `vouching_chain[]`); institutional-actor → `## Program Involvement`
     (from `program_involvement[]`); reporter → `## Publication Record`
     (from `publication_record[]`, sorted by date)

   **Event nodes** (F.2b):
   - `## Event Summary` — from `event_intrinsic`. Kind-specific fields:
     hearing emits Full Title / Convening Body / Session / Congress /
     Date / Location / Chair; encounter emits Date / Location (via
     `location_path` or `location`) / Duration / Weather /
     Instruments Involved.
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

   **Transcript nodes** (F.3b):
   - `## Publication Record` — from `context_extrinsic`. Kind-specific
     rows: hearing emits Full Hearing Title / Convening Body /
     Session / Serial No. / Date / Location / Witness / Oath Status /
     Transcript URL / Transcript Verified / Event Node / Companion
     Written Testimony; `other` emits Outlet / Program / Date /
     Host(s) / Primary Speaker(s) / Format / Source Medium /
     Underlying Media Node / Source URL / Citation Style. Auto-
     populates `Source Medium` and `Underlying X` rows from frontmatter
     (`source_medium` / `derived_from`) per F.3 Decision 1.
   - `## Summary` — from `description` (render-time field→section
     rename per F.3 Q1-A).
   - `## Speakers` — from `speakers[]` (Name / Role / Node Link
     columns).
   - `## Key Passages` — from `quotes[]`, sorted by `statement_date`
     with natural-sort tie-break on id (q1 before q10); H3 per quote
     using `significance` field.
   - **Hearing-only:** `## Material Differences` — from
     `material_differences[]` (Topic / Class / Written Quote / Oral
     Quote / Note columns). Written and Oral cells show ~150-char
     excerpts + anchor links to each artifact's Key Passages section.

   **All renderer-supported types** close with:
   - `## Associated Nodes` — placeholder; filled by `associate.py`
     (auto-generated from body `[`/path`]` links)
   - `## Open Questions / Research Gaps` — from unresolved
     `research_gaps[]` + `retain_as_done: true` resolved gaps

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

1. **Coverage** — every artifact `quotes[].text` (and
   `claims[].statement`, on synthesis artifacts that carry claims)
   appears in the node body (whitespace/punctuation normalized).
2. **Boundary** — the node body (outside `## Associated Nodes`) matches
   what `build-from-research.py --dry-run` would regenerate from the
   current artifact. Divergence means the artifact drifted from the
   node, or the node was hand-edited.
3. **Stub-linking** — every `entities_referenced[].wrap_path` appears
   as a `[`/path`]` link in the node body.
4. **OQ deduplication** — items in `## Open Questions / Research Gaps`
   map 1:1 to unresolved research_gaps (plus any `retain_as_done: true`
   resolved gaps).

Must exit 0. Fix failures by updating the **artifact** (add the missing
quote / entity / gap, or remove orphan node content; on synthesis
artifacts, add the missing claim) and re-running `build-from-research.py`
to resync. Never hand-edit the node to silence a coverage error.

### Step 2. Semantic review (agent-assisted)

Mechanical checks catch structural drift but not narrative coherence —
whether the Description reads cleanly, whether the Key Passages
collectively tell a coherent evidentiary picture, whether Open
Questions are genuinely actionable.

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

### Renderer-supported types (document, person, event)

1. `python3 scripts/validate-research.py research/{slug}.yaml` — must pass
2. `python3 scripts/build-from-research.py research/{slug}.yaml` — must
   complete cleanly (includes post-build `validate.py`)
3. `python3 scripts/review-coverage.py research/{slug}.yaml` — must pass
   (Coverage / Boundary / Stub-linking / OQ deduplication — all four checks)
4. Read the regenerated node top-to-bottom; fix any issues in the
   **artifact** (not the node) and re-run steps 2–3
5. Run the full pre-commit chain before committing:
   ```
   bash tests/pre-commit.sh
   ```
   All six gates must pass (help-check, smoke, validate, validate-research,
   build-state, audit-schedule).
6. `python3 scripts/build-state.py --update` if the commit adds, removes,
   or changes the status of a node (refreshes the CLAUDE.md build-state block)
7. Commit the research artifact + regenerated node + any manifest
   changes in one focused commit (one node per session — hard rule)

### Pending-renderer types (media, organization, location, finding)

Until the per-type renderer sub-phase (F.4 → F.7) ships:

1. `validate-research.py` passes on the populated artifact
2. Hand-author the node body per `meta/conventions.md`, drawing
   exclusively from artifact entries (no training-knowledge claims)
3. `validate.py` passes; run `associate.py` to regenerate Associated Nodes
4. Run `bash tests/pre-commit.sh` — all six gates green before commit

`review-coverage.py` currently skips unsupported artifacts with a
notice; full coverage review unlocks for each type as its Phase II
renderer lands.

---

## Bounded-agent-task summary

Each task has clear I/O and can be run as a focused agent invocation:

| Task | Input | Output |
|---|---|---|
| T1 — Extract claims *(unsupported types only; see Step 7)* | Plaintext + quotes | YAML `claims:` fragment |
| T2 — Extract quotes | Plaintext | YAML `quotes:` fragment |
| T3 — Identify entities | Plaintext + quotes + claims | YAML `entities_referenced:` fragment |
| T4 — Naming quirks | Plaintext + quotes | YAML `naming_quirks:` fragment |
| T5 — Research gaps | Everything above | YAML `research_gaps:` fragment |
| T6 — Rumors (conditional) | Everything above + external context | YAML `rumors:` fragment |

Tasks are **composable** (T3 can use T1 + T2's output). They are
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
  populate — let the references field reflect what the quotes/claims
  actually contain.
- Do not skip the validator. `validate-research.py` errors are
  commit-blocking.
