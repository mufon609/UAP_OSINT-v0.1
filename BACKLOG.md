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

### Extend build-from-research.py to all 8 node types

**Issue.** `scripts/build-from-research.py` supports 4 of 8 node types
as of 2026-04-19: `document` (D.3), `person` (F.1b), `event` (F.2b),
`transcript` (F.3b). Four remain: organization, media, location, finding.

**Why it matters.** Phase II of the layered build process is defined
as "deterministic regeneration from research artifact." Until all node
types are supported, the Phase II discipline is only partially
enforceable — contributors building unsupported types must still
hand-author the body, which reintroduces the fabrication surface
that the layered process exists to close.

**Per-type scope.** Sections remaining per type + artifact-field
conventions that will need to ship with each:

- **media** — Media Summary, Description, Provenance, Key Passages
  (optional — verbatim speech / visible text), Media Versioning
  (when derivation_of set). Four kinds: photo, video, audio,
  imagery-other.
- **organization** — Overview, Description, Key Personnel, What Is
  Confirmed, Timeline, Relationships. Requires `key_personnel`,
  `timeline`, `contracts` (gov-contractor) fields in artifact.
- **location** — Ownership Timeline, UAP-Scope Activity, Relationships.
- **finding** — Timeline, Primary Source Basis, What This Establishes,
  Entities Involved.

Each extension lands as a separate, pilot-tested increment (one type
per change), following the F.1a/b/c → F.2a/b/c pattern on the roadmap.

**Surfaced.** D.3 design (2026-04-17 Q4). **Progress:** F.1b (person,
2026-04-19 commit 491e6f3), F.2b (event, 2026-04-19 commit 5af2416),
F.3b (transcript, 2026-04-19 commit 6cb131a). Next per roadmap: F.4
(media) — natural pairing with `/media/flir1-video` as the pilot
candidate (Nimitz-cluster stub).

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

### Check #16 v2 — n-gram adjacency, whitelist, lemmatization

**Issue.** Check #16 (prose-field token drift) ships in v1 as a
membership-only check: every significant word in a prose field must
appear in the referenced source file. Three known limitations from
the F.1c audit that v1 intentionally defers:

1. **No phrase-adjacency check.** Word-membership alone misses drift
   where all words exist in source but in different adjacency patterns
   — the F.1c issue #1 ("ground operations" vs source's "operations
   supporting the ground forces") exemplifies this. A Tier B 2-gram
   check — verify every contiguous 2-word-significant-span in prose
   appears as a contiguous span in source — would catch this
   category. Tradeoff: adds noise from legitimate contributor
   restructuring; useful as warn-level only.

2. **No lemmatization / stemming.** Word-form drift generates routine
   warnings: source "investigate" ↔ prose "investigation"; source
   "publish" ↔ prose "published"; source "prepare" ↔ prose
   "preparing". V1 strips possessive `'s` only. A Porter stemmer or
   hand-rolled suffix-stripping pass on common English morphology
   (-ing, -ed, -tion, -ive, -s as plural) would resolve most word-
   form noise. Tradeoff: library dependency or hand-rolled rules;
   risk of over-stemming ("business" → "busine" etc.).

3. **No whitelist.** Repo-conventional vocabulary ("disclosure chain",
   "co-observer", "corroboration", "testimony", "subcommittee",
   "archived") warns every time. A module-level whitelist or
   per-schema `prose_drift_whitelist` field would silence these.
   Tradeoff: maintenance burden; risk of whitelisting words that
   actually need checking in different contexts.

**Why it matters (v1 limitations accepted).** The F.1c Fravor baseline
produces 15 warnings — most legitimate synonyms / word-form drift /
synthesis vocabulary. Contributor reviews each warning in ~30 seconds
to ack/fix. Tolerable at current corpus scale (1 person node). Scales
poorly past ~10 person nodes when warning review becomes routine
noise the contributor starts ignoring — at which point the check
loses signal.

**Proposed scope when triggered.** Ship one or more of:

1. Porter stemmer integration (or hand-rolled suffix pass) — removes
   word-form noise, probably the biggest share.
2. Per-type whitelist field in schema — `prose_drift_whitelist` list
   at the `types.person.section_rules.prose_drift` level.
3. Tier B 2-gram adjacency as warn-only — catches phrase-
   restructuring drift the v1 check misses.

**Trigger — evidence-based, NOT count-based.** The original trigger
("after ~5 person nodes") was replaced (2026-04-20 BACKLOG audit)
with evidence requirements because count-based triggers risk
shipping v2 while the zero-warnings discipline is still working.
V2 noise-reduction **silences** warnings; the
`feedback_check16_warnings_must_resolve.md` memory policy depends on
contributors **resolving** every warning. Shipping v2 prematurely
converts "zero-warnings target" (discipline-enforced) into
effectively "zero-errors target" (mechanical-only), losing the
signal the policy relies on.

