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

### 19. Verified-verbatim marker removed; full-corpus source-integrity audit (Phase F) in progress

**The principle (settled, see `meta/conventions.md`).** Confirmation
against the underlying primary source is a precondition for
inclusion in node bodies, not a rendered claim. `validate.py`'s
verbatim-quote check runs unconditionally on every block-quote with
a Source row; nodes carry no per-quote verification marker. The
discipline is enforced mechanically and is invisible to readers by
design.

**Why this entry stays open.** The principle landed via a marker
removal + validator refactor + node regeneration pass. That pass
left a corpus-integrity question: existing quotes were verified
under the old regime, which substring-matched quote text against
`pdftotext` / HTML extract output. When the source's extraction
layer is lossy (OCR-scanned PDFs, character-substituting PDF
generators), bytes-match-extract is not bytes-match-original. A
multi-tier source-integrity audit (Phase F) walks every cited
source and re-verifies extraction quality. **#19 closes when Tier 6
closeout runs.**

**Authoritative progress record.** Tier-by-tier methodology,
findings, and aggregate measurements live in
`meta/toolkit-notes/corpus-audit-2026-04.md`. This BACKLOG entry
tracks the high-level work plan and remaining decisions; the
closeout doc is the source of truth for audit detail.

**Schema additions shipped during Phase F.** `extraction_type`
field on `manifest_entry` with values `text-native | ocr-scan |
extraction-lossy`. The validator prefers a same-stem `.txt` sibling
over `pdftotext` output when extraction_type is non-text-native —
the sibling is a contributor-produced clean transcription, visually
verified against the source, with its own manifest entry + sha256.

**Current corpus state.** 827 quotes across 144 unique source paths
across 28 research artifacts (up from 508 / 64 / 16 at Phase F.1
diagnostic — corpus has grown ~60%). The per-tier source counts in
the closeout doc were Phase F.1 snapshots; counts re-derive at each
audit-execution session.

**Remaining work.**

- **Tier 3 — transcript sources (auto-caption majority).** Audit
  blocked on BACKLOG #20 (auto-caption-vs-audio convention
  decision). Phase E's primary-source principle didn't specify
  audio-source handling; three framings are sketched in the
  closeout doc; option 3 (hybrid by `transcript_provenance`) is
  the most principled and requires schema work. **Estimated: 1
  convention-decision session + 1–3 execution sessions per chosen
  option.**
- **Tier 4 — HTML sources.** Extraction low-risk (tag-strip +
  entity-decode handles nearly all cases). Batched spot-check
  pattern. **Estimated: 1 focused session.**
- **Tier 5 — PDF long-tail.** Government / news / FOIA / SEC
  PDFs. Some pipelines cluster (Uintah parcel PDFs share an ORDS
  portal pipeline — verify once, apply across); the rest are
  one-by-one spot-checks. **Estimated: 1 focused session.**
- **Tier 6 — Closeout.** Aggregate findings across all tiers into
  the closeout doc; confirm follow-up BACKLOG entries are still
  appropriately scoped; close #19. **Estimated: 1 session.**

**Total remaining: 4–7 focused sessions.** Spread depends primarily
on the Tier 3 convention decision.

**Findings to date** (Tiers 1+2). Aggregate contributor-drift rate
across the audited 298 quotes: **0.67%** (6 corrections in Tier 1's
211 quotes / 0 corrections in Tier 2's 87 quotes). Tier 1 was the
worst-case segment of the corpus — high quote volume, known
extraction-layer issue (`11‡→11½` Unicode mapping), and source
complexity (54-page stenographic transcript with oral testimony +
Q&A + submitted documents). Tier 2's 0% rate in contributor-
authored short written testimonies is evidence that Tier 1's 1.4%
standalone rate was the peak, not the baseline. **Projected
remaining findings (Tiers 4+5):** 1–2 corrections.

**Recommended session sequence.**

1. **Tier 4 first** (HTML sources). Larger source surface area
   than Tier 5 but extraction is low-risk; batched spot-check
   pattern applies across the whole set.
2. **Tier 5 after Tier 4** (PDF long-tail). Cluster pipelines
   (Uintah parcel PDFs) verify once-and-apply; remaining PDFs are
   one-by-one.
3. **Tiers 4+5 plausibly fit in one session** if findings stay
   low.
4. **Tier 3 convention decision** runs on its own track. Don't
   collapse into an audit-execution session — option 3 (hybrid by
   `transcript_provenance`) requires a schema field that needs
   the same care `extraction_type` got. Dedicated focused session.
5. **Tier 6 closeout** after Tier 3 execution.

**Follow-up BACKLOG entries surfaced during the audit.** All filed
for tracking; fates confirmed at Tier 6 closeout:

- **#20** — auto-caption vs audio confirmation discipline (blocks
  Tier 3)
