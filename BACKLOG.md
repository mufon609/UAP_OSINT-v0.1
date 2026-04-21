---
id: BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
---

# BACKLOG

Deferred work items surfaced during other work but not on the current
roadmap. Items are captured here when they're real, concrete, and would
be lost otherwise — not to overflow the active-work surface.

Each entry records:

- **Issue** — what the gap or problem is
- **Why it matters** — consequences of not addressing
- **Proposed scope** — rough outline of what a fix would entail
- **Surfaced** — when and in what context it came up

Items leave the backlog when they're either: (a) promoted to the active
roadmap / phase plan, (b) addressed directly, or (c) superseded / no
longer applicable (in which case the entry is marked resolved and kept
as an audit trail for a reasonable period before deletion).

---

## Open items

### Validator is not version-aware

**Issue.** When a file declares `schema_version: 2`, `validate.py` still
validates it against whatever structural rules `meta/schema.yaml`
currently describes. If `schema.yaml` is documenting v1 rules and a
file legitimately uses v2 structure, the validator will apply v1 rules
to a v2 file — producing false positives (v2-valid content flagged)
and false negatives (v1 rules satisfied by v2 content that would fail
v2's stricter requirements).

**Why it matters.** B2 closed the gap where *version labels* weren't
enforced against `compatible_with`. But *structural rules per version*
still aren't. During a real migration (v1 → v2 with genuine
structural differences), we need the validator to know both rule sets
and dispatch to the correct one per file. Today, the validator knows
one rule set and applies it uniformly regardless of file version.

**Proposed scope.** Extend `validate.py` to support per-version rule
dispatch. Three possible approaches:

1. Restructure `schema.yaml` so rule sections are version-keyed
   (e.g., `types.person.v1.required_sections`,
   `types.person.v2.required_sections`).
2. Split into separate `schema.{version}.yaml` files, loaded per-file
   based on the file's declared `schema_version`.
3. Keep a single schema and embed migration/translation logic in the
   validator that converts v1 files into v2-equivalent form for
   validation purposes (works only when migration is mechanical).

Also required:
- A test harness that confirms v1 files still validate cleanly under
  historical v1 rules while v2 files validate under v2 rules, during
  the overlap window.
- Documentation in `meta/toolkit-notes/schema-migrations/` describing
  how the multi-version dispatch works.

