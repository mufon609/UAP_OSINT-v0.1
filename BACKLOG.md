---
id: BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

---

## Open items

### 1. Validator is not version-aware

When a file declares `schema_version: 2`, `validate.py` applies the
current `meta/schema.yaml` rules regardless. B2 enforces version
*labels* against `compatible_with`; it does not dispatch to
version-specific rule sets. A real v1 → v2 migration will need
per-version rule dispatch (approaches: version-keyed schema sections,
split `schema.{version}.yaml` files, or translation layer in the
validator). Not urgent until first real migration is planned.

Surfaced: B2 (2026-04-17).

---

### 2. `validate.py` is trending monolithic

`scripts/validate.py` is **1294 lines** (past the 800-line trigger)
and mixes ~7 concerns in one file. Future check additions compound
the growth.

**Refactor plan** (sibling-script pattern, proven by
`review-coverage.py` + `validate-research.py` + `manifest.py
verify-checksums`): keep `validate.py` as orchestrator + `Issue`
class + report formatting; extract per-category checkers into
sibling scripts (`check-sources.py`, `check-quotes.py`,
`check-structure.py`). Each independently runnable.

Trigger fired 2026-04-20 at 1197 lines; grew to 1294 since. Actionable.

---

### 3. Unit tests for check functions

End-to-end coverage shipped (`help-check.sh`, `smoke.sh`,
`pre-commit.sh`). Function-level unit tests remain open — quote
normalization, checksum computation, verification-block parsing,
`evaluate_condition` parser. Most valuable alongside the monolith
refactor (item 2), where extraction makes functions naturally testable.

Surfaced: Step A/B/C audit (2026-04-17).

---

### 4. F.1a enforcement gaps

Two F.1a schema additions are declarative but not mechanically
enforced:

1. **`timeline_category_values`** — person-timeline Category column
   enum isn't checked. A row with `Category: banana` passes.
   Proposed: extend `check_chronological_tables` to warn on unknown
   values. Low priority (field is advisory metadata, not evidentiary).

2. **Statement-block chronological ordering** — the chronological-ordering
   check enforces ordering inside a single markdown table, but `## Statements`
   renders as a sequence of `> block quote` + verification-table
   pairs. Chronological order across those pairs isn't verified from
   the node body alone. Renderer-driven pipelines can't drift (F.1b
   sorts at render time); hand-authored person nodes could drift
   silently. Gap only matters if hand-authored person nodes are
   built (not on the roadmap).

Surfaced: F.1a audit (2026-04-19).

---

### 5. Display-name lookup in cross-reference cells

Renderer emits cross-reference paths as backtick-bracket wraps
(``[`/organizations/aaro`]``) in table cells. An investigator reads
"us-navy" instead of "U.S. Navy". Look up display name from
`entities_referenced.name` (matching `wrap_path`) or target node
frontmatter. Low urgency — paths render as clickable links.

Surfaced: F.1b audit (2026-04-19).

---

### 6. Honor `optional_sections` as an allowlist

`optional_sections` on the media type is informational — no script
reads it. Schema keys that look load-bearing but aren't are a drift
vector. Promote to an allowlist for an unknown-section warning pass
(warns on an H2 section that's not in `required_sections`,
`optional_sections`, or a corpus addendum).

Surfaced: source-taxonomy consolidation audit (2026-04-18).

---

### 7. Extend manifest `format_values` for audio and image sources

`manifest_entry.format_values` is `[pdf, html, txt, post, video,
transcript]`. Media kinds `audio` and `photo` are first-class per
schema but the manifest vocabulary hasn't kept pace. First audio-only
or image-only primary source will force the `--format` escape hatch
(silent manifest-entry drift).

**Fix on trigger** (first audio or image archival):
1. Add `audio` + `image` to `manifest_entry.format_values`
2. Update `FORMAT_BY_EXT` in `manifest.py` + `infer_format` in
   `research-scaffold.py` (`.mp3/.wav/.flac/.aac/.ogg/.m4a` → `audio`;
   `.jpg/.jpeg/.png/.gif/.tiff/.webp/.bmp/.heic` → `image`)
3. Extend `extract_source_text` in `validate.py` with audio/image
   passthrough (warn-on-unextractable, matches current .mp4 behavior)

Surfaced: F.4c FLIR1 pilot (2026-04-20).

---

### 8. Committee Members sub-grouping in hearing-event rendering

F.2b hearing renderer emits Committee Members as a flat table with
role text embedding leadership status ("Subcommittee Chair (R-WI)",
"Ranking Member (D-TX)"). Flat read is accurate but hides hierarchy.

**Fix on trigger** (second hearing-event artifact — retrofit cost
stays low while count is low): add optional `leadership_role` enum
field to `participant_entry` (`subcommittee-chair`, `ranking-member`,
`full-committee-chair`, `member`, `observer`); renderer sub-groups by
it. Free-text `role` stays as the display cell.

Surfaced: Cluster B hearing-event pilot (2026-04-20).

---

### 9. Rename `finding` → `investigation` + redesign type

Mechanical rename plus a design pass. The `finding` type will be
renamed to `investigation`; the redesign will decide what synthesis
surface an investigation node carries (the Open Questions / Research
Gaps section was removed 2026-04-21 — investigations are the intended
home for that kind of material).

**Rename surfaces** (mechanical):
- `meta/schema.yaml` — `types.finding` block + ~6 enum-list references
- Scripts — `DIRS` maps, `TIMELINE_TYPES`/`RUMORS_TYPES` sets,
  `new.py` argparse, `validate.py` `node_type == "finding"` branch
  (total: 8 scripts)