- **#21** — `pdftotext` Unicode-mapping quirks (extraction-tool-
  layer fix; narrower than the `extraction-lossy` schema category)
- **#22** — Provenance-marker treatment on document Provenance
  tables (different shape from per-quote Verified)
- **#24** — Location reference normalization (stale `lines N-M`
  pdftotext refs; navigation-precision hygiene)
- **#32 (M2)** — naming_quirks preserve-as-sic forms unmarked in
  synthesis prose

**On #21's deferred status.** Tier 2 provided evidence that
Distiller-produced PDFs are not automatically extraction-lossy —
the Grusch written testimony uses the same Acrobat Distiller 23.0
as the Tier 1 hearing transcript but extracts cleanly. The
Unicode-mapping issue isn't consistent within a single producer, so
a wholesale tool change would be solving the wrong problem
(treating the tool as the variable when the actual variable is
upstream — font embedding, encoding tables, source-specific). The
current approach — flag lossy sources, produce `.txt` siblings,
move on — remains correct for the observed pattern. **Revisit #21
only if Tier 5 surfaces a systemic pattern.**

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
   confirmation against audio. Download audio for all transcript
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

**Affected now.** 11 transcript sources, 80 quotes. Representative
cases: JRE 2065 (20 quotes — auto-caption), NewsNation Coulthart
(17 — auto-caption), American Alchemy (10 — auto-caption), plus
`when-it-mattered-55-dietrich-2021.pdf` (6 quotes — provenance
unclear, worth categorizing) and `ncas-kirkpatrick-aaro-duality`
(1 quote — auto-caption from a post-AARO Kirkpatrick presentation).
Mix expected to grow as additional interview / podcast sources land
in the corpus.

**Scope.** Convention decision is ~1 session. Execution scope
depends on option chosen: option 1 = 1 session; option 3 =
classification pass + sampled audio verification = 2–3 sessions.

**Blocks.** Phase F Tier 3. BACKLOG #19 cannot close until this
decision resolves and Tier 3 executes under it.

Surfaced: Phase F.1 diagnostic — transcript sources concentrate
~10% of the corpus's quotes; Phase E principle didn't anticipate
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

**Relationship to BACKLOG #32.** #32 (M1) covers `note` fields on
list-entry relationship rows being dropped by table renderers. This
is a different shape: top-level dict keys on `event_intrinsic` not
in the renderer's emit set, rather than per-row notes. Both are
renderer coverage gaps where validated artifact content doesn't
reach the reader, but the fix shape differs — #32 needs a notes-
rendering convention; this needs the Event Summary table to extend
to whichever keys are populated (mirroring the organization
renderer's pattern of emitting whichever overview keys are
populated, skipping empty ones).

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

The maps' structure suggests the omission is an oversight — every
other content type has a `description` entry with rationale-bearing
comments in `PROSE_FIELDS_BY_TYPE`; document just isn't there.

**Current production impact.** Across the 6 built document
artifacts, **209 unmatched description tokens are silently passing
through with 0 warnings**:

| Artifact | Unmatched / total |
|---|---|
| `eo-14347-restoring-department-of-war` | 0 / 140 |
| `pentagon-uapda-revisions-2023-11` | 36 / 188 |
| `written-testimony-fravor-2023` | 47 / 139 |
| `written-testimony-graves-2023` | 40 / 157 |
| `written-testimony-grusch-2023` | 33 / 178 |
| `written-testimony-kirkpatrick-2023` | 53 / 135 |

