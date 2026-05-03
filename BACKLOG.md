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

---

### 19. "Verified verbatim" marker — removed; full-corpus audit in progress

**Status (2026-04-24).** The original marker-ambiguity problem has
been solved by removing the marker entirely rather than qualifying
it. Confirmation against the underlying primary source is now a
precondition for inclusion in node bodies (enforced mechanically by
`validate.py`'s unconditional verbatim-quote check), not a rendered
claim (`meta/conventions.md` codifies the principle). Implementation
surfaced a corpus-integrity question — were the 508 existing quotes
actually confirmed against their sources, or only against whatever
extraction the pipeline produced? — which restructured the closeout
into a multi-tier per-source audit. **BACKLOG #19 does not close
until Tier 6 runs.**

**Shipped** (pushed to `origin/main` 2026-04-24):

| Phase | Commit | What |
|---|---|---|
| A | `978221a` | `extraction_type` field on `manifest_entry` (text-native \| ocr-scan); validator enforces enum |
| E | `997cc56` | `conventions.md` — "Confirmation is a precondition for inclusion" principle articulated; source-link-is-the-evidence framing; mechanical-backstop named explicitly; transcripts as equivalent-footing sources; OCR blind-spot called out |
| Fix-up | `3e5b88c` | BACKLOG #19 entry itself committed separately for git-history hygiene |
| v2 apply | `8a90d5c` | Grusch v2 audit applied as its own commit (predates implementation work) |
| D | `304bf08` | Grusch PPD-19 re-extraction via VLM page reading; clean `.txt` sibling created; validator extended to prefer sibling on ocr-scan sources; q163/q164/q165 corrected; nq2/nq3/nq4 removed |
| B | `31e03fa` | Verified marker removed from both renderer call sites; `_render_verification_block` → `_render_attribution_block`; `find_quote_verification_pairs` → `find_quote_source_pairs` + unconditional check + line-number failure messages; `requires_quote_verification` → `requires_quote_attribution` schema rename across 7 sites; all 17 nodes regenerated (464 mechanical deletions, 0 additions); prompts + templates updated |
| F.1 | — | Diagnostic: 508 quotes across 64 sources; 70% PDF / 15% HTML / 14% transcript. Top 10 sources carry 77% of quotes. Hearing transcript alone is 42% of the corpus |
| F.2 Tier 1 | `4b4d7fb` | Hearing transcript audit: `extraction-lossy` enum value added (third category after text-native/ocr-scan); sibling-lookup generalized to `!= "text-native"`; 54-page clean `.txt` transcription via VLM; 6 corrections across 3 categories; 1.4% contributor-drift rate measured |
| F.3 stub | `ea64cf4` | Closeout document stubbed at `meta/toolkit-notes/corpus-audit-2026-04.md` with Tier 1 findings recorded |
| F.2 Tier 2 | TBD | 3 written testimony PDFs audited (Fravor / Graves / Grusch). All three text-native with faithful pdftotext output per metadata + suspect-char scan + VLM visual verification. Zero corrections. 87 quotes already passing unconditional verbatim-quote check are now substantively verified. ~30 minutes across all 3 sources. Notable: Grusch testimony uses same Acrobat Distiller 23.0 as Tier 1 hearing transcript but extracts cleanly — Distiller not automatically extraction-lossy |

**Remaining work — Phase F.2 Tiers 3–5 + F.3 Closeout:**

*Tier 3 — 9 transcript sources (73 quotes).*
JRE 2065 (20), NewsNation Coulthart (17), American Alchemy (10),
Somewhere in the Skies (9), Grusch Sol closing (6), Linda Hall (5),
American Veterans Center (3), Merged Podcast (2), Calling All
Beings (1). Mostly YouTube-downloaded auto-captions.
**BLOCKED** on BACKLOG #20 (auto-caption convention decision). Phase
E principle doesn't specify audio-source handling. Three framings in
the closeout doc; hybrid-by-transcript_provenance is most principled
but requires schema work. **Estimated: 1 convention-decision session
+ 1–3 execution sessions depending on which option chosen.**

*Tier 4 — 28 HTML sources (78 quotes).*
HTML extraction low-risk (tag-strip + entity-decode). Batched spot-
check per source. Projected 0–2 findings. **Estimated: 1 focused
session.**

*Tier 5 — PDF long-tail (~17 sources, ~50 quotes).*
6 Uintah parcel PDFs (same ORDS portal pipeline — check once, apply
conclusion to all); AARO HRR Vol I; ODNI preliminary assessment;
various FOIA responses; SEC TTSA filings. One-by-one or batched
where pipeline shared. **Estimated: 1 focused session.**

*Tier 6 — Closeout.*
Complete `meta/toolkit-notes/corpus-audit-2026-04.md` with aggregate
findings across all tiers. Confirm follow-up BACKLOG entries #20–#24
are filed (already queued below). Close BACKLOG #19.
**Estimated: 1 session.**

**Total remaining: 4–7 focused sessions** to complete Phase F and
close #19. Spread depends primarily on the Tier 3 convention decision.

**Findings to date** — 6 corrections across 298 quotes audited
(Tier 1: 6 corrections across 211 quotes, 2.8% error rate across
all causes / 1.4% contributor-drift rate. Tier 2: 0 corrections
across 87 quotes). **Aggregate contributor-drift rate across
audited quotes: 0.67%**, roughly half the Tier 1 standalone rate.

**Tier 1 was the worst-case segment of the corpus, not a
representative sample.** It combined three compounding risk factors:
high quote volume (211 across 6 artifacts), known extraction-layer
issue (`11‡→11½`), and source complexity (54-page stenographic
transcript with oral testimony + Q&A + submitted documents — more
surface area for contributor drift than any single-witness written
document). Tier 2's 0% finding rate in contributor-authored short
written testimonies is evidence that Tier 1's 1.4% was the peak,
not the baseline.

**Projected remaining findings across Tiers 4+5** (~128 quotes):
revised down from earlier 3–5 estimate to **1–2 corrections**
based on Tier 2's outcome. HTML extraction is genuinely low-risk
(tag-strip + entity-decode handles nearly all cases); PDF long-
tail findings likely concentrate in one or two sources with
extraction-condition surprises, not spread evenly across all 17.

**Follow-up BACKLOG entries surfaced during the audit** (filed now
for tracking visibility; fate confirmed at Tier 6 closeout):
- #20 — Auto-caption vs audio confirmation discipline (blocks Tier 3)
- #21 — pdftotext Unicode-mapping quirks (extraction-tool-layer fix; narrower than extraction-lossy schema category)
- #22 — Provenance-marker treatment (per-row custody checkmarks on document nodes; different shape from per-quote Verified)
- #23 — BACKLOG #17 surfacing in Credibility Notes prose (verbatim caption forms read as misspellings)
- #24 — Location reference normalization (stale `lines N-M` pdftotext refs; low-priority hygiene)

**Recommended session sequence** (from post-Tier-2 planning):

1. **Tier 4 next** (28 HTML sources, 78 quotes). Larger source
   surface area than Tier 5 but extraction low-risk (tag-strip +
   entity-decode). Batched spot-check pattern applies across the
   whole set.
2. **Tier 5 after Tier 4** (PDF long-tail, ~17 sources, ~50 quotes).
   6 Uintah parcel PDFs are near-identical from the ORDS portal
   pipeline — batch-verify once, apply across all 6. Remaining ~11
   government / news PDFs are one-by-one spot-checks.
3. **Plausibly Tiers 4 + 5 fit in one session** if findings stay
   low (which Tier 2's outcome suggests they will).
4. **Tier 3 convention decision** runs on its own track. Don't
   collapse it into an audit-execution session — option 3 (hybrid
   by `transcript_provenance`) requires a schema field that needs
   the same care `extraction_type` got in Phase A. Dedicated
   focused session.
5. **Tier 6 closeout** after Tier 3 execution.

BACKLOG #21 (alternate PDF extraction tool) stays deferred. Tier 2
provided evidence that Distiller-produced PDFs are not automatically
extraction-lossy (the Grusch written testimony uses the same Acrobat
Distiller 23.0 as the Tier 1 hearing transcript but extracts
cleanly). If the Unicode-mapping issue isn't consistent within a
single producer, a wholesale tool change is solving the wrong
problem — it's treating the tool as the variable when the actual
variable is upstream (font embedding, encoding tables, something
source-specific). Current approach — flag lossy sources, produce
`.txt` siblings, move on — remains correct for the observed pattern.
Revisit #21 only if Tier 5 surfaces a systemic pattern.

---

**Original problem statement** (preserved for historical context; the
marker-removal decision superseded the four-option "convention fix"
framing proposed below):

The verbatim-quote check compares quote text against the pdftotext /
HTML extract of the cited source. When the source is a text-native
PDF or HTML, the extract is a faithful rendering of the original,
and "✅ Confirmed — verified verbatim" means exactly what it
implies. When the source is a **scanned PDF** and the scan passed
through OCR (inside the PDF or at extraction time), the extract is
a lossy rendering of the original; "verified verbatim" then means
only that the node's quote text matches the OCR extract, not that
it matches what the original document actually says.

**Concrete consequence** — Grusch v2 (2026-04-24). The archived
PPD-19 procedural filing PDF contains multiple OCR artifacts:
`UAP-telated` (for `UAP-related`, two instances), `compatrtmented`
(for `compartmented`), `appatently` (for `apparently`),
`cottelated` (for `correlated`). All three appear in quote entries
on `/people/david-grusch` flagged "verified verbatim" — the flag is
technically correct (bytes match extract), but reader-facing
interpretation is misleading: the attorney-drafted filing almost
certainly reads cleanly.

Workaround applied (Grusch v2): `naming_quirks` entries
(`preserve-as-sic-in-quotes` resolution) registered for each
observed artifact, plus a one-sentence flag in Credibility Notes
prose. This gets the reader-visibility done at the node level but
doesn't solve the broader convention gap.

**Convention fix to consider (not a node-level change):**

1. **Distinguish extraction type at source level.** Add a manifest-
   level or primary_sources-level field like
   `extraction_type: text-native | ocr-scan`. Populated at archival
   time (contributor inspects whether the PDF has a text layer and
   whether that text layer is clean or re-OCR'd).
2. **Differentiate the verification status marker.** Under
   `ocr-scan` sources, render "✅ Verified verbatim against OCR
   extract (original not re-verified)" instead of the unqualified
   "Verified verbatim" label. This is analogous to the distinction
   between "✅ Confirmed as sworn testimony — claim not
   independently verified" and "Testified that X is true" in
   conventions.md — same discipline of separating what a marker
   actually confirms from what a reader might infer it confirms.
3. **Add a `## Source Transcription Notes` rendered section.**
   Surface `naming_quirks` entries with `preserve-as-sic-in-quotes`
   resolution on the node body (currently they sit in the artifact
   and never reach the reader). Optionally scoped to nodes where
   at least one `ocr-scan` source is cited.
4. **Validator coverage.** When a quote's source is `ocr-scan`,
   `validate.py` could add an advisory warning suggesting a re-read
   against the original (human-in-loop only; no mechanical fix
   possible).

**Scope note.** This is cross-cutting: schema (field addition),
conventions (documentation of the distinction), renderer (new
section + status-marker variant), validator (advisory warning).
Touches every node that cites a scanned-PDF source, including
future ones. Worth batching into a single convention pass rather
than per-node workarounds repeated over time.

**Affected now.** Every node that sources from a scanned
government document — grusch (PPD-19 filing), plus any FOIA
response PDFs (several archived in sources/government/) that
went through scanner OCR rather than being text-native exports.

Surfaced: Grusch v2 audit (2026-04-24) — external auditor noted
that "verified verbatim" against a corrupted OCR extract is not
the same as verified against the original and is "a real gap in
the convention that will affect every scanned-document source."

---

### 20. Auto-caption-vs-audio confirmation discipline (Phase F Tier 3 blocker)

Phase E's "Confirmation is a precondition for inclusion" principle
(`meta/conventions.md`) names transcripts as equivalent-footing
sources once confirmed, but does not specify what "confirmed" means
for an auto-caption transcript. A YouTube-downloaded caption file
is itself an extraction of audio by a machine-transcription service;
caption typos (e.g., "Bigalow" for "Bigelow", "lockie Martin" for
"Lockheed Martin" in Grusch's JRE episode) are structurally the
same shape as OCR character-corruption on a scanned PDF — machine
rendering of an underlying signal, with errors.

Current established practice (per `feedback_transcript_timestamps_
in_quotes.md` and Phase A work): preserve auto-caption typos
verbatim via `naming_quirks` entries with resolution
`preserve-as-sic-in-quotes`. This is a node-level workaround; it
does not resolve the broader question of whether audio or the
caption file is the authoritative source.

**Three framings to decide between:**

1. **Transcript-as-source** — what Phase E language literally says.
   Tier 3 audit just confirms quotes match the transcript file,
   which the validator already does. Cheap. Accepts caption errors
   as authentic to the source of record.
2. **Audio-as-source** — every transcript-derived quote needs
   confirmation against audio. Download audio for all 9 transcript
   sources; sample-verify passages; possibly automate via modern
   speech-to-text diffed against the caption file, human-verify
   disagreements. Expensive.
3. **Hybrid by transcript provenance** — equivalent-footing when
   human-produced (stenographic transcripts, published interview
   transcripts — human has already done the confirmation-against-
   audio work). Audio-confirmation required when auto-caption
   (machine extraction of audio; same shape as OCR vs. page image).
   Requires classifying each transcript source via a new field like
   `transcript_provenance: stenographic | human-produced | service-
   produced | auto-caption`.

**Recommendation** (from the Phase F.3 closeout draft): option 3.
Most principled; aligns auto-caption handling with the OCR pattern
established in Phase A/D. Requires manifest schema field addition
+ classification pass + per-category audit methodology in
`meta/conventions.md`.

**Affected now.** 9 transcript sources, 73 quotes. Representative
cases: JRE 2065 (20 quotes — auto-caption), NewsNation Coulthart
(17 — auto-caption), American Alchemy (10 — auto-caption), plus
`when-it-mattered-55-dietrich-2021.pdf` (6 quotes — provenance
unclear, worth categorizing).

**Scope.** Convention decision is ~1 session. Execution scope
depends on option chosen: option 1 = 1 session; option 3 =
classification pass + sampled audio verification = 2–3 sessions.

**Blocks.** Phase F Tier 3. BACKLOG #19 cannot close until this
decision resolves and Tier 3 executes under it.

Surfaced: Phase F.1 diagnostic (2026-04-24) — 9 transcript sources
concentrate 14% of the corpus; Phase E principle didn't anticipate
the auto-caption-vs-audio axis when generalizing transcripts as
equivalent-footing.

---

### 21. pdftotext Unicode-mapping quirks on text-native PDFs (extraction-tool-layer)

The `extraction-lossy` enum category added in Phase F Tier 1 captures
the high-level source-condition pattern: text layer present (not
OCR'd) but pdftotext produces artifacts. The underlying root cause
for the known case (hearing transcript PDF, `11½` rendering as
`11‡` via pdftotext) is specifically a Unicode-mapping issue at the
PDF-generation layer — Acrobat Distiller mapped U+00BD ONE HALF to
U+2021 DOUBLE DAGGER in the text stream.

**Possible narrower fix:** use a different PDF text extraction tool
(e.g., `pdfplumber`, `pymupdf`, `mutool`) that handles this Unicode
mapping correctly, rather than producing a clean-text sibling per-
source. If the alternate tool gives clean output on the hearing
transcript and all other corpus PDFs, the extraction-lossy category
might dissolve for the Unicode-mapping subcase, leaving only
genuinely OCR'd sources needing siblings.

**Scope consideration.** This is a narrower question than the
extraction-lossy schema category. The category stays regardless —
OCR sources still need sibling handling. But if a tool change could
eliminate the Unicode-mapping failure mode across the corpus, that
reduces the sibling-production workload for future tiers of the audit
(and for future contributors adding sources).

**Methodology for evaluation** (deferred to a separate session):
run alternate PDF extraction tools against the hearing transcript
PDF; compare output to the known-correct visual content; check for
`11½` rendering correctness; check other Unicode edge cases
(fractions, typography, signature glyphs, section signs). If an
alternate tool gives clean output uniformly, propose adopting it in
`validate.py` as the PDF extraction path (with pdftotext retained
as fallback for compatibility).

**Affected now.** Hearing transcript PDF (only known case to date).
Future corpus PDFs may exhibit similar conditions — evaluation cost
is bounded.

Surfaced: Phase F Tier 1 (2026-04-24) — `11‡` for `11½` caught
during hearing-transcript audit; extraction-lossy enum added to
handle the pattern generically, but the specific case might have a
narrower solution at the tool layer.

---

### 22. Provenance-marker treatment on document node Provenance tables

Document nodes render a `## Provenance` section that tracks the
custody chain of the source file (authoring date, submission venue,
local archival, etc.). Rows use a `✅ Confirmed —` marker pattern
with evidence descriptions (e.g., `"✅ Confirmed — PDF metadata
CreationDate: Sun Jul 23 14:41:22 2023 EDT"`, `"✅ Confirmed —
hosted at oversight.house.gov"`, `"✅ Confirmed — SHA256 verified
via sources/manifest.yaml"`).

**Question surfaced during Phase B** (2026-04-24): with the per-
quote `Verified` marker removed under Phase E's "no rendered trust
claim" principle, should these per-row Provenance markers be
removed too?

**Analysis from the Phase B discussion** (user/model exchange):
the two markers look similar but do different jobs. The per-quote
Verified marker asserted "this quote matches the source" — a claim
about the quote itself that the reader could theoretically verify
but the marker was standing in for. That's the trust-performance
pattern Phase E rejects. The Provenance markers assert "this custody
event happened" — claims about the history of the artifact that
reference specific checkable evidence (PDF metadata, hostname,
SHA256). That's closer to the rendered-citation pattern (scholarly
"(Smith 2019, p. 47)") than to trust-performance: the prose after
the checkmark names the specific evidence the reader can follow.

The strongest Provenance claim is the SHA256 one (reader can literally
`sha256sum` against the archived file). Weaker is the PDF-metadata
claim (requires pulling PDF + running exiftool). Weakest is the
hostname claim (hostname may have changed since archival — the
Wayback link is the actual evidence, not the hostname).

**If revisited, the interesting move** is not removing the markers
but tightening them so the evidence is always as checkable as the
SHA256 case. That's different analysis from BACKLOG #19 and
deserves its own design pass.

**Recommendation.** Defer. Not a correctness issue (Provenance rows
are factual metadata with evidence attached; the marker is a
shorthand summary); not a readers-being-misled issue (prose names
the evidence). The analysis is genuinely different from #19 — the
removal pattern from #19 would be wrong if applied here.

**Scope if taken up.** Per-provenance-row audit: categorize each
marker's underlying evidence by checkability (SHA256-level / tool-
required / external-attestation); tighten wording to surface the
distinction where useful; or decide the current pattern is fine
given Phase E's principle doesn't scope to Provenance tables.

Surfaced: Phase F spot-check review of `✅ Confirmed —` patterns in
rendered nodes (2026-04-24) — Provenance markers share the marker
pattern with the per-quote Verified row but don't share the trust-
performance shape.

---

### 23. BACKLOG #17 surfacing in Credibility Notes prose — verbatim source forms read as misspellings without reader signal

Related to #17 (table renderers drop `.note` field across structured
sections) but surfaces in a different shape: Credibility Notes
contributor-synthesis prose can include verbatim source-form tokens
that look like typos to a reader who has no signal they are
preserved-as-sic.

**Concrete case.** `people/david-grusch.md` Credibility Notes
paragraph (Grusch v2 commit `8a90d5c`): *"Grusch described the
'$21 million' Reid had given 'to DIA and Bigalow Aerospace' as
funding for the 'assap' program… Grusch named a specific private
defense contractor — 'lockie Martin' — saying the company 'wanted
to divest itself…'"*

Every single-quoted phrase here is a verbatim fragment from the
JRE transcript (auto-caption typos preserved per established
discipline, tracked in naming_quirks nq1, nq5). The reader sees
"Bigalow", "lockie", "assap" and — without context about the
source's auto-caption provenance — reads them as contributor-
introduced misspellings.

**Possible fixes** (conceptually; none prototyped):
1. **Inline `[sic]`** after verbatim source-form tokens in prose.
   Discipline at the contributor layer; no schema change.
2. **Renderer surface for naming_quirks.** Section like
   `## Source-Form Notes` that lists preserve-as-sic entries from
   the artifact so the reader knows why source forms are preserved
   (related to #19's earlier-proposed `## Source Transcription
   Notes`, which was cut during implementation).
3. **Convention-layer signal** — wrap verbatim tokens in
   backtick-quoted spans with a trailing `[source form preserved]`
   descriptor.

**Relationship to #17.** #17 is the general case (note fields drop
in rendered tables); this is the specific case of source-form
tokens appearing unmarked in synthesis prose. Could be addressed
independently or bundled with #17's renderer pass.

**Priority.** Low. Not a correctness issue; reader inconvenience.
But worth tracking because the pattern will recur as more auto-
caption sources enter the corpus.

**Affected now.** `people/david-grusch` (JRE auto-caption forms
in Credibility Notes). Future: any node citing auto-caption
transcripts where contributor prose quotes source-form tokens.

Surfaced: Phase F diagnostic + Grusch v2 audit review (2026-04-24).

---

### 24. Location reference normalization — stale pdftotext line refs in quote Locations

Several existing quotes in the corpus cite `Location: lines 805-810`
or similar line-range references, which point at line numbers in
pdftotext output of the cited source rather than government page
numbers or other stable document anchors. These were keyed to the
pdftotext extraction in use at the time the quote was authored.

**Problem shape.** The validator's verbatim-quote check verifies
quote text substring-matches the extract; it does NOT verify
Location accuracy. So stale `lines N-M` refs don't cause validation
failures, but they become increasingly imprecise as sources get
re-extracted (e.g., Phase F Tier 1's clean-text sibling renumbers
the hearing transcript).

**Concrete affected quotes.** Several in `research/2023-07-26-house-
fravor.yaml`, `research/2023-07-26-house-graves.yaml`, `research/
2023-07-26-house-grusch.yaml`. Exact count deferred to the audit
execution.

**Second imprecision shape — boundary inclusion (surfaced 2026-04-28
during /events/2023-04-19-sasc-aaro-hearing build).** Beyond
re-extraction staleness, contributor-authored Location refs can be
imprecise from the start by including adjoining material in the
range. Concrete cases on `research/2023-04-19-sasc-aaro-hearing.yaml`:
q8 cites `lines 1784-1792` but Kirkpatrick's spoken portion ends at
line 1788 (Sen. Rosen interrupts at 1789, page footer at 1791-1792).
q11 cites `lines 2178-2183` but the quote content runs 2180-2182
(prior speaker turn at 2178-2179, next speaker at 2183). Different
root cause from staleness — caught during writing rather than during
re-extraction — but same fix target: tighter ref discipline using
the conventions in the Fix shape list above. The systematic sweep
addresses both shapes.

**Fix shape.** Systematic conversion of `lines N-M` refs to:
- `p. N, ¶M` for stenographic PDFs (hearing transcripts)
- `p. N` for single-line citations
- `¶N` for short documents without pagination
- `[MM:SS]` ranges for transcript/caption sources
- `lines N-M of the extract` explicitly when the extract is the
  intended reference (rare)

The conversion is mechanical once the rule is written down. Could
be a one-session sweep across the whole corpus.

**Priority.** Low. Not a correctness issue; navigational-precision
improvement for readers. Validator doesn't care.

**Scope.** ~1 session to write the rule + sweep + validate.
Independent of the Phase F audit tiers; can run before, after, or
between them.

Surfaced: Phase F Tier 1 (2026-04-24) — the hearing-transcript
`.txt` sibling used government page numbers as section markers,
which rendered existing `lines N-M` quote Locations increasingly
out-of-sync. Corrections deferred per explicit Phase F Tier 1 scope
decision (Phase F is about extraction integrity, not navigation
precision).

---

### 25. Event-renderer Event Summary table emits a fixed field set; populated `event_intrinsic` keys outside that set are unrendered

The event-renderer (`scripts/build-from-research.py` event branch)
emits the `## Event Summary` table from a fixed set of `event_intrinsic`
dict keys: `hearing_title` / `committee` / `session` / `congress` /
`date` / `location` / `chair` for hearing-kind events. Other
`event_intrinsic` keys populated by contributors are silently dropped
from the rendered node body even though they validate cleanly and
hold reader-relevant facts.

**Concrete affected keys** observed on hearing-kind event artifacts:

- `scheduled_time` (e.g., "10:30 a.m." — when the hearing was scheduled
  to convene)
- `convened_time` (e.g., "11:08 a.m." — when the gavel actually fell;
  often differs from scheduled when chained behind a prior session)
- `adjourned_time` (e.g., "12:08 p.m.")
- `ranking_member` (e.g., "Joni Ernst" — the minority counterpart to
  the chair, structurally significant for committee composition)
- `status` (e.g., "Open/Closed" — capturing that an open session was
  preceded by a closed session that day; relevant when there's a
  dual-status transcript)

All five fields appear on `research/2023-04-19-sasc-aaro-hearing.yaml`
(2026-04-28 build), all populated, all unrendered. Workaround applied
during that build: surface the same facts in the rendered `description`
prose. That works for one node but the pattern of duplicating
artifact-data into description prose to compensate for renderer gaps
isn't sustainable.

**Relationship to BACKLOG #17.** #17 covers `note` fields on list-entry
relationship rows being dropped by table renderers. This is a
different shape: top-level dict keys on `event_intrinsic` not in the
renderer's emit set, rather than per-row notes. Both are renderer
coverage gaps where validated artifact content doesn't reach the
reader, but the fix shape differs — #17 needs a notes-rendering
convention; this needs the Event Summary table to extend to whichever
keys are populated (mirroring the organization renderer's pattern of
emitting whichever overview keys are populated, skipping empty ones).

**Fix shape.** Either (a) extend the Event Summary table to emit any
populated `event_intrinsic` key not already in the explicit set
(generic key-passthrough for hearing-kind events), or (b) add
specifically-named additional rows for the keys above. Option (a)
generalizes better but risks rendering keys with poor display names;
option (b) requires per-key formatting decisions but produces
consistent column labels.

**Priority.** Low. Not a correctness issue; reader-visibility
improvement. The workaround (surface in description prose) is
acceptable single-node hygiene.

**Scope.** Renderer-only change; no schema work needed (the keys are
already optional on `event_intrinsic` per schema.yaml). One session
to add the renderer logic + regenerate any affected event nodes.

Surfaced: 2023-04-19 SASC AARO hearing event build (2026-04-28) —
audit pass identified that 5 populated `event_intrinsic` keys were
not appearing in the rendered Event Summary table; facts duplicated
into description prose as a node-level workaround.

---

### 26. Prose-drift check silently skips `document` type — coverage gap in validate-research.py

**The gap.** `scripts/validate-research.py` defines two maps that
gate the prose-drift check: `PROSE_FIELDS_BY_TYPE` (top-level
free-prose fields per type) and `PROSE_ENTRY_FIELDS_BY_TYPE` (per-
entry synthesis-content note fields per type). Both maps cover
**person, event, transcript, media, organization, location** — six
of the seven content types. **`document` is absent from both maps.**
When `check_prose_drift` runs, the first guard returns immediately
for any artifact whose `target_node` type isn't in either map.
Result: every document artifact's prose-drift check is a no-op,
regardless of how loosely the description tokenizes against source.

**The fit with conventions.** `meta/conventions.md` scopes the
prose-drift check to *"labeled synthesis surfaces (`description`,
`background`, `uap_relevance`, `credibility_notes`) and per-entry
synthesis-content notes"*. Document artifacts have a required
`description` field per schema. Document `description` should be in
scope by the convention; isn't in the implementation. The
implementation and the convention are out of sync.

**Inspection of the maps suggests this is an oversight, not an
intentional exclusion** — every other content type has a
`description` entry with rationale-bearing comments in
`PROSE_FIELDS_BY_TYPE`; document just isn't there.

**Current production impact.** Across the 4 built document
artifacts, **173 unmatched description tokens are silently passing
through with 0 warnings**:

| Artifact | Unmatched / total |
|---|---|
| `written-testimony-fravor-2023` | 47 / 139 |
| `written-testimony-graves-2023` | 40 / 157 |
| `written-testimony-grusch-2023` | 33 / 178 |
| `written-testimony-kirkpatrick-2023` | 53 / 135 |

The 19–39% rates compare against contributor-targeted 0% on other
types under the zero-warnings discipline. A meaningful gap.

**Token analysis** — the unmatched content falls into two buckets:

1. **Provenance/context vocabulary** — PDF-metadata-derived terms
   ("Author", "Producer", "CreationDate"), filing-process language
   ("submitted to the hearing", "open-session companion"), document-
   physical-attribute terms ("4-page", "PDF"). These describe the
   document, not the document's content; by definition they cannot
   match source-body tokens. This bucket is a structural mismatch
   between the description's role on document artifacts (synthesis
   *about* the document) and the prose-drift check's source pool
   (the document body itself).

2. **Synthesis verbs and connectives** — "covers", "characterizes",
   "includes", "describes", etc. The same shape of stylistic drift
   the check catches on other types. This bucket is real bucket-2
   drift that's currently unchecked.

**Are other types similarly impacted?**

- **`finding` type** — also absent from both maps, but no built
  artifacts yet (F.7 design pass pending). No production impact;
  will need to be added when F.7 ships.
- **`meta` type** — also absent. Likely intentional (governing
  docs are not user-content; conventions don't apply).
- **No other content types are missing from the maps.**
- **Per-entry coverage for document** — `quote_entry.significance`
  and `quote_entry.context` are not in conventions.md scope (they're
  per-quote metadata, not per-entry synthesis content), so the
  per-entry-map gap doesn't have a separate functional effect for
  documents. The top-level-map gap is the meaningful one.

**Design choices for the fix.** Three paths, none mechanical:

A. **Add `document` to `PROSE_FIELDS_BY_TYPE` with the same scoping
   pool** (union of `primary_sources[].path` tokens). Cheap; matches
   the convention literally; produces high false-positive rates as
   bucket-1 above shows. Forces document descriptions to use almost
   only source-body vocabulary, which damages legitimate contextual
   framing (provenance, cross-node positioning, document-physical
   attributes). Contributors face an unfixable warning surface.

B. **Add `document` with an expanded source pool.** The pool would
   include the document's own primary sources PLUS the source pools
   of structurally-adjacent nodes (companion transcript on testimony
   docs, hosting event, hosting organization). More machinery; more
   graceful for legitimate contextual content; introduces
   cross-artifact pool-resolution logic the validator doesn't have
   today.

C. **Document the exclusion explicitly** with a rationale comment
   in `PROSE_FIELDS_BY_TYPE` ("document descriptions are *about* the
   document, not from its body, so the token-match check produces
   noise"). Aligns implementation with what's already happening;
   surrenders bucket-2 drift checking on document descriptions.
   Cheapest; loses the most.

The choice depends on how much value bucket-2 drift detection has
for document descriptions vs. how much false-positive cost option A
imposes. Worth one focused session to decide and implement.

**Affected now.** 4 written-testimony documents (Fravor, Graves,
Grusch, Kirkpatrick). Affected on every future built document.

**Priority.** Medium. Not a correctness issue (verbatim-quote check
on document Key Passages is unaffected and runs unconditionally);
discipline-uniformity issue (drift checking is enforced on six
content types but silently skipped on the seventh).

**Scope.** ~1 session: design decision + implementation +
regression sweep across 4 existing document artifacts (which will
require either rewriting their descriptions to match the chosen
scope, or accepting the warnings they'll produce as a baseline).

Surfaced: 2026-04-28 audit pass on
`research/written-testimony-kirkpatrick-2023.yaml` build — direct
recreation of `check_prose_drift` logic showed 53 unmatched tokens
in description, but `validate-research.py` reported 0 warnings;
investigation traced to the missing `document` key in both maps;
confirmed across all 4 existing document artifacts.

---

### 27. Reveal Systems Inc. corporate-registration deep dive — blocked on subscription registry access

Per the 2026-04-29 Kirkpatrick audit § 7 ("Items still open"), specific
state-of-incorporation entity number, filing date, current operating
status, and principals-beyond-inventor list for the Kirkpatrick /
Bogaard / Fairchild patent-assignee Reveal Systems Inc. were not
retrievable through open-access channels. What we did establish during
the 2026-04-29 archival pass:

- **California is the state of incorporation** per the May 2020 USPTO
  assignment record on US20200357080A1: the assignment-of-assignor's-
  interest record on the original non-provisional names "REVEAL
  SYSTEMS, INC., CALIFORNIA" as the assignee.
- **California Secretary of State business search portal** is
  Imperva-blocked at the API layer (HTTP 403 to all automated POSTs);
  the bizfileonline.sos.ca.gov frontend returns an Incapsula JS
  challenge page with `noindex,nofollow` headers. Wayback Machine
  has no usable captures of registry-search result pages.
- **OpenCorporates** is HAProxy CAPTCHA-blocked (hCaptcha challenge on
  every request) and has no Wayback presence for Reveal-Systems-named
  entities.

**Name-collision warning** (load-bearing for any future Reveal Systems
Inc. node build under audit § 6): a different "Reveal Systems Inc."
exists with a Bloomberg company profile (ticker `0408205D:US`) — that
entity produces real estate software (custom legal forms, contracts).
It is **not** the patent-assignee Reveal Systems Inc. Future research
must distinguish via patent-assignee chain (CA assignment record →
USPTO file wrapper) rather than by name search alone.

**Path to closure** when subscription / interactive access becomes
available:
1. CA SoS bizfileonline.sos.ca.gov direct interactive query (browser-
   solved Imperva challenge) — yields entity number + filing date +
   current status + agent for service of process.
2. PACER / federal court records — would surface any litigation,
   bankruptcy, dissolution.
3. CrunchBase / PitchBook subscription — yields any institutional-
   investor activity (audit § 3.1 noted "no documented public-facing
   product launch, marketing presence, or commercial activity"; this
   would confirm or correct that observation).

**Priority.** Low. Not a correctness issue; depth-of-record question
for the eventual `/organizations/reveal-systems-inc` node build (audit
§ 6 recommendation). Patent-record evidence is sufficient for the
existing Kirkpatrick-node Credibility Notes framing.

**Scope.** ~30 minutes if registry access becomes available;
otherwise indefinite-blocked.

Surfaced: Kirkpatrick audit-iteration follow-up (2026-04-29) — open-
access registry hunt established CA state of incorporation per patent
record but blocked at SoS / OpenCorporates layer; name-collision
discovery worth recording so future Reveal Systems node-build
sessions don't conflate.

---

### 28. Mellon Signal exchange — redacted reply text awaiting Black Vault FOIA appeal

The April 18 2024 BlackVault release of FOIA case 24-F-0266 includes
the June 11–13 2023 Signal text-message exchange between Sean
Kirkpatrick and Christopher Mellon. Kirkpatrick's responses
("absurd and false"; "defending and adjudicating, and you're
undermining the very organization you purported to help establish
for this purpose") are visible verbatim in the released screenshots
and are now registered as Statements quotes q36 and q37 on
`/people/sean-kirkpatrick`.

**Mellon's full reply on the same exchange is partially redacted in
the released screenshot** — the visible portion documents Mellon
responding that he never claimed Grusch's claims were "accurate" but
felt Grusch was "sincere and credible," that he expressly called the
allegations "warrant[ing] investigation," and that he would "seek to
avoid further communication unless it is something that seems
extraordinary or if [Kirkpatrick] initiate[s]." The remaining text
is cut off in the released screenshot and Black Vault has filed a
FOIA appeal under case 24-F-0266 for the redacted portion.

**Status.** Pending external FOIA-appeal resolution. Out of repository
control; cannot be advanced through technical or research action.

**Path to closure** (passive, requires external event):
- Black Vault FOIA appeal resolves and the redacted text is released.
  At that point, Mellon's full reply becomes registerable on the
  Mellon person node (when built — that node is unbuilt per audit § 6
  Sol Foundation / disclosure-ecosystem build queue).
- Until resolution, the documentary record on Kirkpatrick's side is
  complete; the Mellon-side completion is downstream.

**Check-back cadence.** ~6 months. Black Vault FOIA appeals typically
resolve in 3–18 months; a 6-month check is the natural cadence to
re-verify whether the redacted portion has surfaced. The check
itself is cheap: re-fetch the FOIA 24-F-0266 release from Black
Vault and re-extract; if the redacted portion is now visible, the
follow-up work is to register Mellon's full reply as a quote on the
Mellon node (when built) and update Credibility Notes Group B on
the Kirkpatrick node accordingly.

**Priority.** Low. Not a correctness issue for Kirkpatrick's node;
adds nuance to the documentary record on the Mellon side. Sit-and-
wait until either (a) the FOIA appeal resolves, or (b) the Mellon
node is built (audit § 6 disclosure-ecosystem cluster) and the
incomplete-reply note becomes load-bearing for the Mellon Statements
section.

**Scope.** Effectively zero ongoing work; one short check-and-update
session when the redacted portion surfaces.

Surfaced: Kirkpatrick audit-iteration follow-up (2026-04-29) —
audit § 7 "Mellon Signal reply text (full)" Open item documented
with concrete check-back cadence and closure path. Logged for
visibility so a future session reviewing the Mellon node or the
Kirkpatrick credibility notes knows the appeal is pending.
