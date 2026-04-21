---
id: meta/toolkit-notes/roadmap
type: meta
schema_version: 1
created: 2026-04-17
---

# Refactor roadmap

Top-level plan for the ground-up refactor of the UAP research repository
into a topic-neutral primary-source investigation toolkit.

This file tracks **active work** and **design decisions that shaped the
current codebase** — not the detailed history of completed phases. Git
log + the code itself is the authoritative record of what shipped and
when.

---

## Active work

### F.7 — finding renderer  ⏳ PENDING (last remaining type)

Finding is the last unbuilt node type. Design pass open: decide what
synthesis section (if any) finding nodes carry under statements-only.
Options: hard-anchored claim layer (every sentence verbatim-quote-
anchored), quotes-only Key Passages parallel to documents, or a cross-
reference surface parallel to hearing Witnesses & Testimony.

No pilot candidate yet — will emerge from cross-entity patterns
observed during Step G content population.

### Step G — Content population  🟡 IN PROGRESS

Interleaves with F sub-phases — each phase pilot is a G node;
additional G nodes follow once the renderer is stable.

**Current active clusters:**

- **Cluster A — 2004 Nimitz encounter.** Event, Fravor person, Fravor
  transcript, FLIR1 media all built. Remaining: Dietrich (eyewitness),
  Underwood (eyewitness), Nimitz / Princeton / VFA-41 (orgs).
- **Cluster B — 2023-07-26 House Oversight hearing.** Complete.
  Event + 3 transcripts + 3 written testimonies + 3 witness person
  nodes all built.
- **Cluster D — UAP oversight institutions.** AARO + UAPTF built.
  Remaining: ONI (UAPTF parent), NIA (UAPTF Charter signer), Norquist
  (DSD approver), Travis Taylor (informal Chief Scientist).

G milestones are emergent, not pre-planned. `meta/topic/research-queue.md`
drives additions after each cluster closes.

### E.3 — Cross-node update propagation  ⏸ DEFERRED

Blocked on: multiple artifacts with overlapping evidentiary claims.
Can't build propagation tooling without a propagation case. Likely
after ~10 nodes through the full pipeline.

When it ships: bidirectional `corroborated_by` / `superseded_by` /
`contradicted_by` pointers resolving across artifacts; validator
coverage for broken cross-artifact refs.

---

## Architectural corrections

Four post-launch corrections shape the current design. Each came from
running the pipeline against real sources and observing a gap between
what mechanical checks catch and what the discipline requires.

### Document nodes have no claims layer (Post-Step D, 2026-04)

Audits kept finding fine drift in contributor-written `claim.statement`
prose — dropped qualifiers, synonym rephrases, word-level
condensations — that the claim-anchor check couldn't catch. Root cause:
the claims layer itself. A contributor-synthesis layer between source
and reader is an unavoidable drift surface while the layer exists.

Correction: document nodes ARE their fact record. Evidentiary content
is verbatim source passages in Key Passages. Other nodes that cite
facts from a document link to the document and reference the specific
passage. No intermediate paraphrase can drift.

**Synthesis nodes** (person, organization, event, finding, location)
retain claim-like sections when analytical purpose requires them
(Claim Inventory on whistleblowers, What The Hearing Established on
hearings, etc.).

### Source-taxonomy partition (Post-Step D, 2026-04)

`news` and `book` were separate node types carrying their own
contributor-synthesis sections (same drift surface as claims). Plus:
the pre-consolidation schema bolted non-text primary sources onto
`document` via `doc_form: video` — wrong shape for photos (no text)
and for videos with pilot audio (speech belongs on a transcript).

Partition by evidentiary primitive:

| Primitive | Node type |
|---|---|
| Verbatim text from text-native source | `document` |
| Verbatim speech rendered from speech-native source | `transcript` |
| Metadata + provenance of non-text artifact | `media` |

`news` and `book` absorbed into `document` via `doc_form: article | book`;
new `media` type with four kinds (photo, video, audio, imagery-other);
`transcript.kind: interview` → `other` to cover podcasts / press
conferences / documentaries.

