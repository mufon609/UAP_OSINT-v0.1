---
id: meta/BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

Open items are partitioned into three sections by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
and **C — Anytime** (no upstream blockers). Item identifiers are
A1, A2, ..., B1, B2, ..., C1, C2, ... — within each section,
retired items leave a gap rather than shifting remaining IDs, so
git-log and commit-message references stay valid. The same
gap-stable policy in `meta/conventions.md` applies to validator
check names.

**Default focus: Section C.** C items have no upstream dependencies
and can be picked up and finished in a single pass. A and B items
carry ordering or coupling constraints — starting one without its
dependencies risks half-baked implementations and leaves the BACKLOG
cluttered with partial work. For ad-hoc sessions, prefer C work.
Reserve A and B for sessions explicitly scoped to those tracks.

Items waiting on an external event the repo can't drive (FOIA
resolution, registry access, third-party publication) and that are
**topic-specific** to the current investigation live in
`meta/topic/research-queue.md` "Externally blocked" — that's the fork-
boundary-correct home for them. If a genuinely toolkit-neutral
externally-blocked item ever surfaces (rare), reinstate the
"Externally blocked" heading at the bottom of this file.

---


## A. Priority sequence

Items with ordering or coupling constraints. A3 carries person-node
Statements polish work that ships cleanly against the
quotes-per-artifact model (each artifact owns its own quotes — the
data-model question is closed).

### A3. Person-node Statements section — Claim Inventory tier labels

The Claim Inventory section on whistleblower nodes renders every
filed-claim row with a hard-coded `✅ Sworn / documented` label (in
`scripts/build-from-research.py` — grep the literal string). Real
attestation tiers vary materially:

- **sworn under oath** — congressional hearing testimony
- **sworn under penalty of perjury** — formal legal filing under
  18 U.S.C. § 1001
- **DOPSR-cleared public disclosure** — pre-publication-reviewed,
  reviewed but not sworn
- **on-record interview** — podcast / broadcast / streaming with no
  attestation ceremony

A reader scanning the inventory cannot distinguish a sworn-oath claim
from a podcast claim. Schema already carries `attestation_tier` on
`quote_entry` (values `sworn-oath` / `sworn-perjury` / `dopsr-cleared`
/ `on-record` / `self-attested` / `secondary-source`) but scoped to
finding artifacts only — the entity-node Claim Inventory renderer
ignores it. Fix: lift the schema scope to entity quotes too, wire the
renderer to map tier → label, and backfill `attestation_tier` on
existing whistleblower filed-claim entries.

Surfaced: Grusch rebuild — Claim Inventory rendered identically
across every row regardless of whether the underlying attestation
was sworn House testimony, an IC IG complaint, or an on-record
podcast statement.

---

## B. Parallel batch (renderer pass)

Items that touch the renderer and naturally batch into a single
polish pass — bundling reduces churn vs. shipping each as a
separate touch.

### B2. `updated` frontmatter field — corpus-wide currency anchoring

**The gap.** Schema-required frontmatter across all content types
is `[id, type, schema_version, status, kind, created]`. There is no
`updated` or `last_modified` field. Body prose periodically carries time-anchored
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

A. Add `updated:` (or `last_reviewed:`) to schema.yaml frontmatter
   `optional` set across all content types. Contributors stamp it
   when a node receives a content-currency review. Renderer surfaces
   it in the Overview row or as a node-foot annotation. Cheap;
   opt-in; no enforcement of refresh cadence. Risk: contributors
   forget to stamp.

B. Move "as of {date}" prose into a structured `currency_anchors`
   list. Each anchor: `clause` + `as_of_date` + `source.path`.
   Renderer composes the prose at build time. Heavier; forces the
   review discipline at the schema layer; surfaces the audit trail
   structurally.

C. Convention-only. Document in `meta/conventions.md` that "as of
   {date}" prose must match the most recent commit date on the node
   file, validated by a new check that reads `git log -1`. No schema
   change.

**Scope shape.** Distinct reader-visibility concern from the now-
closed artifact-attested-nuance work (where `.note` content sat in
YAML without reaching readers). This entry is about prose-clause
currency without a structural anchor.

