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

### 10. Auditing tables for redundant Node Link columns

Surfaced 2026-04-22 during Dietrich node review. Several renderer
tables had a trailing `Node Link` column that duplicated the first
column's wrap path (same `[\`/organizations/x\`]` string in both the
first and last cells). Pattern occurred on every table where the
first column was itself a wrap path — the Node Link column added no
navigation value.

**Fixed in this commit for 8 renderers** (person Affiliations,
person Relationships, Vouching Chain, encounter Participants,
hearing Participants across all sub-subsections and Flagged rollup,
organization Key Personnel sub-subsections, organization
Relationships, location Relationships). All affected built nodes
regenerated.

**Pattern to watch for in new renderers.** When adding a table whose
first column is a wrap-path link, DO NOT add a trailing Node Link
column — the first cell already serves as the navigable link. Keep
Node Link only when the first column is prose / date / free-text
(Timeline, Publication Record, Claim Inventory, Speakers) where a
separate navigable target adds genuine value.

Surfaced: post-Dietrich-rebuild review (2026-04-22). Kept as a
BACKLOG entry to document the pattern; addressed in the commit that
logged this entry.

---

### 11. Wayback fetch workflow should auto-decompress gzip

`web.archive.org` returns `Content-Encoding: gzip` responses when the
client doesn't override `Accept-Encoding`. A plain `curl -sSL -o PATH
URL` saves the gzipped bytes verbatim rather than decompressing. The
result: HTML files on disk that are unreadable to `validate.py`'s
prose-drift check and silently produce cascading false errors ("100%
of tokens absent from source") because the validator tokenizer reads
raw gzip bytes.

**Fix on trigger:** Add `--compressed` to curl invocations in any
fetch workflow (ad-hoc archival, `archive.py` if it ever fetches HTML,
helper scripts). Document the gotcha in `meta/sources-access.md` (done
2026-04-22). A preventive check would be a lint rule in `validate.py`
that flags archived `.html` files whose first bytes are the gzip magic
`\x1f\x8b` — but the fix at write time is one flag.

Surfaced: Grusch rebuild (2026-04-22) — 5 Wayback-fetched HTMLs hit
this; decompressed + checksum-updated after the fact.

---

### 12. Validators don't decode HTML entities before tokenization

`validate.py::normalize_for_compare` and
`validate-research.py::extract_significant_tokens` both read HTML
source files as raw text without running `html.unescape()`. Source
prose containing `doesn&#8217;t` (HTML-entity curly apostrophe)
tokenizes as `doesn` + `8217`, not as the logically-equivalent
`doesn't`. Attestation text written with ASCII `doesn't` then falsely
flags the word as prose-drift-unmatched.

Workaround (used 2026-04-22 on Grusch vouchers): author voucher
attestations with Unicode curly apostrophe `’` (U+2019) — the
tokenizer splits both forms identically so the token simply disappears
rather than mis-matching. Principled fix: add `html.unescape()` after
file read in both validators' source-extraction helpers, with
parallel treatment in `extract-source.py` for consistency.

Low priority — the Unicode-curly workaround is mechanical and the
issue only surfaces on direct quotation of web HTML that uses entity
encoding. Source files from pdftotext and plain-text transcripts don't
hit this.

Surfaced: Grusch vouching-chain rebuild (2026-04-22) — vc4, vc5, vc10
attestations from NewsNation HTML initially failed prose-drift; fixed
by rewriting with curly apostrophes.

---

### 13. Claim Inventory status vocabulary is undifferentiated

`render_claim_inventory` on whistleblower nodes hard-codes every row's
Status cell to `✅ Sworn / documented`, regardless of the actual
attestation venue. That lumps at least four distinct evidentiary tiers
into one label:

1. **Sworn under oath** — congressional hearing testimony (e.g., Grusch
   oral 2023-07-26 under oath before the House Oversight Subcommittee)
2. **Sworn under penalty of perjury** — legal filing (Grusch's PPD-19
   procedural complaint is adopted under 18 U.S.C. § 1001 attestation)