The 0–39% range against contributor-targeted 0% on other types
under the zero-warnings discipline is a meaningful gap. The
eo-14347 row at zero unmatched is informative — for some document
forms (executive orders here, plausibly press releases / FOIA
letters too), the description can plausibly source its vocabulary
entirely from the document body itself. For testimony documents,
the description carries provenance / about-the-document vocabulary
that inherently can't match source-body tokens. The two cases
behave differently under any scoping rule.

**Token analysis** — the unmatched content falls into two buckets:

1. **Provenance / context vocabulary.** PDF-metadata-derived terms
   ("Author", "Producer", "CreationDate"), filing-process language
   ("submitted to the hearing", "open-session companion"),
   document-physical-attribute terms ("4-page", "PDF"). These
   describe the document, not the document's content; by definition
   they cannot match source-body tokens. Structural mismatch between
   description's role on document artifacts (synthesis *about* the
   document) and the prose-drift check's source pool (the document
   body itself).
2. **Synthesis verbs and connectives.** "covers", "characterizes",
   "includes", "describes". The same shape of stylistic drift the
   check catches on other types. This bucket is real bucket-2 drift
   that's currently unchecked.

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
   the convention literally; produces high false-positive rates on
   testimony descriptions per bucket-1 above. Would force testimony
   descriptions to use almost-only source-body vocabulary, damaging
   legitimate contextual framing (provenance, cross-node positioning,
   document-physical attributes). Contributors face an unfixable
   warning surface on testimony nodes; the eo-14347 case at 0%
   suggests other doc forms tolerate Path A cleanly.
B. **Add `document` with an expanded source pool.** The pool would
   include the document's own primary sources PLUS the source pools
   of structurally-adjacent nodes (companion transcript on testimony
   docs, hosting event, hosting organization). More machinery; more
   graceful for legitimate contextual content; introduces cross-
   artifact pool-resolution logic the validator doesn't have today.
