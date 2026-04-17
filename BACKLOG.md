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

---

### Validator scope expansion to meta files

**Issue.** `validate.py` scans only `CONTENT_DIRS` (the 9 content node
types). Meta files — `meta/conventions.md`, `meta/sources-access.md`,
`meta/topic/research-queue.md`, `meta/topic/overview.md`,
`meta/topic/addenda/*.md`, `meta/toolkit-notes/*.md`, and all 9
`meta/templates/*.md` — carry `schema_version: 1` frontmatter but are
never checked for it. The discipline is half-enforced: if someone
creates a new meta file without `schema_version` (or with a drifted
value), nothing catches it.

**Why it matters.** Meta files govern the entire repository's
interpretation. Drift in a template silently propagates to every node
scaffolded afterward. Drift in `conventions.md` frontmatter is low
impact but inconsistent with the repo-wide discipline. The Step A/B/C
work established `schema_version` as a universal required field; the
validator should enforce that universally, not just on content nodes.

**Proposed scope.** Add a "governance-file validation" pass to
`validate.py` (or as a sibling `check-governance.py` if the monolithic
validator is being split per the prior backlog item). The pass:

- Walks meta/ recursively for `.md` files with frontmatter
- Requires `id`, `type`, `schema_version`, `created` fields
- Validates `schema_version` value against `schema.compatible_with`
  (same check as content nodes)
- Validates `id` matches file path (same check)
- Does NOT require `type`-specific sections (meta files have no schema
  type entry; they're governance docs, not structured nodes)

Could be scoped narrower if warranted — e.g., enforce only on
`meta/templates/` which have the highest blast radius.

**Surfaced.** Step A/B/C audit → follow-up assessment 2026-04-17
(P3). Deferred at that time in favor of B-series bug fixes.

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
   **Shipped 2026-04-17.** 12/12 scripts pass. Referenced from
   `CLAUDE.md` §5.
2. **Next**: fixture-based smoke tests — one scaffold per node type
   with known-good flags; validate.py exits clean on the scaffold;
   scaffold is deleted. A single `tests/smoke.sh` runs the whole
   set.
3. **Eventually**: unit tests for specific check functions in
   `validate.py` (quote normalization, checksum computation,
   verification-block parsing). These are the highest-leverage
   unit tests because the check logic is where correctness matters
   most.
4. **Continuous**: a pre-commit hook (or CI equivalent) that runs
   help-check + smoke + validate.py before any commit lands.

The first two are small, script-level, and low-risk. Unit tests and
CI are bigger structural commitments.

**Surfaced.** Step A/B/C audit (W1, 2026-04-17). Upgraded to BACKLOG
after P1 smoke test caught a real latent bug, demonstrating that the
lack of automated testing is not theoretical.

**Progress.** Step 1 shipped 2026-04-17. Steps 2–4 remain open.

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

### Extend build-from-research.py to all 9 node types

**Issue.** `scripts/build-from-research.py` ships in D.3 supporting
**document** nodes only. Person, organization, event, transcript, news,
book, location, and finding node regeneration is not yet implemented.
Attempting to run the script on one of those types exits with
"currently supports ['document'] only".

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
  Material Differences (hearing only).
- **news / book** — Publication Record, Summary, What The Article/Book
  Established, Authors, Key Passages, Credibility Notes.
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
