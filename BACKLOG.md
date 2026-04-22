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

Numbering is stable across removals — retired items leave a gap rather
than shifting remaining IDs, so git-log and commit-message references
stay valid. Same policy `meta/conventions.md` applies to validator check
names.

---

## Open items

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

### 16. Cross-artifact quote ownership — duplication vs. person-node bulk

Person-node Statements sections currently carry every statement the
subject has made across all venues (Grusch: 164 quotes / 1770 lines).
Verbatim source passages are ALSO stored on transcript / document
artifacts, creating data-layer duplication.

Empirical state (2026-04-22): **70 verbatim source passages are
currently duplicated across 2–3 research artifacts each** (same bytes
in different YAML files). Not theoretical — the duplication grows
per node built.

This is the E.3 question the roadmap defers: *"multiple artifacts with
overlapping evidentiary claims. Can't build propagation tooling
without a propagation case. Likely after ~10 nodes through the full
pipeline."* The propagation case is now present at 16 artifacts.

**Three paths:**

1. **Polish on duplication** — ship items #13 (attestation tiers) and
   #14 (Q&A pair schema); 70 dupes persist but Statements rendering
   becomes scannable via tier labels + paired Q&A blocks.
2. **Pull E.3 forward** — each verbatim passage lives in exactly ONE
   artifact (the source-owning one: transcript for oral, document for
   text-native); person / event artifacts carry `quote_refs: [qid@artifact]`
   pointers; renderer resolves refs at build time. Claim Inventory
   filter requires cross-artifact query (reverse index built at
   validation time, or per-quote `speaker_path` + scan). Person nodes
   collapse as a consequence.
3. **Hybrid** — E.3 first; re-evaluate #13 / #14 on the reformed
   model. Tier labels and Q&A pairs likely still useful; duplication
   no longer drives their urgency.

**F.7 dependency:** a finding node citing a quote needs a stable
reference. On the current duplicated model, `q66@david-grusch` and
`q53@2023-07-26-house-grusch` can point to the same source passage —
the finding has to pick one arbitrarily. Finding-node design
(roadmap F.7, next up) probably forces this question regardless of
node-bulk considerations.

**Claim Inventory constraint:** `schema.yaml` defines Claim Inventory
as *"a render-time projection of quotes tagged `category: filed-claim`.
A filter, not a separate data structure — the filed claim IS the
quote."* Under path 2, if Grusch's filed-claim quotes live on the
transcript artifact, the whistleblower Claim Inventory filter has to
cross artifacts. Same for the Direct Observations / Other Statements
split on eyewitnesses. Either the resolver walks all artifacts where
`speaker_path == /people/{slug}`, or a reverse index is built at
validation time.

**Lighter alternative** (if E.3 scope is too big to pull forward):
add a navigation affordance — TOC jump-links at the top of nodes
≥500 lines, or collapsible per-venue Statements subsections in the
renderer. Doesn't touch the data model; addresses the scannability
symptom for investigators who want only Timeline / Relationships /
Connections. Estimated ~2-hour job; strictly cosmetic.

**Relationship to items 13 / 14:** under path 2, both pause pending
the reformed data model. Under path 1, both ship as planned. The
three items form a single design decision point, not independent
fixes.

Surfaced: Grusch post-rebuild architectural discussion (2026-04-22) —
164-quote node at 1770 lines prompted user question about offloading
quotes to hearing-event / transcript nodes so that investigators
looking for just a subject's Timeline or Relationships aren't scrolling
past a full testimony register.
