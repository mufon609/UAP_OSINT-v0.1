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
Options: quotes-only Key Passages parallel to documents, or a cross-
reference surface parallel to hearing Witnesses & Testimony.

No pilot candidate yet — will emerge from cross-entity patterns
observed during Step G content population.

### Step G — Content population  🟡 IN PROGRESS

Interleaves with F sub-phases — each phase pilot is a G node;
additional G nodes follow once the renderer is stable.

**Current active clusters:**

- **Cluster A — 2004 Nimitz encounter.** Event, Fravor person, Fravor
  transcript, FLIR1 media, Dietrich person all built. Remaining:
  Underwood (FLIR1 pilot / corroborator), Nimitz / Princeton / VFA-41
  (orgs), and 19 Dietrich-interview stubs (CBS News + Whitaker + five
  podcast orgs and hosts + Linda Hall + AVC + seven interview
  transcripts).
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

Five post-launch corrections shape the current design. Each came from
running the pipeline against real sources and observing a gap between
what mechanical checks catch and what the discipline requires.

### Statements-only across all node types (2026-04-21)

Audits kept finding fine drift in contributor-written `claim.statement`
prose — dropped qualifiers, synonym rephrases, word-level
condensations — that the claim-anchor check couldn't catch. Root cause:
the claims layer itself. A contributor-synthesis layer between source
and reader is an unavoidable drift surface while the layer exists.

Correction shipped in two waves:
- **Wave 1 (Post-Step D, 2026-04):** document nodes lose their claims
  layer; evidentiary content is verbatim Key Passages only.
- **Wave 2 (2026-04-21):** the `claims[]` shape is eliminated repo-
  wide. `quotes[]` becomes the universal evidentiary primitive
  across all node types. Every rendered "claim-like" surface is a
  filtered view of `quotes[]` (Claim Inventory on whistleblowers =
  quotes tagged `filed-claim`; Key Testimony on hearings = quotes
  sorted by date; Key Passages elsewhere = all quotes).

Cross-entity synthesis (patterns spanning 3+ nodes) goes on finding
nodes (F.7) — a node-level structure, not an artifact-level data
layer.

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

### Cross-script lockstep helpers extracted to `scripts/lib/_common.py` (2026-05-01)

`validate.py`, `validate-research.py`, and `review-coverage.py` share a
load-bearing guarantee per `meta/conventions.md`: the verbatim-quote
check, prose-drift check, and description-drift check must see the
same source bytes under the same normalization. The guarantee was
enforced by in-script `# Mirror validate.py exactly` comments plus
contributor discipline. The discipline failed empirically — features
shipped to `validate.py` without parallel updates (HTML entity decode;
YouTube caption timestamp strip 2026-04-22; OCR-scan / extraction-
lossy `.txt` sibling preference 2026-04-24 per BACKLOG #19 Phase F
Tier 1; HTML tag cleanup) and the divergence was invisible to
pre-commit gates.

Correction: extracted `extract_source_text`, `normalize_for_compare`,
`clean_html_for_text` (and `_load_extraction_types`, caches,
`_HTML_INLINE_TAGS`) into `scripts/lib/_common.py`. The three scripts
import; the lockstep is mechanical. Refactor surfaced one real
contributor drift hidden by corrupted pdftotext output (Grusch
transcript description "himself"), cleared 5 binary-source advisory
warnings via format-aware silent-skip on `image | video | audio`,
and added `.json` to the read-as-text extension list.

The refactor also clarified the previously-implicit flatness rule:
investigator-facing content layers stay flat; tooling layer follows
engineering hygiene. See `meta/conventions.md` "Repository layout" for
the codified rule.

---

## Open architectural threads

- ~~**Statements-only across all synthesis nodes.**~~ **Closed
  2026-04-21.** The claims[] shape was eliminated repo-wide;
  `quotes[]` is now the universal evidentiary primitive across every
  node type. Claim Inventory survives as a render-time filter on
  quotes tagged `filed-claim`, not a separate data structure.

---

## Completed phases (index)

Detailed what-shipped bullets live in git commits; this index exists
so a contributor can recognize what the phase produced.

| Phase | Status | Summary |
|---|---|---|
| Step 0 — Design consultation | ✅ | Scope definition: topic-neutral toolkit, ground-up refactor, minimum taxonomy, schema-driven validation |
| Step A — Schema, conventions, scripts skeleton | ✅ | `schema.yaml`, `conventions.md`, templates, scaffolder, validator, manifest, archive, transcribe, associate, build-state |
| Step B — Bug fixes | ✅ | B1 manifest SHA256; B2 `schema_version` value check |
| Step C — Pilot failure postmortem | ✅ | Mechanical verbatim-quote check, source-read-first rule, one-node-per-session rule |
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