**Priority.** Low. Not a correctness issue — the currency claim is
already source-attested via the underlying primary sources; the
question is whether the reader can tell when the contributor last
reviewed. Worth a single corpus-wide pass once a clear pattern emerges
across 3+ nodes.

**Scope.** Design decision (which of the three options) + schema /
renderer change + per-node sweep across nodes carrying rolling-
currency clauses.

Surfaced: AARO web audit — auditor flagged an "as of {date}" clause
as ambiguous between rolling-currency review and forward-projected
boilerplate. Currently affects AARO; pattern likely recurs corpus-wide.

---

## C. Anytime (no dependencies)

Items with no upstream blockers; safe to pick up at any point in
any session. Per the preamble, this is the default-focus tier:
C work doesn't risk half-baked implementations.

### C3. Provenance-marker treatment on document node Provenance tables

Document nodes render a `## Provenance` section that tracks the
custody chain of the source file (authoring date, submission venue,
local archival, etc.). Rows use a `✅ Confirmed —` marker pattern
with evidence descriptions — for example, "PDF metadata CreationDate:
Sun Jul 23 14:41:22 2023 EDT" / "hosted at oversight.house.gov" /
"SHA256 verified via sources/manifest.yaml".

**Question surfaced during Phase B** of A2's marker-removal work:
with the per-quote `Verified` marker removed under Phase E's "no
rendered trust claim" principle, should these per-row Provenance
markers be removed too?

**Analysis from the Phase B discussion**:
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
SHA256 case. That's different analysis from the Phase F corpus
audit and deserves its own design pass.

**Recommendation.** Defer. Not a correctness issue (Provenance rows
are factual metadata with evidence attached; the marker is a
shorthand summary); not a readers-being-misled issue (prose names
the evidence). The analysis is genuinely different from A2 — the
removal pattern from A2 would be wrong if applied here.

**Scope if taken up.** Per-provenance-row audit: categorize each
marker's underlying evidence by checkability (SHA256-level / tool-
required / external-attestation); tighten wording to surface the
distinction where useful; or decide the current pattern is fine
given Phase E's principle doesn't scope to Provenance tables.

Surfaced: Phase F spot-check review of `✅ Confirmed —` patterns in
rendered nodes — Provenance markers share the marker pattern with
the per-quote Verified row but don't share the trust-performance
shape.

---
### C8. Quote.text leading-timestamp discipline — drift between in-text marker and actual quote-start

The existing convention in
`feedback_transcript_timestamps_in_quotes.md` codifies that quote.text
on caption-source quotes carries at most ONE leading `[MM:SS]` marker
as the navigation anchor, with intermediate markers stripped. Two
failure modes the memory doesn't address have surfaced in the corpus.

**1. Drift between leading marker and quote-start.** The in-text
leading `[MM:SS]` is sometimes 4-9 seconds AFTER the source line where
the quote's first content word appears. The marker still lands on
quote content (not adjoining material) but doesn't anchor the actual
start. Reader clicking through to navigate lands mid-quote, missing
the start. Concrete cases (alex-dietrich, surfaced in 2026-05-04
cluster-1 re-review):

| qid | in-text marker | actual start in source | drift |
|---|---|---|---|
| q17 | `[1:00:56]` | `[1:00:48]` | +8s |
| q18 | `[1:02:00]` | `[1:01:51]` | +9s |
| q19 | `[5:25]`    | `[5:19]`    | +6s |
| q21 | `[56:42]`   | `[56:34]`   | +8s |
| q23 | `[19:37]`   | `[19:30]`   | +7s |
| q25 | `[15:26]`   | `[15:24]`   | +2s |
| q28 | `[58:44]`   | `[58:40]`   | +4s |
| q38 | `[9:24]`    | `[9:20]`    | +4s |
| q40 | `[13:45]`   | `[13:41]`   | +4s |

None observed in david-grusch caption-source quotes — pattern appears
contributor-specific (alex-dietrich and david-grusch were authored in
different sessions).

**2. Intermediate markers retained in quote.text.** Two david-grusch
quotes carry interior `[MM:SS]` markers explicitly forbidden by the
existing memory:

| qid | text snippet | extra marker(s) |
|---|---|---|
| q21 | `know, isotopic ratios that would have to [13:05] be engineered…` | `[13:05]` |
| q29 | `so I was a Intel officer [0:36] in the Air Force for 14 years…` | `[0:36]` |