C. **Document the exclusion explicitly.** Add a rationale comment
   in `PROSE_FIELDS_BY_TYPE` ("document descriptions are *about*
   the document, not from its body, so the token-match check
   produces noise"). Aligns implementation with what's already
   happening; surrenders bucket-2 drift checking on document
   descriptions. Cheapest; loses the most.

The eo-14347 case (0 / 140 unmatched) is evidence that doc-form
heterogeneity matters — testimony descriptions and EO descriptions
have different about-vs-from balance. A per-doc-form scoping rule
(testimony → expanded pool; EO / press-release → source pool) would
slot into Path B as a refinement; consider during the design pass.

**Affected now.** All 6 built document artifacts (2 EOs / press-
release-form documents, 4 written testimonies). Affected on every
future built document.

**Priority.** Medium. Not a correctness issue (the verbatim-quote
check on document Key Passages is unaffected and runs
unconditionally); discipline-uniformity issue (drift checking is
enforced on six content types but silently skipped on the seventh).

**Scope.** ~1 session: design decision + implementation + regression
sweep across 6 existing document artifacts (which will require
rewriting their descriptions to match the chosen scope, or accepting
the warnings they produce as a baseline).

Surfaced: validator audit on a document artifact build — direct
recreation of `check_prose_drift` logic showed 53 unmatched tokens
on the Kirkpatrick written-testimony description, but
`validate-research.py` reported 0 warnings. Investigation traced to
the missing `document` key in both maps; confirmed across all
existing document artifacts.

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

---

### 29. `updated` frontmatter field — corpus-wide currency anchoring

**The gap.** Schema-required frontmatter is `[id, type, schema_version,
status, kind, created]` across all content types. There is no `updated`
or `last_modified` field. Body prose periodically carries time-anchored
clauses — e.g., AARO description prose carrying *"no Sancorp follow-on
or successor AARO Support Services contract is documented in archived
primary sources as of {date}"*. The "as of {date}" form freezes the
contributor's knowledge state at edit time, but a reader arriving six
months later cannot tell whether the clause reflects an actual review
on that date or is forward-projected boilerplate. Git log on the file
is the authoritative edit-history record per `meta/conventions.md`,
but readers don't reach for git log to evaluate prose currency.

**Affected surface.** Any node with rolling-currency clauses — most
acutely on government-entity org nodes where statutory deadlines,
caseload counts, contract terms, and personnel transitions accumulate
inline date anchors. AARO is the surfacing case; UAPTF, IPMO,
OUSD(I&S), Sancorp, Arlo, TTSA, and every person node with current
affiliations carry equivalent risk.

**Design choices.**

A. **Add `updated:` (or `last_reviewed:`) to schema.yaml frontmatter
   `optional` set across all content types.** Contributors stamp it
   when a node receives a content-currency review. Renderer surfaces
   it in the Overview row or as a node-foot annotation. Cheap; opt-in;
   no enforcement of refresh cadence. Risk: contributors forget to
   stamp.

B. **Move "as of {date}" prose into a structured `currency_anchors`
   list.** Each anchor: `clause` + `as_of_date` + `source.path`.
   Renderer composes the prose at build time. Heavier; forces the
   review discipline at the schema layer; surfaces the audit trail
   structurally.

C. **Convention-only.** Document in `meta/conventions.md` that
   "as of {date}" prose must match the most recent commit date on the
   node file, validated by a new check that reads `git log -1`. No
   schema change.

**Relationship to BACKLOG #32.** Adjacent but distinct. #32 is about
artifact-attested nuance (`note` fields, preserve-as-sic forms) not
reaching readers; this is about prose-clause currency without a
structural anchor. Both are reader-visibility issues.

**Priority.** Low. Not a correctness issue — the currency claim is
already source-attested via the underlying primary sources; the
question is whether the reader can tell when the contributor last
reviewed. Worth a single corpus-wide pass once a clear pattern emerges
across 3+ nodes.

**Scope.** ~1 session for design + schema/renderer change + per-node
sweep across affected nodes.

Surfaced: AARO web audit — auditor flagged an "as of {date}" clause
as ambiguous between rolling-currency review and forward-projected
boilerplate. Currently affects AARO; pattern likely recurs corpus-wide.

---

### 30. `archive.py --submit URL` is fire-and-forget — does not update the manifest entry on success

**The gap.** `scripts/archive.py --submit URL` submits a single URL to
the Wayback Machine via the SPN endpoint and prints the resulting
snapshot URL on success, but it does NOT touch `sources/manifest.yaml`.
The manifest's `wayback_date` and `archive_status` bit-1 update only
happens on the no-args sweep (the loop in `main()` lines 161+ that
iterates `entries` and calls `check_wayback` / `submit_wayback` per
entry).

So a contributor who runs `archive.py --submit URL` after registering a
new file ends up with a successful Wayback submission and a stale
manifest entry showing `archive_status: 1` (local only) and no
`wayback_date`. Two paths exist to recover:

- Run `archive.py` no-args (scans every entry needing a check; can take
  several minutes on a corpus of ~500+ entries; may also do unwanted
  resubmits on entries where bit 1 was previously dropped).
- Manually patch the manifest entry to set `wayback_date` + flip
  `archive_status` to 3.

Neither is a great workflow. The contributor's mental model is "I just
submitted; the manifest should reflect it."

**Concrete consequence — AARO node build.** Registered a hearing
landing page with `manifest.py add` (set `archive_status: 1`); ran
`archive.py --submit URL` which succeeded and returned a Wayback
snapshot; manifest entry remained at `archive_status: 1` with no
`wayback_date`. Resolved by manual edit. Five-minute delay; minor
friction.

**Fix sketch (renderer-only, no schema change):**

`cmd_submit_one(url)` in `archive.py` (line 134) calls
`submit_wayback(url)` and prints the result. Extend it to also:

1. Look up the URL in the manifest entries list.
2. On `ok == True`: parse the Wayback snapshot URL for the YYYYMMDDhhmmss
   timestamp, set `e["wayback_date"] = timestamp_to_date(ts)`, set
   `e["archive_status"] |= 2` (preserve existing local-bit), call
   `save_manifest(entries)`.
3. On `ok == False`: log only; don't touch the manifest.
4. If the URL doesn't appear in the manifest at all: warn explicitly
   ("URL not in manifest; submission succeeded but no entry to update")
   so the contributor knows to add it via `manifest.py add`.

**Scope.** ~30-minute change in `archive.py`; no schema work; no
other-script ripple effects (manifest read/write helpers already
exist in archive.py per `load_manifest` / `save_manifest`).

**Priority.** Low. Workaround is straightforward (manual patch or
no-args sweep). Worth fixing because the cmd-line ergonomic gap is
load-bearing — contributors will hit this every time a new
single-URL source is registered + archived in one session.

Surfaced: AARO node build — single-URL Wayback submission succeeded
but manifest entry stayed at `archive_status: 1`; manually patched
to `3` + `wayback_date`.

---

### 31. Person-node Statements section — three reader-visibility problems on one data-model decision

Replaces former #13, #14, #16. The Statements section on a person node
renders every quote attributed to that person, sorted chronologically.
Three problems surface here; they're tied together because the
data-model decision in Problem 3 shapes how Problems 1 and 2 should
be fixed.

**Problem 1 — Claim Inventory status column is undifferentiated.** On
whistleblower nodes, every filed-claim row renders with a hard-coded
`✅ Sworn / documented` label (`scripts/build-from-research.py:723`).
Real attestation tiers vary materially:

- **sworn under oath** — congressional hearing testimony
- **sworn under penalty of perjury** — formal legal filing under
  18 U.S.C. § 1001
- **DOPSR-cleared public disclosure** — pre-publication-reviewed,
  reviewed but not sworn
- **on-record interview** — podcast / broadcast / streaming with no
  attestation ceremony

A reader scanning the inventory cannot distinguish a sworn-oath claim
from a podcast claim. Fix sketch: add an optional `attestation_tier`
enum to `quote_entry` (values `sworn-oath` / `sworn-perjury` /
`dopsr-cleared` / `on-record` / `self-attested` / `unknown`); renderer
maps tier to a differentiated status label.

**Problem 2 — Q&A answer fragments render as standalone blockquotes.**
Oral testimony produces one-word answers (`"Yes."`, `"Both."`,
`"Personally, yes."`) that the verbatim-quote check passes (the byte
appears in source) but that render as full blockquote rows whose
meaning is opaque without reading the `Attributed to` cell. Corpus
state: **9 person-node quotes are sub-30 chars; 7 are Q&A answer
fragments**, 2 are legitimate terminology extracts (`"self-licking
ice cream cone"`, `"eighty-year arms race"`). Fix sketches:

- **Q&A pair schema** — optional `question` field on `quote_entry`;
  renderer emits Q + A as a paired block. Schema extension; verbatim
  check anchors both halves against source.
- **Content-rewrite discipline** — merge tight Q&A exchanges into
  single quote entries where the answer is continuous with the
  question. Schema-stable; relies on author discipline.
- **Render-time demotion** — quotes below a length threshold render
  inline (`> **Q:** … — **A:** Yes.`) rather than as standalone
  blockquotes. No schema change; renderer-only.

**Problem 3 — cross-artifact quote duplication.** A statement made by
person X at hearing Y currently lives as identical bytes in three
places: `quotes` on the person artifact, on the hearing-event
artifact, and on the hearing-transcript artifact. Corpus state: **82
verbatim passages are duplicated across 2+ artifacts** and growing
per node built. Person nodes inflate as a consequence (whistleblower
nodes can run 1000+ lines).

This is the E.3 cross-artifact-resolver question the roadmap deferred
until ~10 nodes were through the pipeline. Threshold reached. Three
paths:

- **Path A — keep duplication, polish renders.** Each artifact owns
  its own quotes. Ship Problems 1 and 2 as render-time / schema
  additions on the existing model. Duplicates persist but Statements
  becomes scannable via tier labels and Q&A handling.
- **Path B — pull E.3 forward.** Each verbatim passage lives in
  exactly one artifact (the source-owning one — transcript for oral,
  document for text-native). Person and event artifacts carry
  `quote_refs: [qid@artifact]` pointers; the renderer resolves at
  build time. Person nodes shrink as a consequence. Whistleblower
  Claim Inventory and eyewitness Direct/Other-Statements filters
  need a cross-artifact resolver — either walk every artifact where
  `speaker_path == /people/{slug}`, or build a reverse index at
  validation time.
- **Path C — hybrid.** Ship E.3 first; re-evaluate Problems 1 and 2
  on the reformed model. Tier labels and Q&A handling likely still
  useful but their shape may shift (Q&A handling moves to the source
  artifact, not the person view of it).

**F.7 dependency.** A finding node citing a quote needs a stable
reference. On the duplicated model, `q66@david-grusch` and
`q53@2023-07-26-house-grusch` resolve to the same source passage — a
finding has to pick one arbitrarily. F.7 (finding renderer, pending
in roadmap) forces this question regardless of person-node bulk
considerations. The data-model decision should land before or with
F.7.

**Lighter alternative if Path A wins.** Add a navigation affordance —
TOC jump-links at the top of nodes ≥500 lines, or collapsible
per-venue Statements subsections. Doesn't touch the data model;
addresses the scannability symptom. ~2-hour job; strictly cosmetic.

**Constraint from `meta/schema.yaml`.** Claim Inventory is defined as
*"a render-time projection of quotes tagged `category: filed-claim`.
A filter, not a separate data structure — the filed claim IS the
quote."* Path B must preserve this filter semantics across artifacts;
the filter logic moves out of the renderer's local-quote iteration
into a cross-artifact walk.

Surfaced: Grusch rebuild — three observations converged from the
same node-build session (Problem 1 from a Claim Inventory rendering
identically across all rows; Problem 2 from oral-testimony Q&A
extraction; Problem 3 from an over-long person node prompting "can
quotes be offloaded?"). One person-node session, one design decision
point.

---

### 32. Artifact-attested nuance not reaching readers — `.note` fields dropped in tables; preserve-as-sic forms unmarked in prose

Replaces former #17 and #23. Two manifestations of the same gap:
research artifacts capture source-derived evidentiary nuance in
fields that the rendered node body silently drops or under-signals,
leaving the reader with the structured surface but not the nuance.

**Manifestation 1 — table renderers drop the `.note` field across
relationship-bearing list sections.**

Eight list-section entry shapes carry an optional `note` field that
no current renderer emits:

- `org_relationships.note` — direct vs. downstream succession,
  oversight vs. parent-chartering, etc.
- `key_personnel.note`
- `contracts.note`
- `affiliations[].note` (person nodes)
- `relationships[].note` (person-to-person)
- `ownership_timeline.note`
- `uap_scope_activity.note`
- `location_relationships[].note`

The corresponding renderers in `scripts/build-from-research.py`
(`render_org_relationships`, `render_affiliations`,
`render_relationships`, `render_org_key_personnel`,
`render_org_primary_contracts`, `render_ownership_timeline`,
`render_uap_scope_activity`, `render_location_relationships`) emit
only the structured cells (e.g., Organization | Relationship |
Source) and drop `note` content. The `note` field IS rendered in
three other places — `rumors.note` (Primary-source refutation),
`corroboration_items.note` (What It Confirms column),
`media_versioning.note` (notes column) — so the gap is specifically
the eight relationship/list sections.

Concrete consequence on the AARO node: `or1` (DoD parent) and
`or5` (OUSD(I&S) supervisory) both render as bare `parent`
relationship type with no visible distinction; the late-July 2023
DEPSECDEF reporting-line shift documented in description prose has
no structural counterpart in the relationship table. Same shape
hits AARO with AOIMSG-vs-UAPTF predecessor disambiguation and the
IPMO co-location-vs-partner case — see "Note-rendering gap
manifestations" under AARO open notes in
`meta/topic/research-queue.md`. The UAPTF audit had flagged the
same pattern earlier with AARO-as-downstream-successor and
EXCOM-as-oversight collapsing into bare `other` relationship type.

**Manifestation 2 — verbatim source-form tokens in synthesis prose
appear unmarked.**

When a primary source uses a non-canonical form (auto-caption typos,
OCR artifacts, alias-of-record), contributors register the variance
as a `naming_quirks` entry with `resolution: preserve-as-sic-in-quotes`.
Currently 74 such entries across 17 research artifacts. The verbatim
form is preserved in `quote.text` (correct per source-read-first
discipline). When the same form appears in synthesis prose
(`description`, `credibility_notes`), the reader has no explicit
signal that "Bigalow Aerospace" is the source's auto-caption output
rather than a contributor misspelling.

The Grusch node uses an implicit signal — single-quoted source form
followed by a canonical wrap link, e.g. `'Bigalow Aerospace'
[`/organizations/bigelow-aerospace`]`. A discerning reader infers
the source-vs-canonical pairing from the bracket-link, but the
convention isn't documented anywhere reader-visible and other nodes
don't apply it consistently. Heaviest affected nodes:
alex-dietrich (9 entries — fraver, prinston, nits, Nimttz, Fleer,
ROC), sancorp-consulting (11 — pdftotext OCR artifacts: SuppOI1,
anached, thi s, etc.), ttsa (6 — metamateiiais, struefural),
aaro (4 — fulfi lled, etc.), david-grusch (4 — Bigalow, lockie,
Jim laty, Lou alzando).

**Why these are one gap.** Both surface artifact-attested
evidentiary nuance that the rendered output drops or under-signals.
M1 lives in the structured table-render path; M2 lives in the
prose-render / convention path. The fix shapes differ but the
diagnosis is shared: artifact metadata not reaching readers. Both
are renderer / convention layer; neither requires schema changes.
A single coordinated pass closes both gaps for past and future
nodes; per-node remediation is not required.

**Fix sketches.**

*M1 — render the `.note` field.*

1. **Display convention.** Inline-below row prose (indented
   paragraph below each row) reads more naturally for the 1–3
   sentences `note` actually carries; column-wise 4th-column
   "Notes" cell pushes long notes into unreadable wrapping on
   narrow screens. Recommend inline-below; confirm at prototype.
2. **Truncation policy.** Full render is probably right for an
   evidentiary repo — codify the convention once rather than
   per-section.
3. **Backlog-stub ghosting** (orthogonal but adjacent). If a
   note-bearing row references an unbuilt stub (e.g., UAPTF's `or9`
   → `/organizations/uap-excom`), the renderer could italicize /
   ghost the row to calibrate click-through expectations. Cheap to
   include if the renderer is being touched anyway.
4. **Enum-extension alternative considered and deferred.** Adding
   `downstream-successor` / `oversight` / `reporting-body` to
   `org_relationships.relationship_type` was rejected because the
   enum grows indefinitely as edge nuances surface, each addition
   is a schema commitment in advance of usage evidence, and
   rendering the existing `note` field achieves the same reader-
   visible outcome without schema prescription. Note rendering
   does NOT foreclose future enum tightening — if notes recur
   across many edges (e.g., 15+ rows saying "oversight body per
   Charter"), that becomes evidence-driven justification for an
   enum addition.

*M2 — signal source-form preservation to readers.*

1. **Inline `[sic]`** after verbatim source-form tokens in prose.
   Contributor discipline; no schema or renderer change.
2. **Renderer surface for `naming_quirks`** — emit a
   `## Source-Form Notes` section listing preserve-as-sic entries
   with their canonical forms. Surfaces 74 entries across 17
   nodes today; auto-applies to future entries.
3. **Backtick-quoted spans with trailing descriptor** —
   `` `Bigalow` [source form preserved] ``. More verbose than
   single-quote-plus-wrap; less ambiguous.

Documenting the single-quote-plus-wrap convention in
`meta/conventions.md` would also help, even without renderer change.

**Parallel renderer polish.** The note-render pass and the
end-only-period rendering (`period: – 2021` for bracketed-end-with-
unknown-start) are both passes over artifact content the structured
data already contains. If the renderer is touched broadly, grouping
related polish — column alignment, sort stability, header
formatting, note rendering, source-form notes — into one pass
reduces churn.

**Scope.** Corpus-wide. M1 affects every relationship/list row in
every node built and every node that will ever be built. M2 affects
74 naming_quirks entries across 17 artifacts today and grows as
auto-caption / OCR sources land in the corpus.

Surfaced: UAPTF audit (M1 — AARO and EXCOM rows displaying
identically to `other`-typed edges); Grusch v2 audit (M2 — auto-
caption verbatim forms in Credibility Notes prose read as
contributor misspellings without explicit signal). The same
node-build-audit cycle surfaced both shapes; reader-visibility for
artifact metadata is the umbrella.