3. **DOPSR-cleared public disclosure** — pre-publication-reviewed
   statements (Grusch's Debrief quotes and written testimony carry
   DOPSR case 23-F-0946; reviewed by DoD but not sworn)
4. **On-record interview without oath** — JRE, American Alchemy,
   NewsNation post-hearing appearances — Grusch-attributed but no
   attestation ceremony

These tiers carry meaningfully different evidentiary weight. A
researcher scanning the Claim Inventory should see at a glance that a
sworn-oath claim and a podcast claim aren't equivalent.

**Fix sketch:** extend quote schema with an optional
`attestation_tier` enum field — values like `sworn-oath`,
`sworn-perjury`, `dopsr-cleared`, `on-record`, `self-attested`,
`unknown`. Renderer maps tier to a differentiated status-cell label
(e.g., `✅ Sworn (oath)`, `✅ Sworn (perjury)`, `✅ Public, DOPSR-cleared`,
`◯ On-record`). Default `unknown` for legacy entries.

Surfaced: Grusch Claim Inventory rebuild (2026-04-22) — 62 filed-claim
quotes all render with identical Status, obscuring the Debrief-vs-oral
distinction.

---

### 14. Q&A answer fragments inflate Statements as standalone quotes

Oral-testimony Q&A produces one-word answers (`"Yes."`, `"Both."`,
`"Personally, yes."`) that currently register as standalone quote
entries with the question carried in the `context` field. Structurally
valid — the verbatim-quote check passes because `"Yes."` appears in
the source — but the rendered Statements section treats each as a
blockquote row equal in weight to a full paragraph. Readers scanning
the node see several `> Yes.` lines that only make sense after reading
the `Attributed to` cell.

**Fix sketches** (pick one at design time):
- **Q&A pair schema**: optional `question` field on `quote_entry`.
  Renderer emits question + answer as a paired block (e.g.,
  `**Q (Burchett):** … **A:** Yes.`). Schema extension; validator
  must re-anchor both Q and A against the source.
- **Content-rewrite discipline**: merge tight Q&A exchanges into
  single quote entries where Grusch's answer is a continuous-with-
  question utterance. Keeps schema stable but requires source-read
  authoring discipline; some answers genuinely stand alone.
- **Render-time demotion**: quotes whose normalized text length is
  below a threshold render as inline `> **Q:** … — **A:** …` rather
  than standalone blockquote. No schema change; renderer-only.

Surfaced: Grusch rebuild (2026-04-22) — 7 of 8 sub-30-char quotes in
the 165-quote Grusch set are oral-Q&A answer fragments; the remaining
1 (`"eighty-year arms race"`) is a legitimate terminology extract.

---

### 15. Vouching Chain cell truncation hides full-length attestations

`render_vouching_chain` truncates the `Statement` cell at 100 chars:

```python
if len(attestation) > 100:
    attestation = attestation[:97] + "…"
```

For short one-phrase vouchers ("beyond reproach") this is fine. For
paragraph-length primary-source-anchored attestations — e.g., Karl
Nell's 2023-06-05 Debrief statement (419 chars) — the rendered cell
reads `"over the pa…"` and the reader has to click through to
`/sources/...` to see what Nell actually said. Data is intact in the
research artifact; only the rendered display is truncated.

**Fix options:**
- Raise the cap (e.g., 300 or 500 chars) — partial improvement
- Shape change: render Vouching Chain like Statements — blockquote
  with the full attestation + an attribution-metadata row below —
  mirroring the person-statement rendering shape. Loses the scannable
  table format but preserves full text.
- Hybrid: keep the table scannable, but also emit a subsidiary
  `### Voucher attestations (full text)` block below the table
  repeating each entry's attestation verbatim.

Shape-change option (full Statements parallel) is most consistent
with the "verbatim text is the primary surface" discipline in
`conventions.md`. Table-with-truncation treats the voucher statement
as metadata, which is the wrong category.

Surfaced: Grusch Vouching Chain (2026-04-22) — 2 Nell attestations
and 1 Burchett "Dadgummit" quote all truncated mid-sentence; user
flagged on review.