**Why this is its own item.** Both failure modes are quote.text
content issues, distinct from the location-ref form addressed by C1.
C1 closes the location-ref dimension; this item closes the in-text
marker dimension. Combined, the two close out the timestamps-memory
convention end-to-end.

**Why deferred from C1.** Phase C of C1 is location-ref-only by
design — touching quote.text during a location-ref conversion would
mix two discipline axes and risk drift. Cluster 1 of C1 (2026-05-04)
preserved the contributor's leading markers verbatim to keep the
rendered blockquote anchor consistent with the Location row;
tightening the in-text marker requires its own pass that updates
both quote.text AND source.location together so they stay aligned.

**Fix sketch.**

1. **Detection.** Either extend `scripts/normalize-locations.py` with
   a `--text-markers` mode or write a small sibling script. Per
   caption-source quote:
   - Extract leading `[MM:SS]` from quote.text (when present).
   - Find the source line where the quote's first 4-6 content words
     appear.
   - Compare timestamps; flag drift >5 seconds.
   - Detect intermediate `[MM:SS]` markers in the quote.text body.

2. **Per-quote correction.** For each flagged quote:
   - Replace the leading `[MM:SS]` with the actual-start timestamp.
   - Strip intermediate markers.
   - Update `source.location` to match the new leading marker
     (preserves blockquote/Location-row consistency).
   - Regenerate the rendered node body via `build-from-research.py`.

3. **Memory update.** Add a sentence to
   `feedback_transcript_timestamps_in_quotes.md`: leading `[MM:SS]`
   matches the timestamp on the source line where the quote's first
   content word appears, not a later caption tick the contributor
   encountered while reading. Include one drift case as a concrete
   example.

**Scope.** 11 currently flagged quotes (9 drift + 2 intermediate-
markers), all in alex-dietrich and david-grusch. Bounded — only
caption-source quotes are at risk. Future caption-source quote
authoring uses the updated memory.

**Priority.** Low. Not a correctness issue; navigation-precision
improvement. Validator doesn't care.

Surfaced: Cluster 1 conversion re-review (2026-05-04) — spot-check
of converted location refs against source content surfaced both
failure modes.

---
### C25. Render `disputed` naming_quirks alongside `preserve-as-sic-in-quotes`

`naming_quirks` entries with `resolution: preserve-as-sic-in-quotes`
auto-render in a `## Source-Form Notes` table near the foot of every
node body (BACKLOG B1 M2, shipped 2026-05-13). Entries with
`resolution: disputed` carry the same evidentiary character — the
contributor has recognized that two primary sources attest opposing
forms of the same fact and chosen not to adjudicate — but currently
render nowhere on the node body. The explicit "this disagreement is
recognized and unresolved" flagging stays investigator-only in the
YAML.

**Surfacing case.** AARO node `naming_quirks.nq4` (Mt. Etna 170m vs
170km) registers the dispute between AARO's slide-deck attestation
("approximately 170 kilometers from the volcano", q54) and Kosloski's
oral SASC testimony ("170 meters away from the plume", q25). Both
verbatim quotes are preserved in Key Passages, so a careful reader
encountering both quotes sees the disagreement in the primary-source
content directly. What's missing is the explicit corpus-level flag
that this disagreement is recognized and unresolved — currently only
in the YAML nq4 entry, not on the body.

**Fix sketch.** Extend the Source-Form Notes renderer (or add a
parallel section like `## Preserved Disagreements`) to surface
`resolution: disputed` naming_quirks entries. Columns could be:
Observed form | Disputed counterpart | Source A | Source B | Note.
Auto-suppressed when no qualifying entries exist, parallel to the
existing Source-Form Notes suppression.

**Priority.** Low. Not a correctness issue; reader-visibility
extension. The disagreement is already visible to a careful reader
in Key Passages; this surfaces it explicitly.

**Scope.** Renderer extension + brief conventions.md note. Likely
one Phase II render-pass + a doc paragraph in
`meta/conventions.md` "Contradictions" section.

Surfaced: 2026-05-13 D4 explanation during F.7 scope design —
eliminating the AARO "open notes" research-queue.md surface as a
philosophy violation surfaced that the explicit disagreement
flagging for nq4 only lives in the YAML, not on the body.
