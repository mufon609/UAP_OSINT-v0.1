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

Items with ordering or coupling constraints. A3 is coupled to
roadmap F.7 (finding renderer); A4 pairs with F.7. Pick up in
this order; do not skip ahead without the upstream piece in
place.

### A3. Person-node Statements section — three reader-visibility problems on one data-model decision

Replaces former #13, #14, #16. The Statements section on a person node
renders every quote attributed to that person, sorted chronologically.
Three problems surface here; they're tied together because the
data-model decision in Problem 3 shapes how Problems 1 and 2 should
be fixed.

**Problem 1 — Claim Inventory status column is undifferentiated.** On
whistleblower nodes, every filed-claim row renders with a hard-coded
`✅ Sworn / documented` label (in `scripts/build-from-research.py` —
grep the literal string).
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
state: 9 person-node quotes are sub-30 chars; 7 are Q&A answer
fragments; 2 are legitimate terminology extracts
(`"self-licking ice cream cone"`, `"eighty-year arms race"`).
Fix sketches:

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
artifact, and on the hearing-transcript artifact. Corpus state: 82
verbatim passages are duplicated across 2+ artifacts, and the
duplication grows per node built. Person nodes inflate as a
consequence (whistleblower nodes can run 1000+ lines).

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
addresses the scannability symptom. Strictly cosmetic.

**Constraint from `meta/conventions.md`.** Claim Inventory is
defined as *"a render-time projection of quotes tagged
`category: filed-claim`. A filter, not a separate data structure —
the filed claim IS the quote."* Path B must preserve this filter
semantics across artifacts; the filter logic moves out of the
renderer's local-quote iteration into a cross-artifact walk.