Ship v2 only when ALL three apply:
- **Signal-to-noise analysis**: >90% of warnings across the corpus
  are provably legitimate word-form drift (`investigate` ↔
  `investigation`), not substantive vocabulary drift worth
  surfacing.
- **Measured contributor cost**: per-artifact rewrite-to-zero
  routinely takes >30 minutes, with that cost clearly going to
  resolving word-form drift rather than substantive drift.
- **Observed discipline breakdown**: documented evidence that
  contributors are ignoring or ack-without-fixing warnings (not
  just theoretical concern about scale).

If any condition is missing, the v1 impartial-reporter + contributor
zero-warnings discipline keeps producing better evidentiary hygiene
than v2 would. The corpus as of 2026-04-20 (10 nodes including 2
person + 2 organization + 3 document + 1 transcript + 1 event + 1
media) clears free-prose fields to 0 warnings routinely — the
discipline is intact.

**Surfaced.** F.1c Fravor audit RCA (2026-04-19). V1 ships as pre-F.2
hardening commit.

**Design note (2026-04-19 revision).** Initial v1 implementation
used differentiated error thresholds (80% top-level, 80% per-entry)
calibrated to accommodate synthesis-heavy fields passing without
error. That calibration embedded a validator-side judgment about
which fields are "allowed" more contributor vocabulary. Revised to
an impartial rule: warn on every unmatched token, error only at 100%
vocabulary divergence. The validator now surfaces drift without
classifying it; the contributor reviews each warning. Any future
v2 additions (stemming, whitelist, n-gram) must preserve the
impartial-reporter framing — reduce warning noise without
reintroducing validator-side judgments about "acceptable" drift
levels.

---

### `derived_from` fallback in transcript Publication Record renderer

**Issue.** Hearing transcripts populate the "Companion Written
Testimony" PR row from either `context_extrinsic.companion_written_testimony`
(the preferred path per F.3c D3) or frontmatter `derived_from` (when
it points at `/documents/...`, kept as a compatibility fallback in
`render_transcript_publication_record`'s hearing branch). The fallback
is dead code if the convention catches on cleanly across hearing-
transcript builds.

**Why it matters.** Two paths producing the same effect is mild
duplication that compounds if the frontmatter form gets misused.
Once the convention proves itself, removing the fallback simplifies
the renderer surface and forces a single declarative source of truth.
Schema's `derived_from` semantic ("this transcript IS a rendering of
that source") doesn't fit hearing transcripts (independent primary
records of the same event); the fallback lets that semantic mismatch
keep working while the convention stabilizes.

**Proposed scope.** When the trigger fires:
- Remove the `elif derived_from and str(derived_from).startswith("/documents/")`
  branch from `render_transcript_publication_record`'s hearing path
  in `scripts/build-from-research.py`.
- Update `meta/schema.yaml` `derived_from` comment to drop the
  "do NOT use for hearings" guidance (no longer needed if no
  fallback path exists).
- Spot-check existing hearing transcript artifacts to confirm none
  rely on the fallback (none should as of trigger date).
- Update the F.3 Decision 1 D3 refinement note in
  `meta/toolkit-notes/roadmap.md` to mark the fallback removed.

**Trigger.** After 3+ hearing transcript pilots ship and all use
`context_extrinsic.companion_written_testimony` (none rely on
`derived_from` for the companion cross-ref).

**Progress.** 1 of 3 hearing transcripts shipped
(`/transcripts/2023-07-26-house-fravor`, F.3c commit `083c249`,
2026-04-19) — uses `context_extrinsic.companion_written_testimony`
cleanly; no fallback triggered.

**Surfaced.** F.3c pre-implementation Decision 3 (2026-04-19). The
renderer kept the fallback as a leniency to avoid a hard convention
break before any hearing transcripts existed; this entry tracks the
eventual cleanup so the fallback doesn't become permanent dead code.

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
   **✅ REMOVED 2026-04-20 (BACKLOG audit cleanup).**
   The flag was descriptive-only and redundant: existing
   `requires_quote_verification: true` already permits zero-quote
   sections (it only errors when quotes exist without verification
   blocks), so `may_be_empty` mirrored default behavior. Removed from
   `meta/schema.yaml` to stop accumulating documentation-only keys that
   read as if they gate behavior. If a future `requires_quote_verification`
   variant starts demanding at-least-one quote, reintroduce the
   negation flag at that time.