**Surfaced.** B2 implementation (2026-04-17). Noted as a deliberate
scope boundary of B2 ("B2 is a minimal first step, not a full
multi-version validation engine"). Not urgent until the first real
schema migration is planned; should be addressed before that migration
begins.

---

### validate.py is trending monolithic

**Issue.** `scripts/validate.py` has grown to ~570 lines and mixes
seven concerns in one file: parsing utilities, schema loading, source
integrity (checksum check, quote-verbatim check), per-node
structural validation, node collection, and report formatting. The
`validate_node` function alone is ~200 lines. Navigation already
requires grep + targeted reads. Adding more checks (Step D will add
research-artifact validation, coverage checks, node-vs-research sync)
will push the file toward 800+ lines.

**Why it matters.** `validate.py` is the load-bearing pre-commit gate
for the entire repository. Readability of this file governs how
confidently new checks can be added and how reliably bugs in the
check logic can be found and fixed. Monolithic files accumulate
unrelated-change bugs (edit near concern A inadvertently affects
concern B) and slow down contributors trying to understand the
validation surface.

**Proposed scope.** When the trigger fires (see below), refactor along
the repository's existing "flat scripts" pattern rather than
introducing a shared `lib/`:

- Keep `validate.py` as orchestration + `Issue` class + report
  formatting
- Extract per-category checkers into sibling scripts, each
  independently runnable:
  - `check-sources.py` (checksum integrity, file existence)
  - `check-quotes.py` (verbatim quote verification against archived
    sources)
  - `check-structure.py` (frontmatter, required sections,
    Confirmed/Flagged splits, OQ formatting)
  - Future Step D: `check-coverage.py`, `check-research-sync.py`
- `validate.py` becomes the composer — invokes each sibling checker,
  collects `Issue` objects, prints unified report
- Each sibling checker is also usable standalone (e.g., iterate-fast
  during development with just the one check you're debugging)

This mirrors the pattern already visible in `manifest.py
verify-checksums` as a standalone tool with its own responsibility.

**Interim mitigation (applied 2026-04-17).** Section-header comments
added to the existing file to make navigation cheaper without
structural changes.

**Trigger for full refactor.** Whichever comes first:
- `validate.py` crosses ~800 lines
- Step D's additions are fully settled and a second round of
  monolithic growth is imminent
- A contributor hits genuine confusion reading the file

**Surfaced.** During B2 summary review (2026-04-17).

**Design decision (D.4, 2026-04-17).** `review-coverage.py` shipped as
a sibling script rather than bolted into `validate.py`. This confirms
the split pattern — future check modules will follow the same approach.

**Trigger fired (2026-04-20).** `validate.py` has grown to 1197 lines,
past the 800-line trigger. Refactor is now actionable work, no longer
gated. The sibling-script pattern is proven (review-coverage.py,
validate-research.py, manifest.py verify-checksums all demonstrate it
well). When scheduled, proceed with the extraction plan above.

---

### Testing infrastructure

**Issue.** No automated tests exist for any script. The only test
signals are: (a) end-to-end smoke tests run manually during
development, (b) the validator exit code after a build. Regressions
in check logic, parsing edge cases, or CLI argument handling go
undetected until a contributor encounters the broken behavior in
real use.

**Why it matters.** The P1 smoke test from the Step A/B/C audit
(2026-04-17) caught a real bug in `new.py`'s `--corpus` handling
that would have silently produced malformed nodes on every
corpus-scaffold invocation. That bug had been shipped since the
initial Step A implementation and was discovered only because a
deliberate smoke test was run. Other scripts may have similar
latent bugs. As the script surface grows (Step D adds several new
scripts), untested regressions compound.

**Proposed scope.** Unit tests for specific check functions in
`validate.py` (quote normalization, checksum computation,
verification-block parsing, `evaluate_condition` parser). The check
logic is where correctness matters most, so it's the highest-leverage
place for function-level tests.

**Surfaced.** Step A/B/C audit (W1, 2026-04-17). Help-check
(`tests/help-check.sh`, 2026-04-17), smoke fixtures (`tests/smoke.sh`,
2026-04-17), and the pre-commit chain (`tests/pre-commit.sh`,
2026-04-18) shipped as end-to-end coverage. Unit tests remain open;
deferred until a check function needs bug-hunting or the validator
monolith refactor makes function-level testing more natural.

---

### Monitor retained-resolved research gaps for clutter

**Issue.** Research gaps with `resolved: true` and
`retain_as_done: true` render in the node's Open Questions section as
`- [x] DONE YYYY-MM-DD: …` entries. The intent is to preserve null
findings, methodology outcomes, and provenance-chain notes where the
closure itself is the useful record. Risk: contributors may set
`retain_as_done: true` too liberally, accumulating resolved-DONE items
that duplicate content now present in the node body (as new claims or
prose), producing a cluttered and less-focused Open Questions section.

**Why it matters.** Open Questions is a navigational surface — it
tells a reader "what's not known." When it becomes "what was asked
and answered ages ago," it loses that navigational value. The
existing repo convention (`meta/conventions.md`) is that resolved
items are normally REMOVED from Open Questions and the resolution is
promoted into the body. `retain_as_done` is a narrow override, not a
default.

**Proposed scope.** After 10+ document nodes have been built through
Phase II:

1. Audit all `retain_as_done: true` entries across the research
   corpus. Confirm each one's closure is the primary record (not
   duplicative of a new claim in the body).
2. If clutter is observed, tighten the `retain_as_done` guidance in
   `prompts/build.md` and/or add a validator warning when
   `retain_as_done: true` is set but the resolution text overlaps
   materially with a claim already in the artifact.
3. Possibly: cap the number of retained-DONE items per node (soft
   warning if a node has >N) as a forcing function.

**Interim.** Document the intent in `research_gap_entry.retain_as_done`
schema comment (done in D.3) and in the build prompt. Trust
contributors to apply sparingly. Re-evaluate after corpus accumulation.

**Surfaced.** D.3 design (2026-04-17 Q5). Deferred in favor of shipping
the layered Phase II.

---

### F.1a descriptive-only gaps (follow-on to #9)

**Issue.** Two F.1a schema additions are declarative but not yet
mechanically enforced. Behavior is correct today (hand-authored
content follows the convention; the F.1b renderer enforces at build
time), but the gap between what schema documents and what the
validator checks is worth tracking so it doesn't accumulate.

1. **`timeline_category_values`** (person type) — the Category column
   vocabulary (affiliation / role / observation / testimony /
   publication / clearance / incident / filing / other) appears in
   schema but isn't checked. A person Timeline row with
   `Category: banana` passes validation. Soft-enforcement (warn on
   unknown) matches the schema's "extensible; validator warns on
   unknown values" comment. Proposed: extend `check_chronological_tables`
   (or a sibling check_person_timeline_categories) to warn when a
   Category cell is set and not in `timeline_category_values`. Low
   priority; no drift damage today because the category field is
   advisory metadata, not evidentiary.

2. **Statement-block chronological ordering** (person Statements
   subsections) — check #15 enforces row-ordering within a single
   markdown table, but a person's `## Statements` section is a
   sequence of `> block quote` + verification-table pairs, not a
   single table. Chronological order across those pairs is not
   mechanically verified in an input-independent way.

   **F.1b resolution (partial).** The Phase II person renderer sorts
   statements at render time by `statement_date`. Under Boundary-check
   discipline (review-coverage.py check 2), renderer-driven nodes
   can't diverge. Remaining gap: validate.py check #15 doesn't
   independently verify block-quote ordering from the node body
   alone, so a hand-authored person node built without the renderer
   pipeline could drift silently. Accepted as a limitation until a
   hand-authored person node is attempted (not on the roadmap).

**Surfaced.** F.1a audit (2026-04-19). A third item (the
`chronological: true` section-rule flag being descriptive-only)
resolved in-place — left as a contributor-facing documentation signal
while check #15 enforces universally on every date-bearing table.

---

### F.1b audit — name lookup for cross-reference cells

**Issue.** F.1b emits cross-reference paths as backtick-bracket wraps
(``[`/organizations/aaro`]``) in table cells where the template
expects a display name (e.g., Organization column of Affiliations).
Today the rendered cell shows the path; an investigator reads
"us-navy" instead of "U.S. Navy".

**Why it matters.** Path slugs are recoverable but not investigator-
friendly. Display names lift readability at the cost of a small
renderer complexity bump. Low urgency because backtick-bracket paths
render as clickable links and the meaning stays one click away.

**Proposed scope.** Look up the display name from
`entities_referenced.name` (where `wrap_path` matches the target
path) or from the target node's frontmatter if the node exists. Apply
in the renderer's cross-reference cell emitters.

**Surfaced.** F.1b audit (2026-04-19). Three sibling observations
(quote_verification_fields, document_intrinsic convention,
entities_referenced vs cross-reference lists) shipped or were
reframed as design-clarity wins in the same pass — this entry carries
only the remaining renderer-enhancement work.

**Design clarity note (entities_referenced vs cross-reference
lists).** `entities_referenced` tracks entities named in *quote
text* — contributor-curated from registered verbatim passages;
stub-linking checks that every listed entity appears in the rendered
body. Cross-reference lists (affiliations / relationships /
corroboration_items / program_involvement / publication_record /
vouching_chain) are structural relationships with their own path
fields; the renderer emits them as backtick-bracket links
automatically and `associate.py` picks them up for Associated Nodes.
Contributors populate `entities_referenced` from quote-text entities
only — paths in structured cross-reference lists don't need
duplication there.

---

### Schema-descriptive keys — `optional_sections`

**Issue.** The `optional_sections` list on the media type
(`optional_sections: [Media Versioning]`) is read by no script. The
Media Versioning section escapes `required_sections` enforcement
because it's not listed there; the `optional_sections` entry is
informational.

**Why it matters.** Documentation-only schema keys that read as if
they gate behavior are a drift vector — contributors or automation
may assume they do. Promoting it to enforced behavior would turn
unknown H2 sections into a warning unless they appear in
`required_sections`, `optional_sections`, or a corpus addendum.
Useful mostly as a forcing function against drift where contributors
invent ad-hoc sections.

**Proposed scope.** Honor `optional_sections` as an allowlist for an
unknown-section warning pass. The `conditionally_required`
dispatcher's condition grammar can also grow (`in <list>`,
`<field> != <value>`) on-demand when a new conditional needs it — no
preemptive extension.

