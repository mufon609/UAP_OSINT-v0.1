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

---

### 17. Table renderers drop the `note` field across structured sections

Every relationship-bearing / synthesis-content-bearing list section in
a research artifact carries a `note` field that captures source-derived
nuance — oversight vs. parent-chartering relationships, direct vs.
downstream succession, role-evolution context, ownership-transition
rationale, contract-lifecycle framing. The node-body renderers emit
the row's structured fields (e.g., Organization | Relationship |
Source) as a table cell and drop the `note` content. The evidentiary
nuance exists in the artifact; the rendered node hides it.

**Affected sections** (non-exhaustive — every list section with a
`note` entry field rendered as a table):

- `org_relationships.note`
- `key_personnel.note`
- `contracts.note`
- `ownership_timeline.note`
- `uap_scope_activity.note`
- `affiliations[].note` (person nodes)
- `relationships[].note` (person-to-person)
- `location_relationships[].note`

**Concrete consequence** — UAPTF v7 audit (2026-04-23). The AARO
relationship entry `or2` carries a note stating *"AARO is the
downstream successor in the chain — UAPTF → AOIMSG (Nov 2021) → AARO.
The primary-direct-successor relationship to UAPTF is or1 (AOIMSG);
this entry captures the downstream succession chain terminus."* The
EXCOM entry `or9` carries *"senior oversight body sitting above UAPTF
in the reporting chain, primary-source-attested by the UAPTF Charter."*
Both rows render as bare `other` relationship type with a source path;
the rendered table gives readers no distinction between AARO (downstream
successor via rename), EXCOM (oversight body per Charter), US Navy
(lead department), and OSD (cognizant authority) — all four display
identically. The audit summary: *"the prose tells a story the
structured data doesn't."*

**Design decisions for the redesign pass:**

1. **Display convention.** Column-wise 4th-column "Notes" header vs.
   inline-under-row prose (indented paragraph below each row). Notes
   run 1–3 sentences in practice; cell treatment pushes long notes
   into unreadable wrapping on narrow screens. Inline-below reads more
   naturally for the prose shape `note` actually carries. Recommend
   inline-below; confirm once implementation is prototyped.
2. **Truncation policy.** Some notes (or2, or4, or6 in uaptf; kp1b /
   kp9b in ttsa) run multi-sentence. Options: full render, soft
   char cap with expand, first-sentence-only at render with link to
   artifact. For an evidentiary repo full render is probably right —
   codify the convention once rather than per-section.
3. **Backlog-stub ghosting** (orthogonal but adjacent). If a
   note-bearing row references an unbuilt stub (e.g., UAPTF's or9
   → `/organizations/uap-excom`), the renderer could italicize /
   ghost the row so click-through expectations are calibrated. Cheap
   to include if the renderer is being touched anyway.
4. **Enum-extension alternative considered and deferred.** The
   narrower fix — extend `org_relationships.relationship_type`
   with `downstream-successor`, `oversight`, `reporting-body`, etc. —
   was rejected because (a) the enum grows indefinitely as each new
   edge nuance surfaces, (b) each addition is a schema commitment
   made in advance of usage evidence, and (c) rendering the existing
   `note` field achieves the same reader-visible outcome without
   schema prescription. Note rendering does NOT foreclose future
   enum tightening — if notes begin recurring across many edges
   (e.g., fifteen rows saying "oversight body per Charter"), that
   becomes evidence-driven justification for an enum addition.
5. **Parallel to end-only-period rendering** (`period: – 2021` for
   bracketed end-with-unknown-start, landed 2026-04-22). Both are
   renderer passes over artifact content the structured data already
   contains. If the renderer is touched broadly, grouping related
   polish (column alignment, sort stability, header formatting) into
   one pass reduces churn.

**Scope note.** This item is corpus-wide, not UAPTF-specific. The
UAPTF v7 audit surfaced it as a concrete example but every
organization, location, person, and gov-contractor node currently
carries `note` fields invisible to readers. A single renderer pass
closes the gap for every node built to date and every node that
will ever be built; no per-node remediation required.