### Material Differences eliminated from hearing transcripts (Post-F.3, 2026-04-20)

Hearing transcripts initially carried a per-divergence Material
Differences table comparing oral vs companion written testimony.
Cross-entity comparison between a transcript and its companion
document is synthesis — belongs on a finding node, not on either
primary record. Feature removed after the second pilot; cross-artifact
resolver machinery went with it. Rebuild when F.7 needs cross-artifact
refs under finding-node design discipline.

### Iteration log eliminated (2026-04-21)

Research artifacts tracked edits via `last_iteration` + `iterations[]`
+ per-entry `added_by_iteration`. Git already provides when / who / why
/ what-changed. The iteration log was ceremony duplicating git; summary
fields drifted into commit-message-length essays embedded in artifacts.
Removed: schema specs, validator checks, scaffolder initialization,
794 per-entry refs across 15 artifacts. Content versioning
(`superseded_by` / `contradicted_by` / `corroborated_by`) retained —
those are orthogonal to edit history.

---

## Open architectural threads

- **Statements-only across all synthesis nodes.** Post-Step-D removed
  the claims layer from documents. Open: whether the same discipline
  extends to surviving claim-like sections on synthesis nodes (Claim
  Inventory, What The Hearing Established, etc.). Each F sub-phase's
  design pass reopens this for its type.

---

## Completed phases (index)

Detailed what-shipped bullets live in git commits; this index exists
so a contributor can recognize what the phase produced.

| Phase | Status | Summary |
|---|---|---|
| Step 0 — Design consultation | ✅ | Scope definition: topic-neutral toolkit, ground-up refactor, minimum taxonomy, schema-driven validation |
| Step A — Schema, conventions, scripts skeleton | ✅ | `schema.yaml`, `conventions.md`, templates, scaffolder, validator, manifest, archive, transcribe, associate, build-state |
| Step B — Bug fixes | ✅ | B1 manifest SHA256; B2 `schema_version` value check |
| Step C — Pilot failure postmortem | ✅ | Mechanical verbatim quote verification (validator check #11), source-read-first rule, one-node-per-session rule |
| Step D — Layered-process tooling | ✅ | Phase I/II/III split: `research-scaffold.py`, `extract-source.py`, `build-from-research.py`, `review-coverage.py`, `validate-research.py` |
| Step E.1 — Pre-commit / CI hook | ✅ | `tests/pre-commit.sh` chains 5 gates (help-check / smoke / validate.py / validate-research.py / build-state.py --check) |
| Step E.2 — Iteration tooling | ❌ REMOVED 2026-04-20 | `iterate.py` planned then removed pre-implementation — git handles iteration audit at current volume |
| F.1 — person renderer | ✅ 2026-04-19 | `build-from-research.py` supports person across all 4 archetypes; Fravor pilot |
| F.2 — event renderer | ✅ 2026-04-19 | hearing + encounter kinds; Nimitz encounter pilot; Witnesses & Testimony table replaces What The Hearing Established |
| F.3 — transcript renderer | ✅ 2026-04-19 | hearing + other kinds; Fravor transcript pilot; `derived_from` auto-populates Publication Record |
| F.4 — media renderer | ✅ 2026-04-20 | photo/video/audio/imagery-other kinds; FLIR1 pilot; Media Versioning conditional on `derivation_of` |
| F.5 — organization renderer | ✅ 2026-04-20 | gov/gov-contractor/private kinds; AARO pilot; Key Personnel with leadership_class sub-grouping; Primary Contracts (gov-contractor only) |
| F.6 — location renderer | ✅ 2026-04-20 | non-institutional site type; Skinwalker Ranch pilot; ownership_timeline / uap_scope_activity / location_relationships conditional sections |

---

## Conventions

- ✅ = done
- 🟡 = in progress
- ⏳ = pending (next-up)
- ⏸ = deferred (not next-up)
- ❌ = removed / rejected
- Phase completion = tooling ships + prompt/docs updated + smoke tests
  pass + relevant BACKLOG entries filed