**Proposed remaining scope.** Honor `optional_sections` as an
allowlist for an unknown-section warning pass. The
`conditionally_required` dispatcher's condition grammar can also grow
(`in <list>`, `<field> != <value>`) on-demand when a new conditional
needs it — no preemptive extension.

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

### `_excerpt_for_table` truncates mid-acronym on first-sentence preference

**Issue.** `build-from-research.py` `_excerpt_for_table()` prefers the
first-sentence excerpt (period-terminated) up to ~150 chars, falling
back to a word-boundary truncation with ellipsis only when no short
first sentence exists. On Fravor's written-testimony q1 ("My name is
David Fravor and I am a retired Commander in the U.S Navy.") the
function treats the period after "U" in "U.S" as a sentence terminator
and returns `"My name is David Fravor and I am a retired Commander in
the U."` — truncated mid-acronym, losing "S Navy" content the reader
needs to see in the Material Differences Written Quote cell.

**Why it matters.** Material Differences cells are the primary surface
where investigators compare oral and written testimony excerpts. A
mid-acronym truncation makes the Written Quote cell confusing and
requires a click-through to the companion node's Key Passages section
to grasp what the excerpt actually contains. The Fravor F.3c pilot has
this visible on 4+ rows (md4, md5, md9, md11 — all anchored to written
q1). The regression affects readability, not evidentiary integrity —
the full text is still one click away — but cell readability is part
of what makes Material Differences an investigative surface rather than
a reference index.

**Proposed scope.** Tighten the first-sentence heuristic to reject
"sentences" terminated by a period inside a known acronym pattern.
Simplest approach: refuse first-sentence excerpts where the terminator
period is preceded by a single uppercase letter and a period earlier
in the sentence (signals an abbreviation like "U.S.", "D.C.",
"Dr."). Fallback to word-boundary truncation with ellipsis. Could also
extend to recognize other abbreviation patterns (Mr., Mrs., Rev.,
initials, numbered items like "1." in lists).

**Trigger.** When more hearing-transcript pilots ship and the pattern
reproduces beyond Fravor's q1 — confirms the issue is not one-off.
Currently 1 node affected; small blast radius.

**Interim.** Leave as-is; flag in roadmap post-mortem. Contributors
reviewing rendered Material Differences tables can click through to
Key Passages for full text.

**Surfaced.** F.3c Phase III semantic review (2026-04-19). The
renderer's truncation logic was written without anticipating
period-bearing acronyms in quote openings.

---

### Extend schema `format_values` for audio and image sources

**Issue.** `meta/schema.yaml` manifest_entry.format_values is
`[pdf, html, txt, post, video, transcript]`. The F.4c pilot
surfaced that video sources (.mp4/.mov/.webm) cleanly map to the
existing `video` value, but audio (.wav/.mp3/.flac) and image
(.jpg/.png/.tiff) files have no matching format value. When the
first audio-only or photo-only media node is built, the manifest
entry for its primary source falls back to `html` (incorrect) or
requires the contributor to pass `--format` manually to override.

**Why it matters.** Media kinds `audio` and `photo` are first-class
node-type kinds per `meta/schema.yaml` (media type has kinds
[photo, video, audio, imagery-other]). The manifest.yaml vocabulary
hasn't kept pace. As media nodes accumulate — photos from Skinwalker
Ranch, cockpit audio releases, satellite imagery — the mismatch will
force contributors into the `--format` escape hatch routinely,
which is easy to forget and produces silent manifest-entry drift.

**Proposed scope.** When the first audio or photo primary source is
about to be archived:

1. Extend `meta/schema.yaml` manifest_entry.format_values with
   `audio` and `image` (covering photo + imagery-other media kinds
   under a single format value).
2. Update `FORMAT_BY_EXT` in `scripts/manifest.py` and `infer_format`
   in `scripts/research-scaffold.py` to map common audio extensions
   (.mp3 / .wav / .flac / .aac / .ogg / .m4a) → `audio` and common
   image extensions (.jpg / .jpeg / .png / .gif / .tiff / .webp /
   .bmp / .heic) → `image`.
3. Extend `scripts/validate.py` `extract_source_text` with explicit
   audio/image passthrough (returns None + warn, matching current
   .mp4 behavior; ensures the quote-verbatim check and review-
   coverage claim-drift check both treat audio/image as legitimately
   unextractable per the F.4c tightening).

**Trigger.** First audio-only or image-only primary-source archival.
Likely candidate: `/media/skinwalker-ranch-photo-{slug}` during F.6
location pilot, or a standalone audio release (press conference
recording, cockpit audio) during Cluster A closeout.