Surfaced: Grusch rebuild — three observations converged from the
same node-build session (Problem 1 from a Claim Inventory rendering
identically across all rows; Problem 2 from oral-testimony Q&A
extraction; Problem 3 from an over-long person node prompting "can
quotes be offloaded?"). One person-node session, one design decision
point.

---

### A4. Rename `finding` → `investigation` + redesign type

Mechanical rename plus a design pass. The `finding` type will be
renamed to `investigation`; the redesign will decide what synthesis
surface an investigation node carries. See **Redesign pass** below
for the open design questions.

**Rename surfaces** (mechanical):
- `meta/schema.yaml` — `types.finding` block + `conditional_keys`
  rule for `timeline.required_when_any_of` (which lists `finding` as
  a target_node_type) + ~6 enum-list references
- Scripts — `DIRS` maps, `new.py` argparse, `validate.py`
  `node_type == "finding"` branch, any `if node_type == "finding":`
  branches in build-from-research.py / associate.py / build-state.py
  (total: 8 scripts). The scaffolder (research-scaffold.py) reads the
  type list from schema.yaml directly (since the conditional_keys
  refactor), so its rename is driven by the schema edit alone.
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

Surfaced: Open-Questions section removal — the rename was
deliberately deferred to a later session rather than bundled with
the removal.

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

### C10. Subdivide `meta/toolkit-notes/` when retrospective files accumulate

`meta/toolkit-notes/` currently holds three long-form retrospective /
design files: `corpus-audit-2026-04.md` (Phase F corpus-audit
closeout), `cross-artifact-consistency-check.md` (technique doc
surfaced from the location-reference normalization work),
`pilot-failure-2026-04-17.md` (Step C postmortem). At
n=3 a flat directory reads fine. As the toolkit accumulates more
closeouts and design records, the directory will get noisier than
scannable.

**Trigger to revisit.** When `meta/toolkit-notes/` reaches ≥5
long-form retrospective files, propose a subdivision convention.
Likely shape: `closeouts/` for retired-audit closeouts (corpus-audit-
2026-04 as the canonical example), root for forward-looking
design / technique notes (cross-artifact-consistency-check as the
canonical example). Sort-by-year and sort-by-topic are alternative
shapes; decision lands when n≥5 makes the comparison concrete.

**Why deferred.** Three files don't justify subdivision — *"don't
design for hypothetical future requirements"* per CLAUDE.md. Trigger-
on-accumulation lets the structure emerge from real data rather
than imposing it speculatively.

**Priority.** Low. Pure tidiness; no correctness implications.

**Scope.** When triggered: 30-min design pass + N file moves +
cross-reference updates (no current refs traverse to specific
files within `toolkit-notes/`).

Surfaced: 2026-05-05 governance-doc reorganization — original
investigation flagged `corpus-audit-2026-04.md` as a candidate for
"some reorganization" but determined three files don't justify
forcing shape; codified the trigger condition here.

---

### C23. Honor `Issue.fatal` in the post-parse main check loop

**The gap.** The validator decomposition shipped with this per-file
iteration contract:

> Per-file loop: (1) pre-parse checks on raw lines; (2) parse +
> Context construction; if parse fails or frontmatter absent, emit
> fatal Issue and continue to next file; (3) post-parse checks; abort
> remaining checks for that file on any fatal Issue (per Q1 — confirmed).

The orchestrators currently honor (1) and (2) — preflight checks short-
circuit `_NODE_CHECKS` / `_ARTIFACT_CHECKS` / `_REVIEW_CHECKS` on any
fatal Issue. They do NOT honor the same contract for (3). The main
check-dispatch loops are unconditional ``for check_module in
_NODE_CHECKS: issues.extend(check_module.check(node_ctx))`` patterns
with no fatal-Issue inspection.

**Why latent.** No main-loop check yields ``fatal=True`` today. Every
fatal Issue currently emitted comes from a preflight module
(``frontmatter_parse``, ``artifact_parse``, ``manifest_parse``,
``phase_iii_inputs``). So the gap doesn't manifest as a behavior bug
on the current corpus — but the contract the design doc declared is
half-implemented, and the next contributor adding a fatal-yielding
main-loop check would discover the mismatch.

**Concrete near-term motivator.** The Finding-F investigation surfaced
the layering gap between ``status_archetype_kind`` and downstream
checks that depend on a valid archetype/kind value (currently
``required_sections`` handles invalid arch/kind via explicit early-
return + direct subscript, per the Finding-F local fix). A more
principled architecture would: (a) make ``status_archetype_kind``
yield ``fatal=True`` on invalid arch/kind, (b) have the orchestrator
short-circuit the rest of ``_NODE_CHECKS`` on that fatal, (c)
downstream checks rely on the value being valid without explicit
guards. C23 is the orchestrator-side prerequisite for that chain.

**Three orchestrators to update** (same shape change in each):

  - ``scripts/validate.py::validate_node`` — main loop is
    ``for check_module in _NODE_CHECKS: issues.extend(...)``;
    add ``if any(i.fatal for i in fresh_issues): break`` semantics.
  - ``scripts/validate-research.py::validate_artifact`` — same shape
    over ``_ARTIFACT_CHECKS``.
  - ``scripts/review-coverage.py::review_artifact`` — same shape
    over ``_REVIEW_CHECKS``.

**UX trade-off.** With fatal-chain in the main loop, contributors see
ONE error per fix-cycle (root cause first). Without it, they see ALL
related errors at once, which is sometimes useful for batch fixes
(e.g., a renamed file producing both id-path-mismatch and broken-link
issues). Decision is not obvious; either model is defensible.

**Recommendation.** Decide the UX question first; the implementation
is mechanical once the contract is agreed. Likely outcome: honor
fatal in the main loop, since the alternative (status quo) means the
``fatal`` field on Issue is half-honored — which is itself a contract
inconsistency.

**Scope.** ~15 lines per orchestrator (insert fatal-check after each
check_module call). Optional follow-up: promote
``status_archetype_kind`` errors to ``fatal=True`` and remove the
explicit early-return guards in ``required_sections`` (rebound by the
fatal short-circuit instead).

**Priority.** Low. Latent, no current corpus impact. Worth resolving
before any future check is added that genuinely needs to halt the
chain on a discovered defect.

Surfaced: Finding F investigation during the audit-of-audit pass —
the orchestrator's fatal-handling asymmetry between preflight and
main loop became visible while comparing layering options.

---

### C24. Wrap ``check_module.check(ctx)`` calls in try/except — convert unhandled exceptions to fatal Issues

**The gap.** Each orchestrator's main check-dispatch loop is an
unguarded ``for check_module in _NODE_CHECKS: issues.extend(
check_module.check(node_ctx))``. If a check raises an unexpected
exception (TypeError on an unanticipated input shape, AttributeError
on a refactor mismatch, KeyError where the silent-fallback sweep
tightened a schema lookup but missed a corner case), the exception
propagates up
through ``main()`` and crashes the validator with a Python traceback
— taking the rest of the per-file iteration with it. Contributors see
a stack trace instead of a check-named Issue, AND any other defects
in the same node (or other nodes) go unreported.

**Why latent.** No check yields exceptions in normal operation today.
The silent-fallback sweep tightened many ``.get(..., default)``
fallbacks to direct subscripts which DO raise KeyError on schema
drift — but every site tightened was on a path the schema is
guaranteed to populate, and the corpus passes pre-commit clean. So
the latent failure mode hasn't manifested.

**UX trade-off, same shape as C23.**

  - Catch + convert to fatal Issue: validator never crashes; one
    buggy check reports cleanly and the iteration continues. Risk:
    hides actual bugs in checks during development.
  - Don't catch (status quo): exceptions are loud during dev, but
    contributors hitting an edge case see a traceback instead of a
    diagnostic.

A reasonable middle ground: catch + fatal-Issue with the exception
type + message + check_name in the Issue; iteration continues.
Contributors see "check X crashed with Y" rather than a traceback;
the failure is in the Issue stream so other checks still run. Bugs
during dev still surface (the Issue prints the traceback inline).

**Scope.** ~10 lines per orchestrator — wrap ``list(check_module
.check(ctx))`` in try/except, build an Issue with the check_module's
``CHECK_NAME`` (or the module's ``__name__`` if CHECK_NAME isn't
exposed), append to the issues list. Three orchestrators:
``validate.py::validate_node``, ``validate-research.py
::validate_artifact``, ``review-coverage.py::review_artifact``.

**Coupled to C23.** Both items are about the orchestrator's
exception-handling contract for the main check-dispatch loop. C23
handles ``Issue.fatal=True`` short-circuit; C24 handles exceptions
that escape the check entirely. Decide both UX questions in the same
session if either is taken up — the design pressure is similar.

**Priority.** Low. Latent today. Pairs naturally with C23 if either
is promoted.

Surfaced: audit pass after the contributor-script catch-up bundle
(commit 7ecf6ad) — verifying orchestrator robustness on bad CLI
paths exposed Q (mechanical, fixed in same commit-sequence) and
this latent design gap.


