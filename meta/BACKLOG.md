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

*No anytime items currently open.*