**Surfaced.** Source-taxonomy consolidation double-check (2026-04-18).
Sibling descriptive-only items resolved in the same audit window:
`conditionally_required` dispatcher shipped (2026-04-18),
`chronological: true` flag enforced via check #15 (2026-04-19 F.1a),
`may_be_empty: true` removed from schema (2026-04-20) as
documentation-only noise.

---

### Extend schema `format_values` for audio and image sources

**Issue.** `meta/schema.yaml` manifest_entry.format_values is
`[pdf, html, txt, post, video, transcript]`. The F.4c pilot
surfaced that video sources (.mp4/.mov/.webm) cleanly map to the
existing `video` value, but audio (.wav/.mp3/.flac) and image
(.jpg/.png/.tiff) files have no matching format value. When the
first audio-only or photo-only media node is built, the manifest
entry for its primary source falls back to `html` (incorrect) or
requires the contributor to pass `--format` manually to override.

**Why it matters.** Media kinds `audio` and `photo` are first-class
node-type kinds per `meta/schema.yaml` (media type has kinds
[photo, video, audio, imagery-other]). The manifest.yaml vocabulary
hasn't kept pace. As media nodes accumulate — photos from Skinwalker
Ranch, cockpit audio releases, satellite imagery — the mismatch will
force contributors into the `--format` escape hatch routinely,
which is easy to forget and produces silent manifest-entry drift.