- `meta/templates/finding.md` → `investigation.md`
- `/findings/` directory (currently empty) → `/investigations/`
- Top-level docs — README, AGENT, CONTRIBUTING, conventions, overview,
  research-queue

**Redesign pass** (design decision deferred):
- What sections does an investigation node carry under the
  statements-only discipline? Options: quotes-only Key Passages
  parallel to documents, or a cross-reference surface parallel to
  hearing Witnesses & Testimony. See roadmap "F.7" section.
- Incorporate the investigation-pathway material that used to live in
  `research_gaps[]` (what readers expect from an active research
  thread: concrete methodology, cross-node scope, resolution state).

Surfaced: OQ removal (2026-04-21) — the rename was deliberately
deferred to a later session rather than bundled with the removal.

---

### 10. Replace Phase II Step 1 field enumerations with renderer-pointer refs

**Context.** `prompts/build.md` Phase II Step 1 documents what each
renderer emits per node type. For most subsections, the per-kind row
labels and field orders are enumerated explicitly — e.g., the
Organization Overview subsection lists gov / gov-contractor / private
field orderings; Media Summary lists ~15 row labels; Transcript
Publication Record lists the ~12 per-kind field labels. These
enumerations duplicate renderer internals (e.g.,
`_ORG_OVERVIEW_ORDER_BY_KIND`, `_LOCATION_OVERVIEW_ORDER`,
`render_media_summary`'s inline `row(…)` calls,
`render_transcript_publication_record`'s per-kind row() blocks).

**Problem — systematic drift surface.** Every time a renderer
adds / removes / renames a field, the prompt's enumeration drifts.
Surfaced during the 2026-04-21 audit of the 6 inherited Phase II
Step 1 subsections against their renderers — every detailed
enumeration had some form of drift accumulated since the initial
write:

- **Organization Overview.** Wrong labels (`Current Director` vs
  actual `Director`; `Office Type` vs actual `Type`). Missing gov
  fields (Internal Name, Terminated, and the entire military-unit +
  military-service sub-shape field sets: Designator / Unit Class /
  Parent Unit / Home Station / Commissioned / Decommissioned /
  Mission / Branch Type / Founded). Wrong field order in all 3
  kinds (e.g., `CAGE Code / Registered Status` reversed from
  renderer's actual `Registered Status / CAGE Code`).

- **Transcript Publication Record** (`other` kind). Truncated labels
  (`Outlet` vs actual `Outlet / Platform`; `Program` vs actual
  `Program / Show / Venue`; `Host(s)` vs actual `Host(s) /
  Interviewer(s)`). Missing `Transcript Verified` row entirely.

- **Media Summary.** Listed 5 of ~15 row labels. Wrong labels
  (`Camera Device` vs actual `Camera / Device`; `Embedded Metadata`
  vs actual `EXIF / Container Metadata`). Missing Title / Kind /
  Date Captured / Date Released / Codec / Color Mode / File Size /
  Primary Source URL / SHA256 rows.

Each enumeration is an ongoing drift surface that has to be
hand-maintained per renderer commit.

**Proposed fix.** Replace the detailed per-kind / per-row
enumerations with pointers to the renderer constants or functions.

Before:
> gov emits Full Name / Internal Name / Type (from `office_type`) /
> Statutory Authority / Established / Terminated / Parent Organization
> / Director / Jurisdiction. Military-unit and military-service gov
> kinds layer additional fields (Designator / Unit Class / Parent
> Unit / Home Station / Commissioned / Decommissioned / Mission /
> Branch Type / Founded)...

After:
> gov Overview fields emit per
> `_ORG_OVERVIEW_ORDER_BY_KIND['gov']` in `build-from-research.py`;
> labels from `_ORG_OVERVIEW_LABELS`. See the renderer for the
> exact row order and label names.

Apply analogously to:
- Transcript Publication Record hearing / other →
  `render_transcript_publication_record`
- Media Summary fields → `render_media_summary`
- Any other Phase II Step 1 enumeration that duplicates a renderer
  constant or function-local row-list

Keep the **section-level structure** intact — what H2 sections render,
what they draw from, kind-conditional dispatch. Section-level info
rarely drifts; field-level info drifts constantly.

**Trade-off.**
- **Loses:** information density on first read. Reader who wants to
  know "what will a gov-contractor Overview table show?" now has to
  open the renderer source; the prompt gives the semantic category
  ("per-kind keys") but not the exact row list.
- **Gains:** elimination of an ongoing drift surface. Renderer
  commits that add / remove / rename fields don't require parallel
  prompt updates. One source of truth (the renderer) instead of two
  (renderer + prompt) for per-kind row details.

**Paired improvement.** If paired with a docstring refresh on the
renderer functions themselves (e.g., `render_org_overview` docstring
listing the fields it dispatches on), the renderer becomes
self-documenting and the pointer-from-prompt is a one-hop read.
Worth considering bundling.

**When to do.**
- Low urgency today. Current enumerations are accurate as of the
  2026-04-21 audit.
- Worth doing proactively if enumerations drift again in the next
  few renderer changes.
- Also worth doing if the prompt length becomes a concern — the
  field enumerations are the densest part of Phase II Step 1 (~130
  lines across 7 type subsections).

Surfaced: 2026-04-21 Phase II Step 1 audit.