**Interim.** F.4c's manifest.py / research-scaffold.py additions
explicitly route .mp4/.mov/.webm/.m4v/.avi/.mkv → `video` without
touching audio or image. Contributors archiving audio or image files
pass `--format` manually; manifest.py will not reject arbitrary
format strings today (there's no enforcement against format_values
in validate.py), but the manifest-entry's format field will then be
a free-text value not listed in the schema vocabulary.

**Surfaced.** F.4c FLIR1 pilot (2026-04-20). The MP4 case was
addressed in-session because `video` was already in format_values;
audio and image deferred because they'd require schema vocabulary
extension.

---

### YAML unquoted-scalar colon trap

**Issue.** YAML's block-mapping parser treats `: ` (colon-space) as the
key/value separator anywhere in a value. An unquoted scalar containing
an embedded colon followed by a space — common in titles and prose
like `We are not alone: The UFO whistleblower speaks` — causes either a
parse error or silent mis-parsing (the portion before the colon is
treated as a key, the portion after as its value). Surfaced during the
Cluster B hearing-event pilot (2026-04-20) when a Luna NewsNation
submission title broke the `publication_record` entry; fixed by
single-quoting the value AND replacing the inner `:` with an em-dash
(`—`) for safety.

**Why it matters.** Unlike the `#` comment-truncation trap (warn-level
pre-parse check shipped F.4c), the colon-space trap typically surfaces
as a hard parse error rather than silent truncation — so evidentiary
data loss is less likely. But: contributors working with natural prose
titles, quote-bearing fields, and research_gap methodologies routinely
generate colon-bearing strings. Recurring friction is the cost; a
preemptive validator check would surface the issue at write time with
clear remediation guidance rather than via a cryptic YAML parser trace.

**Proposed scope.** Extend `validate-research.py`'s pre-parse scan (same
mechanism as `check_yaml_hash_truncation`) with a companion check that
warns on unquoted scalars containing `: ` (colon-space) followed by 2+
words. Remediation message: `quote the scalar value, OR replace the
colon with an em-dash / semicolon if typographically appropriate`.
Tradeoff: some colon-bearing unquoted scalars are valid (e.g., single-
word `url: https://...`). The check should be narrow enough to catch
prose but not URL/path strings — check if the colon is preceded by a
known-URL-scheme word (http, https, ftp, mailto, ssh) and skip.

**Trigger.** When a second hearing-event or media-artifact pilot
encounters the same trap.

**Interim.** Document in `prompts/build.md` alongside the `#` trap
guidance; contributors hand-quote values with embedded `: ` patterns.

**Surfaced.** Cluster B hearing-event pilot (2026-04-20).

---

### Committee Members subsection lacks Chair/Ranking sub-grouping

**Issue.** F.2b hearing-event Participants renders Committee Members
as a flat table with Name / Role / Affiliation / Status columns. The
Cluster B pilot populated 21 Members — Chair (Grothman), Ranking
(Garcia), Full Committee Chair (Comer), plus 18 sitting Members —
with role text capturing their leadership status ("Subcommittee Chair
(R-WI)", "Ranking Member (D-TX)", etc.). The flat table reads
accurately but requires the reader to scan every row to identify
leadership; a sub-grouped layout (Chair / Ranking / Members) would
surface the structural hierarchy faster.

**Why it matters.** Hearings have asymmetric member influence —
Chair controls the gavel; Ranking controls minority time; ordinary
Members ask questions in their allotted minutes. An investigator
comparing hearings by leadership composition benefits from the
hierarchy being visible at a glance rather than derivable from a
string-match scan of role cells. Not urgent — the information is
present, just flat.

**Proposed scope.** Two options:

1. **Render-time grouping via role-string parsing** — detect
   "Subcommittee Chair", "Ranking Member", "Full Committee Chair" in
   the `role` cell and emit H5 sub-subheads (Chair / Ranking /
   Leadership / Members). Fragile — role cell phrasing varies across
   hearings (Senate vs House; subcommittee vs full committee
   hearings).
2. **Schema-level role vocabulary** — add an optional
   `leadership_role` field on `participant_entry` with enum values
   (`subcommittee-chair`, `ranking-member`, `full-committee-chair`,
   `member`, `observer`). F.2b reads it for sub-grouping; leave
   `role` as the free-text display cell. Cleaner; retrofits require
   a sweep of hearing-event artifacts (currently 1).

**Trigger.** Second hearing-event artifact shipped (Cluster C or the
next Senate/House hearing to land). The retrofit cost stays at 1
artifact while the count is low.

**Interim.** Flat table with role-embedded leadership text is
acceptable; contributors reading the node can sort mentally or
filter by text.

**Surfaced.** Cluster B hearing-event pilot (2026-04-20).