Surfaced: UAPTF v7 audit (2026-04-23) — AARO and EXCOM rows flagged
as displaying identically to `other`-typed edges despite the
artifact carrying distinctive source-derived framing for both.

---

### 18. Codify Key Passages ordering convention in `conventions.md`

The node-body renderer sorts Key Passages (and Key Testimony on
hearing events) by `statement_date` when the field is present on
entries. The ordering is currently an implicit behavior — it is
explicit in `schema.yaml` only for hearing-kind Key Testimony
("verbatim passages sorted by statement_date"); for document /
transcript / media / organization / location Key Passages, the
schema says "all quotes" without specifying ordering. Behavior is
emergent: artifacts with `statement_date` populated render
chronologically; artifacts without it render in artifact-entry
order; partial population produces mixed ordering.

**Concrete consequence** — TTSA v3 (2026-04-23). Phase 3 of the
v2 cleanup populated `statement_date` on all 44 quotes. The
renderer then sorted Key Passages chronologically, which promoted
q5 (DeLonge email to Podesta, 2016-01-25) from mid-list to position
1 — ahead of the 2017-07-10 SEC 1-A filings. The DeLonge email is
the weakest-sourced entry in the set (self-attestation about
Roswell material and Wright-Patterson AFB, not independently
verified), and placing it at position 1 risks a chronological
convention being read as an epistemic endorsement.

The v2 cleanup had independently flagged this risk and tightened
the q5 header to "DeLonge email to Podesta — claim-of-record
regarding McCasland, Roswell material, and Wright-Patterson AFB
(claim made by DeLonge; not independently verified)". That
in-header framing means the weakest attestation carries its own
epistemic hedge at the top of the passage, independent of list
position.

**Convention to codify:**

1. **Chronological ordering is the corpus default** for Key
   Passages across all node types that support `statement_date`.
   Same rule as the explicit hearing Key Testimony rule — extend
   the scope clause in `schema.yaml` to cover all Key-Passages
   sections, and cross-reference the behavior in
   `conventions.md`.
2. **`statement_date` should be universally populated** on quotes
   whenever the source attests a date. Partial population produces
   mixed-order rendering that confuses readers; a fully-populated
   artifact produces clean chronology. Consider promoting
   `statement_date` from optional to required where the source
   has a date (validate-research.py can warn when a quote has no
   statement_date but the source has an attested date).
3. **In-header epistemic flagging is the hedge for weak
   attestations** that would otherwise claim position 1 purely on
   chronology. The convention: when a quote's evidentiary weight
   is meaningfully below the median for its artifact (claim-of-
   record, self-attested, secondary-source, contested), the
   `significance` header carries an explicit hedge phrase —
   "claim made by X; not independently verified" /
   "claim-of-record" / "self-attested, contested" — so readers
   see the epistemic framing before they read the quote text.
   No schema change; discipline at the contributor layer.

**Scope note.** Rule 1 is a documentation change (schema.yaml
comment clarification + a `conventions.md` section on Key Passages
ordering). Rule 2 is a schema policy decision (whether to promote
`statement_date` from optional to required-when-attested, and
whether to add a validate-research.py warning). Rule 3 is a
contributor-discipline convention — codifying the hedge-phrase
pattern with examples in `conventions.md`. All three address the
same emergent behavior and should land in a single convention
pass.

**Confirm pattern before codifying.** TTSA v3 surfaced the
behavior; one more organization-node audit (with weak-attestation
quotes and `statement_date` populated) would confirm the
hedge-phrase convention holds generally before freezing it in
`conventions.md`. If the next audit produces a different
ordering concern, revisit.

Surfaced: TTSA v3 (2026-04-23) — q5 DeLonge-Podesta email
promoted from position 5 to position 1 after `statement_date`
adoption; hedged in-header in the same commit.
