---
id: meta/toolkit-notes/roadmap
type: meta
schema_version: 1
created: 2026-04-17
---

# Refactor roadmap

Top-level plan for the ground-up refactor of the UAP research repository
into a topic-neutral primary-source investigation toolkit. Preserved as
durable context so conversation-summary compaction does not lose the
outline of what's been done and what remains.

Update this file as phases complete or scopes change. The file is the
source of truth; conversation recall is not.

---

## Step 0 — Design consultation  ✅ DONE

Scope definition. Settled on:

- Topic-neutral toolkit (UAP is the first instance)
- Fresh ground-up build in `REFACTOR/`, original repo preserved
- Minimum taxonomy (orgs: gov/gov-contractor/private;
  documents: gov-doc/non-gov-doc + doc_form)
- Schema-driven validation via `meta/schema.yaml`
- Topic-specific material lives under `meta/topic/` (deleted cleanly on fork)

---

## Step A/B/C — Governance + infrastructure  ✅ DONE

### A — Schema, conventions, scripts skeleton
`meta/schema.yaml`, `meta/conventions.md`, templates under
`meta/templates/`, AGENT.md, CLAUDE.md, CONTRIBUTING.md, README.md.
Flat scripts (no shared `lib/`): `new.py`, `validate.py`, `manifest.py`,
`archive.py`, `associate.py`, `audit-schedule.py`, `build-state.py`,
`transcribe.py`.

