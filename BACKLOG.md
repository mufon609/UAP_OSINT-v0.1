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
`validate.py` remains at ~693 lines; full refactor still gated on the
~800-line trigger or contributor confusion.

---

### Validator scope expansion to meta files — ✅ RESOLVED 2026-04-17 (commit 30b7fc3)

Check #13 `check_governance_files()` in `scripts/validate.py` walks
`meta/` recursively and enforces the governance-file frontmatter
discipline exactly as proposed in the original entry:

- Every `.md` under `meta/` must carry `id / type / schema_version /
  created`
- `schema_version` must appear in `schema.compatible_with`
- `id` must match the file path
- Templates are routed through a placeholder-aware regex check because
  their `{{slug}}` / `{{today}}` values aren't YAML-parseable cleanly
- No `type`-specific section requirements for meta files

Entry retained as audit trail through ~2026-07 (~3 months); then
delete with a note in `meta/toolkit-notes/roadmap.md`'s history if
useful or drop silently. The roadmap's Step A/B/C section already
captures the high-level scope; this entry's resolution needs no
further roadmap note.

**Original surface.** Step A/B/C audit → follow-up assessment
2026-04-17 (P3). Deferred at that time in favor of B-series bug fixes.
**Shipped.** commit 30b7fc3 ("Add check #13 — governance-file
frontmatter validation"), 2026-04-17.

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

**Proposed scope.** Start small, scale with need:

1. **Immediate**: `tests/help-check.sh` — calls `--help` on every
   script in `scripts/`; confirms exit 0 and no Python traceback.
   Catches argparse regressions, syntax errors, and import failures.
   **Shipped 2026-04-17.** 13/13 scripts pass. Referenced from
   `CLAUDE.md` §5.
2. **Next**: fixture-based smoke tests — one scaffold per node type
   with known-good flags; validate.py exits clean on the scaffold;
   scaffold is deleted. A single `tests/smoke.sh` runs the whole
   set. **Shipped 2026-04-17** (commit f5760c0); updated 2026-04-18
   with media/article/book/social-post/transcript-other fixtures
   post-source-taxonomy-consolidation. 23/23 passing.
3. **Eventually**: unit tests for specific check functions in
   `validate.py` (quote normalization, checksum computation,
   verification-block parsing, `evaluate_condition` parser). These
   are the highest-leverage unit tests because the check logic is
   where correctness matters most.
4. **Continuous**: a pre-commit hook (or CI equivalent) that runs
   help-check + smoke + validate.py before any commit lands.
   **Shipped 2026-04-18** (`tests/pre-commit.sh`). Chains
   help-check + smoke + validate.py + validate-research.py +
   build-state.py --check + audit-schedule.py --overdue. Install
   instructions in-file; not auto-installed (git-hook installation
   is explicit opt-in).

The first two are small, script-level, and low-risk. Unit tests and
CI are bigger structural commitments.

**Surfaced.** Step A/B/C audit (W1, 2026-04-17). Upgraded to BACKLOG
after P1 smoke test caught a real latent bug, demonstrating that the
lack of automated testing is not theoretical.

**Progress.** Steps 1, 2, and 4 shipped. Step 3 (unit tests) remains
open — deferred until a check function actually needs bug-hunting or
the validator monolith refactor (separate BACKLOG item) makes
function-level testing more natural.

---

### Description field: move to agent-generated (currently human-authored)

**Issue.** `research-artifact.description` is a free-text prose field the
contributor writes by hand during Phase I. It renders directly as the
node's `## Description` section. This is intentionally simple for D.3
(Option A: the artifact stores the prose, the build just passes it
through). The long-term goal (Option B) is to derive the description
programmatically from the artifact's structured fields
(`document_intrinsic`, `claims`, `entities_referenced`, etc.) so that
the description can never drift from the artifact's evidentiary layer.

**Why it matters.** Hand-written descriptions are a reintroduction of
the Phase 2 v1 failure surface: prose that "feels true" but isn't
strictly derivable from the artifact's claims/quotes. A programmatic
derivation (or a tightly-bounded agent-task that reads only
document_intrinsic + claims + quotes) would close that surface.

**Proposed scope.** Two possible directions, to be evaluated once more
artifacts have been built under Option A:

1. **Deterministic template** — a per-node-type template that
   interpolates artifact fields into a fixed-shape description. Works
   when descriptions follow predictable patterns (e.g., for documents:
   "{Internal title} — {author}'s {doc_form} submitted {date} for
   {hearing/venue}. The document opens with {first claim statement}…").
   May feel mechanical; sacrifices narrative flexibility.

2. **Bounded agent task T7** — an agent reads
   `document_intrinsic + claims + quotes + entities_referenced` and
   produces a 1-3 paragraph description whose every factual statement
   is traceable to a specific artifact entry. A coverage checker
   confirms the generated description cites no claim not in the
   artifact. This preserves narrative voice while enforcing
   evidentiary bounds.

**Interim decision.** Option A (human-authored `description` field in
research artifact) for D.3. Re-evaluate after 10+ document nodes are
built through the full Phase I → II pipeline.

**Surfaced.** D.3 design (2026-04-17 Q2).

---

### Extend build-from-research.py to all 8 node types

**Issue.** `scripts/build-from-research.py` ships in D.3 supporting
**document** nodes only. F.1b (2026-04-19) added **person** support.
Organization, event, transcript, media, location, and finding node
regeneration is not yet implemented.

**Why it matters.** Phase II of the layered build process is defined
as "deterministic regeneration from research artifact." Until all node
types are supported, the Phase II discipline is only partially
enforceable — contributors building a person or organization node
must still hand-author the body, which reintroduces the fabrication
surface that the layered process exists to close.

**Proposed scope.** Per-type section renderers. Each node type's
required sections map to specific artifact fields or to type-specific
conventions:

- **person** — Identity, Background, UAP Relevance, Affiliations, Key
  Statements, Relationships, Corroboration / Claim Inventory /
  Program Involvement / Publication Record (by archetype),
  Credibility Notes, Associated Nodes, Open Questions. Requires new
  artifact conventions for `biographical_data`, `corroboration_items`,
  `claim_inventory`, `program_involvement`.
- **organization** — Overview, Description, Key Personnel, What Is
  Confirmed, Timeline, Relationships. Requires `key_personnel`,
  `timeline`, `contracts` (gov-contractor) fields in artifact.
- **event** (hearing / encounter) — Participants split by
  evidentiary category, Timeline, Key Testimony, Corroboration.
- **transcript** — Publication Record, Summary, Speakers, Key Passages,
  Material Differences (hearing only). Kind `other` covers interview,
  podcast, broadcast, documentary, press conference, conference talk.
- **media** — Media Summary, Description, Provenance, Key Passages
  (optional — verbatim speech / visible text), Media Versioning
  (when derivation_of set). Four kinds: photo, video, audio,
  imagery-other.
- **location** — Ownership Timeline, UAP-Scope Activity, Relationships.
- **finding** — Timeline, Primary Source Basis, What This Establishes,
  Entities Involved.

Extending per-type will likely expand the artifact schema with
type-specific required fields. Each extension should be landed as a
separate, pilot-tested increment (one type per change), not as a big-bang
multi-type rollout.

**Surfaced.** D.3 design (2026-04-17 Q4). Deferred in favor of
shipping document-type support first, piloting end-to-end on the
Fravor node (D.5), and learning from observed failure modes before
scaling.

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

### Audit-cadence defaults may need type-specific tuning

**Issue.** Research artifacts carry `audit_cadence_days` on every
entry — how long until the entry should be re-verified against its
source. D.0 design originally proposed type-specific defaults
(180-day for claims, 365-day for quotes, on-demand for entities).
Adopted a single 365-day default across all entry types for initial
implementation to reduce complexity. This may turn out to be
wrong in either direction:

- **Too slack for volatile claims.** "Person X currently holds role
  Y" can become stale within weeks, not a year.
- **Too aggressive for stable quotes.** A verbatim passage from a
  fixed-date hearing transcript doesn't change meaning over time;
  365-day re-audit on hundreds of quote entries is busywork.

**Why it matters.** Audit scheduling only works if the cadence
reflects reality. A schedule that over-schedules stable content
gets ignored; one that under-schedules volatile content misses
staleness. Either failure mode erodes the audit system's
credibility.

**Proposed scope.** After research artifacts accumulate (say, 20+
artifacts built through the full Phase I → II → III pipeline),
analyze:

- Which entry types actually go stale? (check by spot-auditing)
- Are contributors overriding the 365 default frequently? If so, to
  what values?
- Do some entry types (institutional claims, "current role" claims)
  exhibit faster drift than others?

Based on observed patterns, either:

- Keep the single 365-day default (simplicity wins)
- Reintroduce type-specific defaults (180 claims / 365 quotes /
  on-demand entities from D.0 design)
- Introduce claim-subtype-specific defaults (e.g., claims tagged
  as "current state" get shorter cadence than historical claims)

**Interim decision.** Single 365-day default across all entry types
until enough data exists to tune.

**Surfaced.** D.0 design review (2026-04-17). Deferred in favor of
shipping Phase I tooling.

---

### F.1a descriptive-only gaps (follow-on to #9)

**Issue.** Three F.1a schema additions are declarative but not yet
mechanically enforced. Behavior is correct today (hand-authored
content follows the convention; the F.1b renderer will enforce at
build time), but the gap between what schema documents and what the
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

   **F.1b resolution (partial).** The Phase II person renderer now
   sorts statements at render time by `statement_date` (a new optional
   field on `quote_entry`). Under Boundary-check discipline (review-
   coverage.py check 2), renderer-driven nodes can't diverge — any
   attempt to hand-reorder statements would fail Boundary when
   review-coverage runs. So the renderer enforces order on the
   happy path. Remaining gap: validate.py check #15 doesn't
   independently verify block-quote ordering from the node body
   alone, so a hand-authored person node built without the renderer
   pipeline could drift silently. Accepted as a limitation until a
   hand-authored person node is attempted (not on the roadmap).

3. **`chronological: true` section-rule flag is now descriptive.**
   The flag appears on six section_rules in schema.yaml (person
   Timeline, organization Timeline, event Timeline, finding Timeline,
   document Provenance, media Provenance, location Ownership
   Timeline). Check #15 actually runs universally on every
   date-bearing table regardless of whether the flag is set — so
   having the flag is strictly documentation of which sections the
   rule applies to. Two paths:
   - Leave as-is. Universal enforcement is simpler; the flag
     signals intent to contributors reading schema.yaml.
   - Make check #15 read the flag and scope only to flagged
     sections. Stricter but risks false negatives (future
     date-bearing tables that don't get the flag).

   My lean: leave as-is. The flag is a contributor-facing
   documentation aid; the enforcement is universal by design.

**Surfaced.** F.1a audit (2026-04-19).

---

### F.1b audit findings — descriptive-only and forward-looking

Four F.1b observations. Items 1 and 2 shipped in the 2026-04-19 pre-
F.1c hardening pass; items 3 and 4 remain open but reframed.

1. **`quote_verification_fields.required` (schema) — ✅ RESOLVED
   2026-04-19.** Schema listed `[Attributed to, Source, Verified]` as
   required rows in a verification block, but `validate.py` only
   enforced `Verified`. Fix path chosen: require `context` on person-
   artifact quotes (input-side discipline) so the renderer always has
   material for the Attributed-to row. Shipped via
   `validate-research.py` check_quotes extension + schema comment on
   `quote_entry.context`.

2. **`document_intrinsic` convention for person artifacts — ✅
   RESOLVED 2026-04-19.** Schema's required_keys comment now
   enumerates per-type key conventions: `document` uses
   internal_title / authors_per_document / classification / pages /
   etc.; `person` uses full_name / aliases / nationality / profession.
   Future renderers (F.2+) document their keys in the same comment as
   they ship.

3. **Name lookup for cross-reference cells.** F.1b emits cross-
   reference paths as backtick-bracket wraps (``[`/organizations/aaro`]``)
   in table cells where the template expects a display name (e.g.,
   Organization column of Affiliations). Today the rendered cell
   shows the path; an investigator reads "us-navy" instead of
   "U.S. Navy". Enhancement: look up the display name from
   `entities_referenced.name` (where `wrap_path` matches the target
   path) or from the target node's frontmatter if the node exists.
   Renderer complexity bump; low urgency because backtick-bracket
   paths render as clickable links and the meaning is recoverable.

4. **entities_referenced vs cross-reference lists — reframed
   2026-04-19 as separation-of-concerns, not duplication.** Initially
   flagged as redundant (paths in affiliations / relationships /
   corroboration_items / etc. must also appear in
   entities_referenced for stub-linking to fire). On reflection the
   two lists serve different purposes:

   - `entities_referenced` — entities named in *quote text*. The
     contributor curates this list from the verbatim passages they
     registered. Stub-linking checks that every listed entity appears
     somewhere in the rendered body (catches: contributor wrote a
     quote mentioning "Kelleher" but forgot to wrap him as
     `[`/people/colm-kelleher`]` anywhere).
   - **Cross-reference lists** (affiliations / relationships /
     corroboration_items / program_involvement / publication_record /
     vouching_chain) — structural relationships with their own path
     fields. The renderer emits them as backtick-bracket links
     automatically. `associate.py` picks them up for the Associated
     Nodes section. No contributor curation of entities_referenced
     needed for these.

   **Convention for contributors:** populate `entities_referenced`
   with entities named in quote text only. Don't duplicate paths that
   already appear in structured cross-reference lists. Stub-linking
   will still fire correctly — it just won't check paths that aren't
   in entities_referenced, and those paths don't need it (they're
   already linked via the cross-reference table render).

   No code action required. Documenting this note closes the "gap"
   as a design-clarity win, not a bug.

**Surfaced.** F.1b audit (2026-04-19).
**Shipped items 1 and 2.** 2026-04-19 pre-F.1c hardening pass.
**Reframed item 4.** 2026-04-19 (same pass).

---

### Corroboration table's `Source` column displays the attesting document, not the corroborator (F.1c finding)

**Issue.** The Corroboration section on eyewitness person nodes
renders with a `Source | Type | What It Confirms | Node Link`
template header. F.1b's renderer puts the artifact's
`corroboration_items[i].source.path` (the PDF where the corroboration
fact is attested) in the `Source` column, and the `observer_path`
(who/what corroborates) in the `Node Link` column. Investigator
scanning the table sees the attesting document first and the
corroborator last — backwards from the natural "who corroborates?
via what evidence?" reading order.

F.1c Fravor pilot made this visible: the Corroboration table's first
column reads `government/oversight-...fravor-...2023.pdf` three
times in a row (all three corroboration items are attested by the
same PDF), with the actual corroborators (Dietrich, USS Princeton,
FLIR1 video) hidden in the rightmost column.

**Why it matters.** Corroboration is a navigational surface — the
investigator's first question is "who corroborates?" and the column
layout should answer that question first. The attesting-document
column, if kept, should be secondary. Not an evidentiary integrity
issue (all facts are correct); purely a readability / template-
renderer mismatch.

**Proposed scope.** Two options:

1. Rename columns + swap order. Template becomes
   `| Observer | Type | What It Confirms | Attested In |`,
   renderer emits observer_path (wrapped as backtick-bracket link)
   in column 1 and source.path in column 4. Keeps all four cells;
   fixes reading order. Investigator-friendly.

2. Drop the attesting-document column entirely. Template becomes
   `| Observer | Type | What It Confirms | Node Link |`. The
   attestation source is implicit at the artifact level (every
   corroboration_item carries its source, but that's artifact
   metadata, not investigator-facing). Minimal column count; the
   Node Link column becomes redundant with Observer if Observer is
   already a backtick-bracket link.

My lean: option 1. Attestation provenance is useful (tells reader
which source attests a given corroboration); surfacing it in a
secondary column keeps the table self-contained. The column rename
also clarifies the table's role as a cross-reference surface, not a
statement surface.

**Surfaced.** F.1c Fravor pilot audit (2026-04-19). Not blocking;
the Corroboration section renders correctly, just awkwardly. Fix
naturally lands with F.2 (event renderer) since encounter event
nodes have the same Corroboration shape on their own node-type
template.

---

### Schema-descriptive keys not yet schema-driven in the validator

**Issue.** Post-source-taxonomy-consolidation (2026-04-18) the schema
grew three new descriptive keys. Initially none were read by
`validate.py`; this entry tracks which have since been wired and which
remain documentation-only.

Status as of 2026-04-18 hardening pass:

1. **`conditionally_required`** (document + media) — **✅ SHIPPED**
   `validate.py` now reads `types.{T}.conditionally_required` via the
   `check_conditionally_required()` dispatcher. Condition grammar:
   `<field> == <literal>` and `<field> is set`. Keys route to a
   frontmatter-field check (lowercase names) or a section-presence
   check (Title Case names) by shape. Malformed expressions surface
   as validator errors. Future conditionals land as schema edits
   alone; the two live rules (archival_status when doc_form=book;
   Media Versioning when derivation_of is set) are now schema-driven.
2. **`optional_sections`** (media) — **still descriptive-only**
   `media: [Media Versioning]`. Read by no script. The Media
   Versioning section escapes `required_sections` enforcement because
   it's not listed there; the `optional_sections` entry is
   informational. Promoting it to enforced behavior means making
   unknown H2 sections a warning unless they appear in
   `required_sections`, `optional_sections`, or a corpus addendum.
   Modest scope; useful mostly as a forcing function against drift
   where contributors invent ad-hoc sections.
3. **`may_be_empty: true`** on `media.section_rules.Key Passages` —
   **still descriptive-only, likely redundant**
   Read by no script. The existing `requires_quote_verification: true`
   rule already permits zero-quote sections (it only errors when
   quotes exist without verification blocks), so the flag mirrors
   current default behavior. It becomes meaningful only if a future
   variant of `requires_quote_verification` starts demanding
   at-least-one quote — at which point the negation (`may_be_empty`
   means "do not demand") would actually gate behavior. Until then,
   safe to keep as documentation.

**Proposed remaining scope.** Honor `optional_sections` as an
allowlist for an unknown-section warning pass. Defer `may_be_empty`
until there's a concrete case for it. The `conditionally_required`
dispatcher's condition grammar can also grow (`in <list>`,
`<field> != <value>`) on-demand when a new conditional needs it —
no preemptive extension.

**Update 2026-04-19 (F.1a).** The schema flag `chronological: true`
on section_rules (previously descriptive-only) is now enforced by
`validate.py` check #15. Applied universally across all date-bearing
tables on every node type. Closes one more descriptive-only gap from
this entry's scope.

**Surfaced.** Source-taxonomy consolidation double-check (2026-04-18).
**Partial resolution.** `conditionally_required` dispatcher shipped
(2026-04-18 hardening pass). `chronological: true` flag enforced via
check #15 (2026-04-19 F.1a).

---

### Cross-node reference existence not validated (derivation_of / derived_from) — ✅ RESOLVED 2026-04-18

**Issue (original).** The source-taxonomy consolidation added two
optional cross-node pointers on frontmatter:

- `media.derivation_of` — path to a parent media node when this media
  is an edited / cropped / re-encoded / metadata-scrubbed derivative.
- `transcript.derived_from` — path to the underlying media or document
  node this transcript renders.

Neither pointer was validated for existence. A media node with
`derivation_of: /media/does-not-exist` or a transcript with
`derived_from: /media/typo` passed validation cleanly.

**Resolution.** `scripts/validate.py` grew a module-level constant
`NODE_PATH_FRONTMATTER_FIELDS = {"media": ["derivation_of"],
"transcript": ["derived_from"]}`. The internal-link-resolution pass
now reads frontmatter values from the declared fields on each node
type, normalizes them to leading-slash form, and feeds them into the
same existence-check that body `[`/path`]` links already flow through.
Missing targets register in the broken-link registry as backlog (not
errors), matching body-link stub behavior.

Smoke-test coverage: `tests/smoke.sh` transcript-other fixture now
uses `--derived-from /documents/__smoke-doc-gov` to lock in the
resolves-clean case. Broken-path case covered by manual test during
implementation; a negative-case smoke fixture would require a cleanup-
ordered broken-link that's tolerable during validation — deferred
because the behavior is already exercised in the positive direction
and the code path is straightforward.

**Promote to schema-driven if.** The field list grows past ~5
entries. Today: two entries, flat-scripts pattern applies.

**Surfaced.** Source-taxonomy consolidation double-check (2026-04-18).
**Shipped.** 2026-04-18 hardening pass (this commit).
