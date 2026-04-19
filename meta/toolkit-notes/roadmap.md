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

#### F.1b — Phase II renderer for person  ⏸ NEXT

Extend `build-from-research.py` to support `target_node` type
`person`. Per-section renderers drive from the artifact fields:

- `Statements` renders from `quotes` filtered by `observation_type`
  and sorted chronologically within each subsection.
- `Timeline` renders from `timeline` entries, chronologically.
- Archetype-specific section renders from the matching artifact
  field (corroboration_items → Corroboration table, etc).
- `Claim Inventory` on whistleblower archetype is a render-time view
  of `quotes` tagged `category: filed-claim`.

Pre-flight validates artifact; post-build validates node; invokes
`associate.py` — same pattern as the document renderer shipped in D.3.

#### F.1c — Fravor pilot  ⏸ AFTER F.1b

First end-to-end person node through Phase I → II → III under the
statements-only discipline. `/people/david-fravor` — eyewitness
archetype; the Fravor written-testimony document is already built as
a primary source, which means Phase I has extraction-ready material.

Hard rule: one node per session.

### F.2 — event  ⏸ PENDING

Two kinds (hearing, encounter). Design pass addresses:
- Hearings — can `What The Hearing Established` survive as a
  synthesis section, or does it collapse into verbatim Key Testimony
  + cross-references? (Parallel to the news/book `What The Article
  Established` collapse.)
- Encounters — Corroboration section maps cleanly to multi-eyewitness
  observation; renderer needs to read cross-references to the people
  who observed.

Pilot candidate: `/events/2004-nimitz-encounter` — first-cluster
anchor event; multi-eyewitness (Fravor, Dietrich, Underwood);
primary sources across documents, transcripts, and media.

### F.3 — transcript  ⏸ PENDING

Two kinds after the post-Step-D revision (`hearing`, `other`).
Design pass:
- `derived_from` pointer — does the renderer auto-populate the
  Publication Record's "Underlying Media Node" row from the
  frontmatter, or leave it as a contributor-filled field?
- Material Differences section on hearings — what's the artifact
  shape for the written-vs-oral divergence entries?

Pilot candidate: `/transcripts/2023-07-26-house-fravor` — companion
transcript to the already-built Fravor written-testimony document.

### F.4 — media  ⏸ PENDING

Shipped in the source-taxonomy consolidation as a type but with no
renderer. Design pass:
- Key Passages on media has two extraction modes (audio/video speech
  + visible text in imagery) — does the artifact distinguish them in
  the `quote.source` shape, or merge?
- Media Versioning (conditional on `derivation_of`) — artifact shape
  for the parent/derivative comparison rows.

Pilot candidate: `/media/flir1-video` or `/media/gimbal-declassified`
— canonical DoD video releases with documented leaked/official
derivation history.

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

- `/events/2004-nimitz-encounter` (F.2 pilot)
- `/people/david-fravor` (F.1 pilot)
- `/people/alex-dietrich` (follow-on; same archetype)
- `/people/chad-underwood` (follow-on)
- `/transcripts/2023-07-26-house-fravor` (F.3 pilot)
- `/media/flir1-video` (F.4 pilot)

Cluster-close when the ring validates cleanly against schema,
cross-references resolve in both directions, and the research-queue
broken-link registry for the cluster has drained.

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