**Proposed scope.** When the first audio or photo primary source is
about to be archived:

1. Extend `meta/schema.yaml` manifest_entry.format_values with
   `audio` and `image` (covering photo + imagery-other media kinds
   under a single format value).
2. Update `FORMAT_BY_EXT` in `scripts/manifest.py` and `infer_format`
   in `scripts/research-scaffold.py` to map common audio extensions
   (.mp3 / .wav / .flac / .aac / .ogg / .m4a) → `audio` and common
   image extensions (.jpg / .jpeg / .png / .gif / .tiff / .webp /
   .bmp / .heic) → `image`.
3. Extend `scripts/validate.py` `extract_source_text` with explicit
   audio/image passthrough (returns None + warn, matching current
   .mp4 behavior; ensures the quote-verbatim check and review-
   coverage claim-drift check both treat audio/image as legitimately
   unextractable per the F.4c tightening).

**Trigger.** First audio-only or image-only primary-source archival.
Likely candidate: `/media/skinwalker-ranch-photo-{slug}` during F.6
location pilot, or a standalone audio release (press conference
recording, cockpit audio) during Cluster A closeout.

**Interim.** F.4c's manifest.py / research-scaffold.py additions
explicitly route .mp4/.mov/.webm/.m4v/.avi/.mkv → `video` without
touching audio or image. Contributors archiving audio or image files
pass `--format` manually; manifest.py will not reject arbitrary
format strings today (there's no enforcement against format_values
in validate.py), but the manifest-entry's format field will then be
a free-text value not listed in the schema vocabulary.

**Surfaced.** F.4c FLIR1 pilot (2026-04-20). The MP4 case was
addressed in-session because `video` was already in format_values;
audio and image deferred because they'd require schema vocabulary
extension.

---

### Committee Members subsection lacks Chair/Ranking sub-grouping

**Issue.** F.2b hearing-event Participants renders Committee Members
as a flat table with Name / Role / Affiliation / Status columns. The
Cluster B pilot populated 21 Members — Chair (Grothman), Ranking
(Garcia), Full Committee Chair (Comer), plus 18 sitting Members —
with role text capturing their leadership status ("Subcommittee Chair
(R-WI)", "Ranking Member (D-TX)", etc.). The flat table reads
accurately but requires the reader to scan every row to identify
leadership; a sub-grouped layout (Chair / Ranking / Members) would
surface the structural hierarchy faster.

**Why it matters.** Hearings have asymmetric member influence —
Chair controls the gavel; Ranking controls minority time; ordinary
Members ask questions in their allotted minutes. An investigator
comparing hearings by leadership composition benefits from the
hierarchy being visible at a glance rather than derivable from a
string-match scan of role cells. Not urgent — the information is
present, just flat.

**Proposed scope.** Two options:

1. **Render-time grouping via role-string parsing** — detect
   "Subcommittee Chair", "Ranking Member", "Full Committee Chair" in
   the `role` cell and emit H5 sub-subheads (Chair / Ranking /
   Leadership / Members). Fragile — role cell phrasing varies across
   hearings (Senate vs House; subcommittee vs full committee
   hearings).
2. **Schema-level role vocabulary** — add an optional
   `leadership_role` field on `participant_entry` with enum values
   (`subcommittee-chair`, `ranking-member`, `full-committee-chair`,
   `member`, `observer`). F.2b reads it for sub-grouping; leave
   `role` as the free-text display cell. Cleaner; retrofits require
   a sweep of hearing-event artifacts (currently 1).

**Trigger.** Second hearing-event artifact shipped (Cluster C or the
next Senate/House hearing to land). The retrofit cost stays at 1
artifact while the count is low.

**Interim.** Flat table with role-embedded leadership text is
acceptable; contributors reading the node can sort mentally or
filter by text.

**Surfaced.** Cluster B hearing-event pilot (2026-04-20).