### B — Bug fixes
- **B1** — manifest SHA256 integrity (checksum at archive-time;
  `manifest.py verify-checksums`; validator check #12)
- **B2** — `schema_version` value check against `schema.compatible_with`
  (prevents drifted-version content passing validation silently)

### C — Pilot failure postmortem
First Phase 2 pilot (2026-04-17) produced fabricated quotes and
mis-attributed claims in 10 nodes. Deleted all 10. Established four
process fixes:
- Mechanical verbatim quote verification (validator check #11)
- Source-read-first hard rule
- One-node-per-session hard rule
- Postmortem captured at `meta/toolkit-notes/pilot-failure-2026-04-17.md`

---

## Step D — Layered-process tooling  ✅ DONE (D.0 through D.7; see post-Step-D section below for the subsequent claims-layer refactor)

Three-phase build process: **Investigation → Build → Review**. Each
phase has dedicated tooling and a bounded discipline.

### D.0 — Research-artifact schema design  ✅ DONE
`meta/schema.yaml` research-artifact spec: required keys, entry shapes
per section (quotes, claims, entities_referenced, naming_quirks,
research_gaps, rumors conditional), lifecycle fields, iteration log,
validation invariants.

### D.1 — Phase I scaffolding + validation  ✅ DONE
- `scripts/research-scaffold.py` — scaffolds empty `research/{slug}.yaml`
  with type-conditional `rumors` section
- `scripts/validate-research.py` — 18 check helpers, structural
  validation only (coverage checks live in D.4)

### D.2 — Phase I source extraction + prompt  ✅ DONE
- `scripts/extract-source.py` — wraps `pdftotext` + `pdfinfo`; writes
  `/tmp/scratch-{slug}-N.txt`; batch + single modes
- `prompts/build.md` — Phase I workflow with 11 steps + 6 bounded agent
  tasks (T1–T6)

### D.3 — Phase II build  ✅ DONE
- `scripts/build-from-research.py` — deterministic regeneration from
  research artifact → node body. **Document-only scope.** Pre-flight
  validates artifact; per-section renderers; post-build validates node;
  invokes `associate.py`.
- Schema: added `description` required field, `retain_as_done` optional
  on research-gap entries.
- Existing Fravor node cleaned: removed "What This Does Not Establish"
  section.
- Prompt updated with Phase II workflow.

### D.4 — Phase III review  ✅ DONE
- `scripts/review-coverage.py` — four mechanical consistency checks
  between the regenerated node and its research artifact: Coverage
  (artifact claim/quote → node body), Boundary (node body matches
  build-from-research.py dry-run, excluding Associated Nodes),
  Stub-linking (every `entities_referenced.wrap_path` renders as a
  `[\`/path\`]` link), and OQ deduplication (Open Questions items
  map 1:1 to unresolved + retain_as_done research_gaps).
- Shipped as a sibling script (not bolted onto validate.py), confirming
  the split pattern for future check modules. Resolves BACKLOG item 2's
  deferred design decision.
- Document-type scope (matches build-from-research.py D.3); other
  types emit a skip notice. Per-type extension lands with its Phase II
  renderer (BACKLOG).
- Agent-assisted semantic review is not a separate script — documented
  in `prompts/build.md` Phase III Step 2 as a human-read pass. Bounded
  agent task (T7) is a future increment.

### D.5 — Fravor pilot rebuild  ✅ DONE
First end-to-end run of Phase I → II → III on the Fravor
written-testimony document. Populated 8 quotes / 15 claims / 20
entities / 4 naming_quirks / 4 research_gaps. All validators green:
validate-research.py, build-from-research.py (with post-build
validate.py), and review-coverage.py (all four checks). Demonstrated
that artifact-driven builds produce more accurate location refs than
hand-authored nodes (corrected ¶7→¶8 on "What is shocking") and that
the pilot-failure-era architectural guarantees hold in practice.

### D.6 — Docs + prompt updates post-pilot  ✅ DONE
Four pilot findings absorbed:
- `meta/templates/document.md` — removed redundant `## Authors`
  section. Author info lives in `document_intrinsic.authors_per_document`
  and renders as the Document Summary "Author (per document)" row.
  News and book templates keep their Authors sections (different
  authorship semantics).
- `prompts/build.md` Phase I Step 4 — `context_extrinsic.provenance[].date`
  values standardized to ISO format (YYYY-MM-DD); renderer passthrough.
- `prompts/build.md` Phase I Step 6 — quote `location` paragraph refs
  must be counted from the extracted scratch file, not from memory
  or prior prose. Pilot evidence: the ¶7/¶8 correction.
- `prompts/build.md` Phase I Step 10 — research_gap `methodology`
  should be concise; the renderer concatenates `statement — methodology`
  into a single Open-Questions line.

Two pilot observations required no action (document_intrinsic field
design solid; one-node rule held under a realistic-scope artifact).

### D.7 — Post-pilot cleanup  ✅ DONE
- `scripts/build-from-research.py` `_claim_source_cell` — dedupe
  identical location strings while preserving order (surfaced during
  the D.5 audit). Note: this helper was subsequently removed as dead
  code during the post-Step-D claims-layer refactor; dedupe is moot
  when there are no claim rows.
- Claim-anchoring discipline (Check A + Check B, shipped post-D.6)
  was the load-bearing D-era defect-prevention mechanism for the
  claims layer. It caught coarse drift reliably but not fine drift;
  see the post-Step D section below for the architectural resolution.
- Step D (D.0 through D.7) complete.

---

## Post-Step D — Claims-layer elimination for document nodes  ✅ DONE

Audit-driven architectural correction. Discovered through:
- Fravor audits (iterations i1 → i4) that kept finding the same
  shape of fine drift: c4 "intercept occurred during training" vs
  source "training was suspended," c13 dropped "and others," c6
  "at intercept" contributor framing
- Graves audit (iteration i0 → i1) that surfaced c16 "warning area"
  vs source "early warning area" and the possessive-apostrophe
  false-positive in the token extractor

Root cause: the claims layer itself. `claim.statement` was
contributor-written prose anchored to a verbatim quote, but the
prose was subject to fine drift that mechanical checks could not
catch (dropped qualifiers, synonym rephrases, word-level
condensations). A contributor-synthesis layer between source and
reader is an unavoidable drift surface *while the layer exists*.

Correction: **document nodes have no claims layer.** A document
node IS the fact record; evidentiary content is verbatim source
passages in Key Passages. Contributor prose exists only in the
Description section (explicitly labeled as synthesis). Other nodes
that cite facts from a document link to the document and reference
the specific passage — no intermediate paraphrase exists to drift.

Changes landed:
- `meta/schema.yaml` — `What This Establishes` dropped from gov-doc /
  non-gov-doc required_sections
- `meta/templates/document.md` — section removed; Key Passages is
  the sole evidentiary layer
- `scripts/build-from-research.py` — `render_what_establishes()` and
  its helpers removed as dead code (−55 lines)
- `meta/conventions.md` — new "Document nodes vs synthesis nodes"
  section; contradictions-routing table reframed (document nodes
  don't own contradictions; synthesis nodes do)
- `prompts/build.md` — Step 7 scope note (`claims: []` for documents);
  Phase II/III wording aligned
- `CLAUDE.md` / `CONTRIBUTING.md` — "`verified verbatim` claim" →
  "quote" (marker attaches only to quote-verification blocks)
- Fravor artifact → iteration i4: `claims: []`; description expanded
  to wrap the entities previously reachable only through claim prose
- Graves artifact → iteration i1: `claims: []`
- Both nodes regenerated; 0 errors / 0 warnings across the pipeline

**Synthesis nodes** (person, organization, event, finding, news,
book, location) retain claim-like sections when their analytical
purpose requires them (Claim Inventory on whistleblowers,
What The Hearing Established on hearings, etc.). Check A
(validate-research quote_ref requirement) and Check B
(review-coverage token drift) still apply to those contexts.

This is the **second architectural correction post-launch**. The
first was the 2026-04-17 pilot-failure postmortem (fabricated
verbatim quotes) which produced the validator's mechanical
verbatim-quote check. This one is deeper — it eliminates the
source-to-reader contributor-prose layer entirely for fact
documents. Both corrections came from running the pipeline against
real sources and observing the gap between what mechanical checks
can catch and what the discipline requires.

Graves written-testimony node was also built during this period
(commits 517d273 / 4d0bf8a / e24a726) — second node through the
full layered pipeline and the first built without a retrofit. The
extractor fix (single-quote false-positive) landed mid-build,
demonstrating dogfood catching a real extractor bug.

Node count after this work: 2 document nodes (Fravor, Graves), both
iterated through the full Phase I → II → III pipeline under the
claims-layer-free architecture.

---

## Post-Step D — Source-taxonomy consolidation  ✅ DONE

Design-level reconsideration of the node-type taxonomy under the
statements-only (verbatim-only) discipline established by the
prior claims-layer elimination. Driven by two observations:

- `news` and `book` node types carried contributor-synthesis sections
  (`What The Article Established`, `What The Book States`) — the same
  drift surface the claims-layer correction removed from document
  nodes. Structurally, a news article and a book are just non-gov-doc
  documents; their publication-event nature is metadata, not a
  separate node shape.
- Primary-source format coverage: the repository will archive FOIA
  documents, written testimony, congressional transcripts, news
  articles, books, photos, videos, podcasts, YouTube talks,
  documentaries, press conferences, social-media posts, and imagery
  (satellite, radar, infrared). The pre-consolidation schema handled
  text-native sources cleanly and bolted non-text sources onto
  `document` via `doc_form: video` — the wrong shape for photos
  (no text to extract) and for videos with pilot audio (speech
  belongs on a transcript).

Three evidentiary primitives drove the partition:

| Primitive | Node type |
|---|---|
| Verbatim text from a text-native source | `document` |
| Verbatim speech rendered as text from a speech-native source | `transcript` |
| Metadata + provenance of a non-text artifact (plus optional verbatim speech / visible-text extracts) | `media` |

Changes landed:
- `meta/schema.yaml` — `news` and `book` types removed; `document`
  absorbs both via `doc_form: article | book` + optional
  `archival_status` frontmatter (required when `doc_form == book`).
  Doc_form vocabulary: `video` removed (now `media`); `social-post`
  and `database-extract` added; `book-excerpt` renamed to `book`.
  `media` type added with four kinds (photo, video, audio,
  imagery-other) and required sections (Media Summary, Description,
  Provenance, Key Passages, Associated Nodes, Open Questions) plus
  optional `Media Versioning` (required when `derivation_of` is set).
  `transcript` revised: `interview` kind → `other`; optional
  `source_medium` and `derived_from` frontmatter.
- `meta/templates/` — `news.md` and `book.md` deleted; `media.md`
  added; `document.md` and `transcript.md` updated.
- Directory layout — `news/` and `books/` deleted (both empty);
  `media/` created.
- Scripts — `new.py`, `validate.py`, `build-state.py`, `manifest.py`,
  `research-scaffold.py`, `validate-research.py`, `build-from-research.py`,
  `review-coverage.py`, `associate.py` all updated for the new
  type/directory set and the conditional frontmatter checks
  (archival_status on book, Media Versioning on derivative media).
- `tests/smoke.sh` — news/book fixtures replaced with document
  article + document book + document social-post; media fixtures
  added for all four kinds; transcript fixture switched to kind
  `other`. 22/22 passing (up from 18/18).
- Docs — `AGENT.md`, `README.md`, `meta/topic/overview.md` refreshed.

Node-type count: 9 → 8 (news + book removed, media added). All
pipeline stages green after the consolidation: validate.py,
validate-research.py, review-coverage.py, build-state.py --check,
help-check.sh, smoke.sh.

Phase II renderers for non-document types (media, transcript, and the
others listed in BACKLOG "Extend build-from-research.py to all 9 node
types") will follow the new taxonomy when built — one type per
increment, as that BACKLOG item specifies.

---

## Step E — Operational tooling (split)

The original "Step E" block bundled three unrelated concerns with
different blockers and different shovel-readiness. Split into three
sub-steps so each can move independently.

### E.1 — Pre-commit / CI hook + audit-schedule wiring  ✅ DONE (2026-04-18)

Shipped in the 2026-04-18 hardening pass.

- `tests/pre-commit.sh` — chains `help-check.sh` + `smoke.sh` +
  `validate.py` + `validate-research.py` + `build-state.py --check`
  + `audit-schedule.py --overdue` into a single gate; non-zero exit
  on any failure. Install instructions in-file (contributor-driven
  install; no auto-wire — git-hook installation rewrites local git
  state and is explicit opt-in).
- `audit-schedule.py --overdue` turned out to be already operational
  (discovered during the hardening pass). Only the hook chain was
  missing; pre-commit.sh closes that gap.
- Side effect: closed the "Testing infrastructure" BACKLOG item's
  step 4 (pre-commit chain) and the audit-cadence half of the
  original Step E bundle.

### E.2 — Iteration tooling (i0 → i1 mechanics)  ⏸ MID-TERM

Blocked on: first content node reaching the i1 boundary. Today the
two document nodes are at i5 (Fravor) and i1 (Graves); but each of
those iterations was hand-authored in the research YAML with a
matching hand-appended `iterations[]` entry. The hand path works at
current volume; automation begins to pay off around ~5 artifacts at
i1+.

Scope when it ships:

- A script (`scripts/iterate.py` — name provisional) that bumps
  `last_iteration`, appends a structured `iterations[]` entry
  (trigger, summary, entries_added, entries_modified), and optionally
  re-runs build-from-research → review-coverage.
- Prompt companion: `prompts/iterate.md` (a referenced-but-unshipped
  prompt is already listed in `prompts/README.md`).

### E.3 — Cross-node update propagation  ⏸ DEFERRED

Blocked on: multiple artifacts with overlapping evidentiary claims.
Can't build propagation tooling until there's a propagation case to
build against. Likely after ~10 nodes through the full pipeline.

Scope when it ships:

- When a claim in artifact A changes the evidentiary picture for
  artifact B (claim A supersedes, contradicts, or corroborates a
  claim in B), propagate the reference bidirectionally
  (`corroborated_by`, `superseded_by`, `contradicted_by` on both
  sides, with pointers that resolve across artifacts).
- Validator coverage: broken cross-artifact refs fail validation,
  same shape as the existing intra-artifact `corroborated_by` /
  `superseded_by` / `contradicted_by` resolution check in
  `validate-research.py`.

---

## Step F — Phase II per-type renderers  ⏸ PENDING (one sub-phase at a time)

Promoted from BACKLOG ("Extend build-from-research.py to all 8 node
types"). Currently `build-from-research.py` supports `document` only;
seven other types still require hand-authored nodes, reintroducing
the fabrication surface the layered process exists to close.

**Sub-phase template.** Each F sub-phase mirrors D.3 → D.5 shape:

1. **Design pass** — resume the per-node-type analysis conversation
   (paused after the news/book collapse). What sections survive
   under the statements-only discipline? What archetype-specific
   structure does the renderer need? What metadata does the artifact
   gain?
2. **Schema delta** — revise `meta/schema.yaml` per the design pass.
   Update template, scaffolder, validator.
3. **Renderer implementation** — add type-specific section renderers
   to `build-from-research.py`. Pre-flight validates artifact;
   post-build validates node; invokes `associate.py`.
4. **Pilot** — build one node end-to-end through Phase I → II → III.
   All validators green before the sub-phase is considered shipped.
5. **Absorb pilot findings** — any doc / template / renderer
   adjustments surfaced by the pilot (same pattern as D.5 → D.6).

**One type per sub-phase. One pilot per type.** Same hard rule that
produced the 2026-04-17 pilot failure postmortem.

### F.1 — person

Decomposed into three shippable units (F.1a → F.1c).

#### F.1a — schema + template + validator + research-artifact extensions  ✅ DONE (2026-04-19)

Design pass settled the two paused threads via the "statement surface
vs cross-reference surface" lens: archetype-specific sections are
cross-reference/metadata surfaces (NOT statement surfaces), so they
stay distinct; a universal `## Statements` section (verbatim-only,
split into Direct Observations / Other Statements) is added for the
statement-surface role. A universal `## Timeline` section is added on
all person archetypes (aggregated chronological dated facts with
Category column). Changes shipped:

- `meta/schema.yaml` person type — `Key Statements` renamed to
  `Statements` with `split: [Direct Observations, Other Statements]`
  + `requires_quote_verification: true`; `Timeline` required on all
  four archetypes; `timeline_category_values` vocabulary added;
  `Timeline: {chronological: true}` section rule.
- `meta/schema.yaml` research-artifact spec — `timeline` conditional
  key on person/organization/event/finding artifacts; archetype-
  conditional keys `corroboration_items` / `program_involvement` /
  `publication_record` / `vouching_chain`; quote entry gains
  `observation_type` (required on person artifacts; `direct|relayed`)
  and optional `category`; five new entry shapes (timeline_entry,
  corroboration_entry, program_involvement_entry,
  publication_record_entry, vouching_chain_entry).
- `meta/schema.yaml` — `chronological: true` section rule added to
  `Timeline` / `Provenance` / `Ownership Timeline` on organization,
  event, document, media, location. Upgrades the flag from
  descriptive-only to enforced via check #15.
- `meta/templates/person.md` — rewritten: renamed Key Statements to
  Statements with Direct Observations / Other Statements subsections;
  added Timeline section with Category column; archetype-specific
  sections clarified as cross-reference/metadata surfaces.
- `scripts/validate.py` — check #15 (chronological-ordering) added.
  Scans every H2 section's markdown tables for date columns (Date /
  Date / Time / Period / Start / Date Captured / Date Released /
  Dates), parses dates (ISO prefix + leftmost-of-range), verifies
  ascending order. Errors on disorder; warns on unparseable cells.
  Universal across every node type.
- `scripts/validate-research.py` — archetype reader + per-archetype
  required-section check; timeline conditional; observation_type
  enum check on person-artifact quotes; five new per-section check
  helpers (check_timeline / check_corroboration_items /
  check_program_involvement / check_publication_record /
  check_vouching_chain) with enum vocabularies for
  corroboration.observation_type / evidentiary_basis / confidence.
- `scripts/research-scaffold.py` — reads target archetype from
  person frontmatter; scaffolds the matching archetype-specific
  section (corroboration_items / vouching_chain / program_involvement
  / publication_record) as an empty list; scaffolds `timeline: []`
  on timeline-bearing types.

23/23 smoke fixtures still pass; pre-commit chain fully green.

#### F.1b — Phase II renderer for person  ✅ DONE (2026-04-19)

`build-from-research.py` now supports `target_node` type `person`
alongside `document`. Ten per-section renderers driven from the
artifact fields:

- `Identity` from `document_intrinsic` (full_name / aliases /
  nationality / profession)
- `Background` / `UAP Relevance` / `Credibility Notes` from
  respective prose keys (new person-required artifact fields)
- `Affiliations` from `affiliations` list (new), split into Confirmed
  / Flagged subsections; sorted by `period_start`
- `Statements` from `quotes` filtered by `observation_type` and
  sorted ascending by `statement_date` (new optional quote field)
  into Direct Observations / Other Statements subsections
- `Timeline` from `timeline` entries, chronologically
- `Relationships` from `relationships` list (new), Confirmed / Flagged
- Archetype-specific section dispatched by frontmatter archetype:
    eyewitness          → Corroboration       (from corroboration_items)
    whistleblower       → Claim Inventory     (render-time view of
                                               quotes w/ category:
                                               filed-claim)
    institutional-actor → Program Involvement (from program_involvement)
    reporter            → Publication Record  (from publication_record,
                                               sorted)
- `Vouching Chain` — whistleblower-only; standalone H2 after
  Credibility Notes (from `vouching_chain`)

New / extended schema surface:
- `quote_entry.statement_date` (optional) — enables chronological
  sort of Statements
- Five new person-required conditional keys: `background`,
  `uap_relevance`, `affiliations`, `relationships`,
  `credibility_notes`
- `affiliation_entry` + `relationship_entry` shape specs
- Matching enforcement in `validate-research.py` (per-type and
  per-entry checks; empty placeholders tolerated)
- `research-scaffold.py` auto-populates all five on person artifacts

`review-coverage.py` accepts person artifacts; existing four checks
(Coverage / Boundary / Stub-linking / OQ dedup) generalize without
modification — quotes carry the evidentiary load on person nodes the
same way they do on documents.

All four archetypes verified end-to-end: scaffold → artifact →
build-from-research → validate → review-coverage, all clean. Pre-
commit chain 6/6 green.

#### F.1c — Fravor pilot  ✅ DONE (2026-04-19)

First end-to-end person node through Phase I → II → III under the
statements-only discipline. `/people/david-fravor` built at iteration
i0 from the Fravor written-testimony primary source:

- 6 verbatim quotes (4 direct observations of the 2004 Nimitz
  encounter; 2 relayed narratives about the post-encounter
  disclosure chain) — all verified character-for-character against
  the archived PDF by validate.py check #11
- 2 affiliations (U.S. Navy retired Commander; VFA-41 Commanding
  Officer 2004-11)
- 3 relationships (Dietrich wingman; Stratton 2009 contact; Elizondo
  2016 contact)
- 3 corroboration items (Dietrich testimonial, USS Princeton Aegis
  instrumented, FLIR1 video documentary)
- 6 timeline entries chronologically ordered (2004-11 → 2023-07-26)
- 16 entities_referenced (all rendered via backtick-bracket links
  in prose; stub-linking clean)
- 1 naming_quirk (Delonge → DeLonge, preserve-as-sic-in-quotes)
- 3 research_gaps (Navy retirement date; VFA-41 command tenure;
  full statement-set extension from oral testimony / NYT / CBS /
  podcast sources — i1 scope)

All three phases green:
  validate-research.py      0 / 0
  build-from-research.py    0 errors + post-build validate clean
  review-coverage.py        0 / 0 (Coverage / Boundary / Stub-linking /
                                   OQ dedup)

Pre-commit chain 6/6 green. 15 broken-link stubs registered in the
registry — all are Nimitz-cluster nodes not yet built (Dietrich,
Underwood, Stratton, Elizondo, 2004-nimitz-encounter event, FLIR1
video, TTSA, UCC Princeton, CVW-11, DOD, etc.). Those are Step G
work.

Pilot findings absorbed inline or no action needed:
- Renderer handled all four archetypes (F.1b) plus the real-content
  eyewitness case (Fravor) without schema or code change
- `_wrap_path` helper correctly produced backtick-bracket links for
  every cross-reference path in the rendered body
- The pre-F.1c hardening (context required on person quotes;
  document_intrinsic convention documented) made the contributor
  experience frictionless — quote population was straightforward,
  no renderer bugs surfaced

Post-F.1c audit surfaced 4 contributor-prose drift issues (RCA in
commit `f67f6e8` message) driving a pre-F.2 hardening pass —
see next section.

#### F.1c-audit hardening (pre-F.2)  ✅ DONE (2026-04-19)

RCA on the F.1c audit: the mechanical verification pipeline caught
verbatim-quote drift (check #11) but had no check verifying
contributor-authored prose fields against the source. All four drift
issues I found in the Fravor audit were in prose surfaces
(background, uap_relevance, timeline event descriptions,
relationship descriptions).

**Check #16 — prose-field token drift** shipped in
`scripts/validate-research.py`:

- For person artifacts, verify every significant word in contributor-
  prose fields (`background`, `uap_relevance`, `credibility_notes`,
  plus per-entry prose fields on timeline / affiliations /
  relationships / corroboration_items / program_involvement /
  publication_record / vouching_chain) appears in the referenced
  primary-source text.
- Significant words: lowercase tokens ≥3 chars, not in a ~110-entry
  STOPWORDS list; backtick-bracket repo paths stripped; possessive
  `'s` stripped.
- Impartial reporter: warn on every unmatched token (any field, any
  count); error only at 100% vocabulary divergence (mathematical
  floor, not stylistic threshold). Initial differentiated-threshold
  calibration (80% error) was revised to the single impartial rule
  after contributor feedback flagged the implicit synthesis-vs-
  fabrication bias in the thresholds — the validator surfaces drift
  without classifying it.
- Tier B (n-gram adjacency), lemmatization, and whitelists deferred
  to v2 per BACKLOG after ~5 person nodes accrue signal. Any v2
  additions preserve the impartial-reporter framing.

Docs updated: `prompts/build.md` Phase I Step 12 gains a prose-drift
review step; `meta/conventions.md` adds a prose-drift discipline
subsection under "Document nodes vs synthesis nodes". BACKLOG gains
the v2 extensions entry.

Fravor i1 baseline after shipping: 0 errors, 15 warnings (all
legitimate contributor-synthesis vocabulary per the RCA categories).
Fabrication test (injecting invented content): 100% unmatched
tokens → error fires correctly. Drift-restoration test (restoring
the i0 drift vocabulary): unmatched-token warnings surface each
drifted word.

### F.2 — event

Decomposed into three shippable units (F.2a → F.2c), mirroring the
F.1 pattern.

#### F.2a — schema delta + template + validator + scaffolder  ✅ DONE (2026-04-19)

Design pass settled the hearing synthesis question via the statements-
only lens established in the news/book collapse: `What The Hearing
Established` was a contributor-prose synthesis section that belongs
in the repository's navigational surface, not its evidentiary surface.
Replaced with `Witnesses & Testimony` — a cross-reference table
(witness / oath status / transcript node / written testimony node)
that routes the investigator to the verbatim record without a
paraphrase layer.

Changes shipped:

- `meta/schema.yaml`:
  - hearing kind — `What The Hearing Established` replaced with
    `Witnesses & Testimony` in required_sections
  - research-artifact spec gains `event_intrinsic` + `participants`
    on event artifacts; `witnesses_testimony` conditional on
    hearing kind; `corroboration_items` extended to also apply to
    encounter-kind event artifacts (shared entry shape with
    eyewitness person artifacts)
  - New entry shapes: `participant_entry`, `witnesses_testimony_entry`
  - New vocabulary: `VALID_PARTICIPANT_CAPACITY` and
    `VALID_OATH_STATUS`
  - Invariants block updated for the new conditional rules
- `meta/templates/event.md`:
  - `What The Hearing Established` + `What The Hearing Did Not
    Establish` sections removed; `Witnesses & Testimony` added
  - Corroboration column layout fixed per the BACKLOG entry from the
    F.1c audit: `Observer | Type | What It Confirms | Attested In`
- `scripts/validate-research.py`:
  - Target-frontmatter reader generalized (archetype + kind +
    future expansion)
  - `EVENT_REQUIRED_KEYS` required on every event artifact
  - `EVENT_KIND_REQUIRED_SECTION` rule enforces exactly one of
    witnesses_testimony (hearing) / corroboration_items (encounter)
  - `check_participants()` and `check_witnesses_testimony()` helpers
  - `corroboration_items` absent-on-other-archetypes check relaxed
    to allow encounter events to carry the section
  - Check #16 PROSE_FIELDS_BY_TYPE and PROSE_ENTRY_FIELDS_BY_TYPE
    gain event entries
- `scripts/research-scaffold.py`:
  - Reads target kind from event node frontmatter
  - Scaffolds `event_intrinsic = {}` + `participants = []` on every
    event artifact; kind-conditional section scaffolded correctly

All pre-commit gates green; Fravor person artifact unchanged (no
regression). Both event kinds scaffold + validate cleanly.

#### F.2b — event renderer in build-from-research.py  ✅ DONE (2026-04-19)

Extended `build-from-research.py` with event-type support. Per-kind
dispatch + 10 section renderers:

- `render_title_event` — prefers context_extrinsic.display_title,
  falls back to event_intrinsic.hearing_title or humanized slug
- `render_event_summary(kind)` — populates from event_intrinsic
  with per-kind field lists (hearings emit hearing_title / committee
  / session / congress / date / location / chair; encounters emit
  date / location / duration / weather / instruments_involved).
  Skips rows with empty values.
- `render_event_description` — from artifact.description
- `render_participants_encounter` — flat Confirmed/Flagged table
- `render_participants_hearing` — sub-sectioned by participant
  capacity (Witnesses — Eyewitness / Whistleblower / Institutional
  Testimony / Committee Members), plus Flagged rollup
- `render_timeline` — reused from F.1b
- `render_key_testimony` — hearing-only; verbatim block-quote +
  verification-block pairs sorted by statement_date. Reuses
  `_render_statement_block` from F.1b.
- `render_witnesses_testimony` — hearing-only; cross-reference table
  (witness / oath status / transcript / written testimony). Replaces
  the prior What The Hearing Established synthesis section.
- `render_corroboration` — shared between eyewitness person and
  encounter event. Column layout revised to Observer | Type | What
  It Confirms | Attested In (was Source | Type | What It Confirms |
  Node Link — inverted the investigator scan order). F.1c finding
  from BACKLOG closed by this revision.

Supporting changes:
- `scripts/build-from-research.py` SUPPORTED_TYPES gains `event`
- `scripts/review-coverage.py` SUPPORTED_TYPES matches
- Existing Fravor person node regenerated under the revised
  Corroboration column layout (no regression; review-coverage
  Boundary check passes against the re-rendered dry-run)

End-to-end verification: synthetic encounter artifact scaffolds +
validates + renders + passes review-coverage. Check #16 correctly
caught a test-prose-token injection (1/1 unmatched = 100% = ERROR).
Person Corroboration regeneration across the layout change was
clean.

#### F.2c — Nimitz encounter pilot  ✅ DONE (2026-04-19)

First end-to-end event node through Phase I → II → III under the F.2b
encounter renderer. `/events/2004-nimitz-encounter` built at iteration
i1 from a single archived primary source (Fravor's 2023 written
testimony):

- `event_intrinsic`: date, location, weather, 5 instruments (Aegis
  SPY-1, AN/APG-73, FLIR pod, visual, pilot HUD)
- `context_extrinsic`: display_title, primary_source_url
- `description`: 3-paragraph prose grounded in source vocabulary
- 7 participants (Fravor, Dietrich, Underwood, Princeton Aegis operator,
  VFA-41, USS Princeton, USS Nimitz)
- 9 timeline entries chronologically ordered
- 3 corroboration items (Dietrich testimonial, USS Princeton
  instrumented, FLIR1 video documentary)
- 12 entities_referenced
- 1 naming_quirk (Lue → Luis; alias-of-record, 2 source instances)
- 5 research_gaps, 3 rumors (Underwood as FLIR1 pilot; "Southern
  California" location; November 14 exact date)
- `quotes: []`, `claims: []` — encounter renderer emits no Key Testimony
  / What-This-Establishes section, so evidentiary content flows through
  structured surfaces (description + timeline + participants +
  corroboration) rather than verbatim quotes

All pipeline stages green:
  validate-research.py  0 errors / 2 warnings (both exempt timeline cells)
  build-from-research.py  0 errors + post-build validate clean
  review-coverage.py  0 / 0 (Coverage / Boundary / Stub-linking / OQ dedup)

**Pilot finding absorbed (pre-F.3 hardening — memory + contributor
policy).** User-driven scope revision on check #16 resolution policy.
i0 shipped with 4 check #16 warnings initially rationalized as
"legitimate synthesis vocabulary." Corrected to the durable contributor
policy captured in `feedback_check16_warnings_must_resolve.md`:
every warning on free-prose synthesis fields (`description`,
`background`, `uap_relevance`, `credibility_notes`) needs real
resolution — source-match rewrite or promotion to structured
evidentiary data. Timeline-cell cosmetic voice-swap warnings exempt.
i1 drove prose-field warnings to zero; 2 timeline-cell warnings
remain under the scoped exemption. Pre-F.2c roadmap anchored at
commit 305407d; policy propagation followed in the prompts/build.md
Phase I Step 12 refresh (commit f9bad12).

### F.3 — transcript  ✅ DONE (F.3a + F.3b + F.3c shipped 2026-04-19)

Two kinds after the post-Step-D revision (`hearing`, `other`). Design
pass completed in the F.2c session post-commit (2026-04-19).

**Decision 1: `derived_from` pointer — auto-populate.**
When the transcript frontmatter carries `derived_from` (path to the
underlying media or document node), the renderer emits a Publication
Record row from the frontmatter directly. Row label dispatched by path
prefix — `Underlying Media Node` for `/media/...`, `Underlying
Document` for `/documents/...`. When the field is absent, the row is
omitted (absence is its own signal; no "N/A" placeholder). Parallel
treatment for the optional `source_medium` frontmatter field —
auto-populate a Source Medium row when set. Rationale: keeps
frontmatter as the single source of truth, preserves Phase II
deterministic-render discipline, matches review-coverage Boundary
integrity, and surfaces provenance in the section where investigators
already scan for it rather than in frontmatter that requires a view
switch. No artifact field duplication needed.

**F.3c D3 refinement (2026-04-19).** Hearing transcripts vs. their
companion written testimony are independent primary records of the
same event — neither is "derived from" the other. So hearing
transcripts use `context_extrinsic.companion_written_testimony` for
the cross-reference (renders as the same "Companion Written Testimony"
PR row), and `derived_from` is reserved for transcripts where the
text record IS a rendering of an underlying media/document node
(typical: `other`-kind transcripts of podcasts / video interviews /
press conferences). The renderer keeps a `derived_from → /documents/...`
fallback path on hearing transcripts for backward compatibility, but
the convention is `companion_written_testimony`. See BACKLOG entry on
the fallback removal trigger.

**Decision 2: Material Differences — per-divergence entries with
cross-artifact quote refs.**
Each entry carries: `id`, `topic` (short descriptor), `divergence_class`
(enum: `elaboration` | `contradiction` | `omission` | `clarification` |
`qa-addition`), `written_ref` (cross-artifact reference
`{artifact: documents/<slug>, quote_id: qN}`), `oral_ref`
(intra-artifact `quote_id`), `note` (contributor synthesis; check #16
verified against the pooled source texts of both referenced quotes).
Renderer emits a table with columns Topic / Class / Written Quote /
Oral Quote / Note; quote cells show excerpted text + link to the source
node anchor, not duplicated verbatim (the full passages live in each
artifact's Key Passages section).

This is the first case requiring cross-artifact quote-ref resolution.
Validator extension scope: `validate-research.py` resolves
`{artifact, quote_id}` pointers by loading the referenced artifact and
verifying the quote_id exists in its `quotes` list; error shape
matches existing intra-artifact `quote_ref` errors. Denormalization
(copying written-quote text onto the transcript artifact) was
considered and rejected — violates single-source-of-truth and goes
stale when the document artifact's location refs are corrected.
Moving Material Differences to the hearing event node was also
considered and deferred to an architectural-threads note — justified
only when a hearing aggregates 5+ witnesses' divergences.

**F.3 sub-phase decomposition** (mirrors F.1a/b/c and F.2a/b/c):

#### F.3a — schema + template + validator + scaffolder  ✅ DONE (2026-04-19)

Schema, validator, scaffolder, template, and smoke-fixture
groundwork for hearing-transcript `material_differences` plus a
generic cross-artifact quote-ref resolver. Shipped in commit
`9217693`:

- `meta/schema.yaml` — `material_differences` conditional key
  (`required_when_target_node_type_in: [transcript]` +
  `required_when_target_node_kind_in: [hearing]`);
  `material_differences_entry` shape with 5-value
  `divergence_class` enum (elaboration / contradiction / omission /
  clarification / qa-addition); cross-artifact `written_ref`
  (`{artifact, quote_id}`) + intra-artifact `oral_ref` (quote-id
  string); optional `note` (contributor synthesis). Invariants block
  extended with three new entries.
- `scripts/validate-research.py` — `TRANSCRIPT_KIND_REQUIRED_SECTION` +
  `VALID_DIVERGENCE_CLASS` constants; target_kind read extended to
  transcript target-type; transcript-kind dispatch block mirroring
  the event-kind pattern. New generic
  `resolve_cross_artifact_quote_ref()` helper + `_load_cross_artifact()`
  cache (kept type-agnostic; reusable by Step E.3's deferred
  cross-node propagation work). New `check_material_differences()`
  helper. Check #16 extended via `_gather_material_diff_source_tokens()`
  + special-case branch in `check_prose_drift` so
  `material_differences[].note` scans against the UNION of the
  written_ref's cross-artifact quote source + the oral_ref's
  intra-artifact quote source (per the F.3 design).
- `scripts/research-scaffold.py` — `KIND_SECTIONS_BY_TYPE` nested dict
  replaces the former single-type `EVENT_KIND_SECTION`; `read_target_kind`
  generalized to cover transcripts. transcript.hearing scaffolds
  `material_differences: []`; transcript.other scaffolds no
  kind-specific section.
- `meta/templates/transcript.md` — Material Differences columns
  aligned to the design shape (Topic / Class / Written Quote / Oral
  Quote / Note) with per-column guidance.
- `tests/smoke-fixtures/` — new subdirectory with pre-built YAML
  fixtures (cross-artifact-doc.yaml, cross-artifact-trans.yaml,
  source.txt). `tests/smoke.sh` extended: cleanup trap handles
  manifest backup + fixture source-file; two new blocks exercise
  (a) scaffolder transcript-kind dispatch for hearing + other,
  (b) end-to-end cross-artifact resolver fixture standing up a
  temporary archived manifest entry with real sha256. Smoke fixture
  count 23 → 27.

Negative-path verification (not in smoke; tested during audit):
nonexistent referenced artifact, non-dict `written_ref`, unknown
`oral_ref` quote_id, invalid `divergence_class`, and note drift each
fire the expected error/warning with a clear message.

**Scope deferral absorbed to BACKLOG.** Transcript top-level
`description` field scanning by check #16 deliberately NOT added in
F.3a — blocked on F.3b's renderer design settling whether
`description` maps to `## Summary`, a new `## Description` section,
or a new `summary` artifact field replacing it. BACKLOG entry
"Transcript top-level description — check #16 prose scoping blocked
on F.3b renderer" documents the decision. Until resolved,
`material_differences[].note` is the only check #16 coverage on
transcript artifacts.

#### F.3b — Phase II renderer  ✅ DONE (2026-04-19)

Transcript support added to `build-from-research.py` in commit
`6cb131a`. Per-kind dispatch:

- Both kinds: Publication Record (auto-populated from `derived_from` +
  `source_medium` frontmatter per F.3 Decision 1), Summary (rendered
  from `artifact.description` via F.3 Q1-A field→section rename),
  Speakers (from new `speakers[]` artifact field), Key Passages
  (verbatim block-quote + verification-block pairs from `quotes[]`,
  sorted by `statement_date`, H3 per quote for navigability).
- Hearing only: Material Differences table rendered from
  `material_differences[]` — Topic / Class from entry fields; Written
  Quote and Oral Quote cells show ~150-char excerpt + anchor link to
  the source node's Key Passages section (full verbatim lives in each
  artifact's Key Passages, not duplicated). Unresolvable refs emit a
  placeholder comment cell (validator already fires the resolution
  error; renderer makes the failure visible in the body).

Supporting changes:
- `scripts/build-from-research.py` SUPPORTED_TYPES gains `transcript`;
  10 new render helpers (`render_title_transcript`,
  `render_transcript_publication_record` with kind dispatch,
  `render_transcript_summary`, `render_transcript_speakers`,
  `render_transcript_key_passages`, `render_transcript_material_differences`,
  `render_body_transcript`, `_resolve_cross_artifact_quote`,
  `_excerpt_for_table`).
- `scripts/review-coverage.py` SUPPORTED_TYPES matches; Coverage check
  handles material_differences excerpt pairs.
- `scripts/validate-research.py` — `speakers[]` required on every
  transcript artifact; `speaker_entry` shape (name req, source req,
  role/node_link/note opt); `speakers[].role` added to
  PROSE_ENTRY_FIELDS_BY_TYPE[transcript] for check #16; transcript
  top-level `description` added to PROSE_FIELDS_BY_TYPE[transcript]
  (closes the F.3a scope deferral).
- `scripts/research-scaffold.py` — transcript artifacts scaffold
  `speakers: []` on every kind.
- `meta/templates/transcript.md` — Speakers section added; Publication
  Record rows per kind; kind-conditional Material Differences.
- `tests/smoke.sh` — transcript fixtures exercise both kinds plus the
  speaker + material-differences paths. 31/31 passing.

End-to-end verification: synthetic transcript fixtures scaffold +
validate + render + pass review-coverage for both `hearing` and
`other` kinds. Check #16 transcript description scoping verified
(token-injection test; fabrication errors fire correctly).

#### F.3c — Fravor hearing-transcript pilot  ✅ DONE (2026-04-19)

First end-to-end transcript node through Phase I → II → III under the
F.3b renderer; first real-content exercise of the F.3a cross-artifact
Material Differences resolver. `/transcripts/2023-07-26-house-fravor`
built at iteration i0 from the archived 54-page stenographic PDF
(`sources/government/congress-gov-house-hearing-transcript-20230726.pdf`).
Shipped in commit `083c249`:

- 39 quotes — 19 opening-statement + 20 substantive Q&A responses
  spanning exchanges with Grothman, Burchett, Raskin, Moskowitz, Mace,
  Langworthy, Gaetz, Ogles, Biggs, Frost, and Ocasio-Cortez. All
  verified verbatim against source via validate.py check #11.
- 19 speakers — 3 witnesses (Fravor/Graves/Grusch with node_link
  wraps) + 16 Members who spoke. Role labels distinguish Subcommittee
  Members (Moskowitz/Foxx/Frost/Biggs/Mace) from Members waived-on for
  this hearing (Burchett/Luna/Gaetz/Ocasio-Cortez/Burlison/Langworthy/
  Ogles) per transcript preamble lines 158-170.
- 16 material_differences cross-referenced against
  `documents/written-testimony-fravor-2023` quotes q1-q20 — ~11
  qa-addition / ~5 elaboration. Oral-only content includes APG-73
  jamming mechanics, "Chad" named as FLIR1 crew, multi-platform radar
  tracking (Princeton + Nimitz + E2), biographical detail (enlisted
  Marine / Naval Academy / UH Master's / accident investigator), "most
  credible UFO sighting in history" framing, and motivation narrative
  (pestered by a friend).
- 19 entities_referenced, 3 naming_quirks (Leslie Keane typo preserved
  in quotes parallel to written-testimony nq1; "Lue" alias-of-record
  across 2 instances; ATIP program — disputed vs AATIP, parallel to
  written-testimony rg2), 3 research_gaps.

All three phases green:
  validate-research.py      0 / 0 (check #16 clean on description +
                                    all 16 per-entry MD notes)
  build-from-research.py    0 errors + post-build validate clean
  review-coverage.py        0 / 0 (Coverage / Boundary / Stub-linking /
                                    OQ dedup)

Pilot finding absorbed inline. `scripts/build-from-research.py`
`sort_by_date()` used raw string id as tie-breaker, lex-sorting same-
date entries (q1, q10, q11, …, q19, q2, q20, …) — Key Passages on
this transcript surfaced the bug. Fix extracts `_id_natural_key()`
from existing `sort_by_id()` and uses it as the sort_by_date tie-
breaker. Fravor transcript Key Passages now flow in narrative order
(q1 → q2 → q3 → … → q39). Fix benefits any future artifact with 10+
same-date entries in any date-sorted context.

Broken-link registry holds at 32 unbuilt-stub targets — this transcript
adds one new stub (/people/david-grusch from Fravor's q15 "Mr. Grusch
just covered that") and surfaces no new cluster-scoped priority queue
additions.

### F.4 — media  🟡 IN PROGRESS (F.4a done; F.4b/c pending)

Shipped in the source-taxonomy consolidation as a type but with no
renderer. Design pass completed 2026-04-20.

**Decision 1: Key Passages extraction — one format-flexible entry type.**
Media Key Passages cover two semantic shapes — verbatim speech (audio/
video, timestamp-located) and verbatim visible text (photo/video
legible text, spatial-coordinate-located). Rather than split the
quote entry into two schemas, a single `quote_entry` accommodates both
via a flexible `source.location` string: timestamp (`0:23-0:45`),
timestamp + in-frame coordinate (`HUD bottom-right, 0:12`), or
spatial-only (`upper-right corner`). Single entry type keeps the
schema compact and lets the contributor choose the shape that best
anchors the passage. Schema comment updated in F.4a.

**Decision 2: Media Versioning — hybrid enum + free-text observations
(Shape D).**
Per-aspect entries with a 6-value `aspect` enum (duration / encoding /
metadata / content / provenance / other) + free-text `parent_form` /
`this_form` / `source` / optional `note`. The enum provides structured
top-level filtering for future cross-node queries ("show all media
with metadata scrubs"); free-text observation cells accommodate
per-aspect shape variance (numerical for duration, list-like for
metadata, prose for content). `other` is an extensibility escape
that warns on use — signaling schema-growth discussion. Mirrors
`divergence_class` pattern from `material_differences`.

**F.4 sub-phase decomposition** (mirrors F.1a/b/c, F.2a/b/c, F.3a/b/c):

#### F.4a — schema + template + validator + scaffolder  ✅ DONE (2026-04-20)

Groundwork for the F.4b renderer. Shipped in commit `0bf04cd` +
tightening in a follow-on commit:

- `meta/schema.yaml` — `media_versioning` conditional key
  (`required_when_target_node_type_in: [media]`); `media_versioning_entry`
  shape with 6-value `aspect` enum; `quote_source.location` comment
  extended with media flexibility note (Decision 1); `document_intrinsic`
  per-type convention comment extended with media keys
  (internal_title / capture_date / duration / dimensions / file_format
  / camera_device / embedded_metadata / color_mode / codec) paired
  with context_extrinsic fields (display_title / release_date /
  primary_source_url) + primary_sources[0].path / manifest sha256
  for Local Archive / SHA256. Invariants block extended.
- `scripts/validate-research.py` — `VALID_MEDIA_VERSIONING_ASPECT`
  constant (6 values); media-type conditional enforcement (parallels
  speakers on transcript, corroboration_items on eyewitness);
  `check_media_versioning()` helper (required fields, aspect enum,
  source dict); check #16 scoping extended for media (PROSE_FIELDS
  `description`; PROSE_ENTRY_FIELDS `media_versioning.note`); new warn
  when target node has `derivation_of` set but `media_versioning` is
  empty (contributor-forgot-to-populate signal; non-blocking).
- `scripts/research-scaffold.py` — media artifacts scaffold
  `media_versioning: []` on every kind regardless of derivation_of.
- `meta/templates/media.md` — Media Versioning columns revised from
  Dimension / Parent / This Derivative / Significance → Aspect /
  Parent / This / Source / Note (Decision 2 shape) + per-column
  guidance.
- `tests/smoke.sh` — new media-type research-artifact dispatch block
  (5 cases); smoke count 31 → 36.

End-to-end verification: all 5 media-kind scaffolds scaffold + validate
clean. Derivative fixture surfaces the new "empty media_versioning
when derivation_of set" warn (non-blocking; contributor review).

#### F.4b — Phase II renderer  ⏸ NEXT

Extend `build-from-research.py` with media support. Per-kind dispatch
(photo / video / audio / imagery-other). Section renderers:

- `## Media Summary` — kind-sensitive table from `document_intrinsic`
  + `context_extrinsic` + `primary_sources[0].path` + manifest sha256.
  Fields per the document_intrinsic media convention (F.4a schema
  comment).
- `## Description` — from `description` prose.
- `## Provenance` — from `context_extrinsic.provenance` list
  (chronological custody chain).
- `## Media Versioning` — conditional on `derivation_of` frontmatter
  set. Rendered from `media_versioning[]`; columns per F.4a template.
  Emitted only when the section has at least one entry; omitted
  entirely for canonical / original media.
- `## Key Passages` — from `quotes[]`, sorted by `statement_date` with
  natural-sort tie-break; verification-block format flexible per the
  `source.location` shape (timestamp / spatial / combined).

`review-coverage.py` extension: `SUPPORTED_TYPES` gains `media`;
existing four checks (Coverage / Boundary / Stub-linking / OQ dedup)
generalize. Synthetic-fixture pilot to prove the renderer before F.4c.

#### F.4c — FLIR1 pilot  ⏸ AFTER F.4b

`/media/flir1-video` — the 90-second targeting-pod video from the
2004 Nimitz encounter. DoD publicly released in 2020; earlier leaked
versions circulated from 2017 via TTSA. Multi-version history makes
it the cleanest real-world test of the Media Versioning path.
Cockpit audio is minimal; visible on-screen HUD text is present
throughout.

Side effect: `/people/chad-underwood` identity attribution (F.3c
research_gap rg1) may resolve if the provenance chain names him.

Pilot candidate: `/media/flir1-video` (primary); alternative
`/media/gimbal-declassified` has similar structure.

### F.5 — organization  ⏸ PENDING

Under the statements-only discipline, organizations don't speak —
officials speak for them. Design pass:
- Key Personnel section is a cross-reference surface; What Is
  Confirmed / Timeline rows need source attribution per row.
- `gov-contractor` sub-kind has Primary Contracts section — artifact
  shape for contract rows (number, value, period, counterparties).

Pilot candidate: `/organizations/aaro` — current-state entity with
extensive primary-source documentation.

### F.6 — location  ⏸ PENDING

Inanimate hub. Minimal synthesis; mostly navigational.

Pilot candidate: `/locations/skinwalker-ranch` — only non-
institutional location currently on the build queue.

### F.7 — finding  ⏸ PENDING (last)

Only node type where contributor analytical prose survives post-
statements-only. Landed last so the discipline around the other
seven types is fully stable before the one synthesis surface is
ratified.

Design pass: the synthesis-section hard-anchoring rules (every
sentence in What This Establishes must be verbatim-quote-anchored to
an entry in an artifact's quote list, enforced mechanically).

No pilot candidate yet — will emerge from cross-entity patterns
observed during G (content population).

---

## Step G — Content population  ⏸ INTERLEAVED WITH F

The toolkit's purpose. Each F sub-phase's pilot is a G node; additional
G nodes in the same cluster follow once the renderer is stable.

**First cluster — 2004 Nimitz encounter.** Structurally the tightest
target: one event, three pilots, one primary media artifact, companion
transcripts, and one already-built document (Fravor written testimony).
Cluster-scope first-pass targets:

- `/events/2004-nimitz-encounter` (F.2 pilot) ✅ DONE 2026-04-19
- `/people/david-fravor` (F.1 pilot) ✅ DONE 2026-04-19
- `/transcripts/2023-07-26-house-fravor` (F.3 pilot) ✅ DONE 2026-04-19
- `/people/alex-dietrich` (follow-on; same archetype) ⏸ pending
- `/people/chad-underwood` (follow-on) ⏸ pending
- `/media/flir1-video` (F.4 pilot) ⏸ pending

Cluster-close when the ring validates cleanly against schema,
cross-references resolve in both directions, and the research-queue
broken-link registry for the cluster has drained.

The Fravor person node registers 15 broken-link stubs (Nimitz cluster
entities). Those are the build queue for the remainder of Step G's
first cluster, interleaved with F.2 (event renderer + Nimitz
encounter pilot) and F.3/F.4 as needed to unlock dependent content.

**Second cluster — candidate.** Either: 2015 Virginia Beach encounters
(parallel eyewitness cluster, Graves-anchored) OR a hearing cluster
(2023-07-26 House Oversight, a known-complete primary-source cluster).
Picked after Nimitz ships to keep the one-cluster-at-a-time discipline.

G milestones are emergent, not pre-planned. The research queue
(`meta/topic/research-queue.md`) drives additions after each cluster
closes.

---

## Architectural threads still open

Two design conversations paused mid-stride; belong under the next F
sub-phase that touches them.

- **Statements-only discipline across all synthesis nodes.**
  Post-Step-D removed the claims layer from documents; open question
  is whether the same discipline extends to the surviving
  claim-like sections on synthesis nodes (Claim Inventory,
  What The Hearing Established, What The Book States — the last
  one already resolved by collapsing book into document). Each F
  sub-phase's design pass reopens this for its type.
- **Person archetype structural collapse.** Whether the four
  archetype-specific sections (Corroboration / Vouching Chain /
  Program Involvement / Publication Record) collapse into a single
  `## Context` with archetype-selected subsections. Resolved inside
  F.1's design pass.

---

## Conventions

- ✅ = done
- 🟡 = in progress
- ⏳ = pending (next-up)
- ⏸ = deferred (not next-up)
- Phase completion = tooling ships + prompt/docs updated + smoke tests
  pass + relevant BACKLOG entries filed

Keep this file ≤ one screen per step. Long-form design notes belong
in `meta/toolkit-notes/{topic}.md` files, not here.
