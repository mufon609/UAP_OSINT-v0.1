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

2. **Statement-block chronological ordering** — check #15 enforces
   ordering inside a single markdown table, but `## Statements`
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
  statements-only discipline? Options: hard-anchored claim layer
  (every sentence verbatim-quote-anchored), quotes-only Key Passages
  parallel to documents, or cross-reference surface parallel to
  hearing Witnesses & Testimony. See roadmap "F.7" section.
- Incorporate the investigation-pathway material that used to live in
  `research_gaps[]` (what readers expect from an active research
  thread: concrete methodology, cross-node scope, resolution state).

Surfaced: OQ removal (2026-04-21) — the rename was deliberately
deferred to a later session rather than bundled with the removal.
