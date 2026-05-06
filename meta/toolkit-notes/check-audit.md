---
id: meta/toolkit-notes/check-audit
type: meta
schema_version: 1
created: 2026-05-05
---

# Per-check investigation tracking (BACKLOG C17)

Tracks the C17 investigation pass — for each named validator check at
`scripts/checks/{check_name}.py`:

1. **Production-issue anchor.** What concrete failure mode does the
   check protect against? `git log --diff-filter=A` on the module
   file finds the introducing commit; from there, BACKLOG /
   toolkit-notes / postmortem entries usually trace the surfacing
   incident. The anchor goes in the check's docstring (so future
   readers see it without leaving the file) and in the relevant
   row's notes column below.
2. **Logic review.** Confirm the check's code actually catches the
   failure mode anchored above. Surface dead code, ambiguous
   behavior, or schema gaps in the same commit (small fixes) or in
   new BACKLOG entries (larger ones).
3. **Docstring + comment discipline.** No dates, no session lore,
   no didactic examples per CLAUDE.md comment discipline. Anchored
   to BACKLOG IDs, schema field paths, conventions.md sections.

Status legend:

| Mark | Meaning |
|---|---|
| ✅ | investigated; docstring audited; production-issue anchor recorded |
| 🟡 | docstring audited, but production-issue anchor still loose |
| ☐ | pending |

The pilot 7 are 🟡: docstrings cleaned, but anchors not systematically
traced via `git log --diff-filter=A` + BACKLOG / toolkit-notes search.
Remaining 42 should land at ✅.

---

## BaseContext (global) — 4 checks

| Check | Status | Notes |
|---|---|---|
| governance_files | ☐ | Walks `meta/`; substantial — schedule with heavy batch |
| manifest_archive_status | ✅ | Anchored to `7a01d8b` (field + check introduced together — defensive, paired with the `archive.py` recheck-skip optimization). Concrete adjacent failure class: BACKLOG #30 (`d6732e1`, archive.py fire-and-forget) — check catches any regression of that shape. |
| manifest_checksums | ☐ | File-IO + sha256 |
| manifest_extraction_type | ☐ | Light; pairs with manifest_archive_status |

## NodeContext (per-content-node) — 13 checks

| Check | Status | Notes |
|---|---|---|
| chronological_tables | ☐ | H2 table parsing + chronology ordering |
| conditionally_required | ✅ | Anchored to `26969ba` (source-taxonomy consolidation surfaced two simultaneous conditionals — archival_status when doc_form==book, Media Versioning when derivation_of). Dispatcher pattern chosen over two hardcoded `if` blocks to keep schema as the single source of truth. Both routes (field-key + section-name) currently exercised. |
| doc_form_archival_status | ☐ | Likely subsumed by conditionally_required pattern |
| finding_cross_ref | ☐ | Cross-references entities[] from finding |
| frontmatter_required | ✅ | Foundational schema discipline; present in initial commit (`af5f789`). No specific incident — class of failure protected against is dispatcher-correctness (downstream archetype/kind dispatch fails if required fields are absent). Presence-only by design; downstream enum checks (`status_archetype_kind`) catch nullified values. |
| id_path_match | ✅ | Foundational schema discipline; present in initial commit (`af5f789`). Class of failure protected against: cross-reference correctness (broken-link registry, associate.py auto-generator, inter-node links all key off the slug). Paired with frontmatter_required; together they have an accepted layering gap on nullified id (no downstream enum defense for id; defensive coverage not justified absent a real incident). |
| link_resolution | ☐ | Writes to `ctx.broken_links` (out-of-band) |
| required_sections | ☐ | H2 presence per type_spec |
| schema_version_compat | ☐ | Light; uses `lib._common` helper |
| section_rules | ☐ | Walker — split / prose-only / quote-attribution |
| status_archetype_kind | ☐ | Frontmatter enum validation |
| table_cell_word_budget | ☐ | Soft cap warning |
| verbatim_quotes | ✅ | Anchored directly to `pilot-failure-2026-04-17.md` postmortem. The toolkit's load-bearing backstop: 10 pilot nodes passed structural validation 0/0, post-build fact-check found composite quotes / paraphrases / mis-attributions; same-day fix was a mechanical substring-match against extracted sources. All three F1/F2/F3 fabrication shapes fail this check. The conventions.md "Confirmation is a precondition for inclusion" principle rests on this module. |

## ResearchContext (pre-parse) — 2 checks

| Check | Status | Notes |
|---|---|---|
| yaml_colon_space | ☐ | Pairs with yaml_hash_truncation |
| yaml_hash_truncation | ✅ | Anchored to F.4c FLIR1 pilot (`c065e4a`) — methodology field truncated at `validate.py check #11 returns warn`. 3-word heuristic calibrated against that shape; accepts short `#N` references as known false-negative. |

## ResearchContext (per-artifact) — 26 checks

| Check | Status | Notes |
|---|---|---|
| affiliations | ✅ | Anchored to F.1b (`491e6f3`) — person renderer required structured `affiliations[]` to emit the Confirmed/Flagged-split table sorted by period_start. Extended D.4-era entry-list pattern to affiliations + relationships; later F.X work extended again to the full 18-check family. Same template applies to the 17 sibling entry-list checks. |
| artifact_top_level | ☐ | Top-level required keys |
| contracts | ☐ | gov-contractor only; multi-field shape |
| corroboration_items | ☐ | eyewitness archetype + encounter kind |
| cross_refs | ☐ | Cross-entity link consistency |
| entities | ☐ | entity_entry shape |
| iff_section | ✅ | Anchored to BACKLOG C15 (`dc95d39`). Forcing case for the schema-driven dispatcher + grammar upgrade was `witnesses_testimony` (event-hearings only, not transcript-hearings; `hearing` is shared across both kinds → flat OR-keys couldn't express the AND-conjunction). |
| key_personnel | ☐ | leadership_class sub-grouping |
| location_relationships | ☐ | Heterogeneous entity_path |
| media_versioning | ☐ | derivation_of conditional |
| naming_quirks | ☐ | resolution enum + observed/canonical |
| org_relationships | ☐ | relationship_type enum |
| ownership_timeline | ☐ | Period + use_status |
| participants | ☐ | capacity enum dispatch |
| primary_sources | ☐ | path + format |
| program_involvement | ☐ | institutional-actor archetype |
| prose_drift | ✅ | Anchored to F.1c Fravor pilot audit (introducing commit `d9bc684`) — RCA found contributor-prose drift unchecked despite verbatim quotes being source-verified. Threshold-tuning history at `836f96a` (revised from differentiated 80% to impartial single-rule) established the "validator surfaces drift, doesn't classify it" principle — reference before proposing any threshold change. Per-entry fields pool against top-level union, not per-entry source. |
| publication_record | ☐ | reporter archetype |
| quotes | ☐ | Universal evidentiary primitive; observation_type |
| relationships | ☐ | person↔person edges |
| rumors | ☐ | rumor status enum |
| speakers | ☐ | transcript-only |
| timeline | ☐ | Person/org/event/finding shapes |
| uap_scope_activity | ☐ | Location-only |
| vouching_chain | ☐ | whistleblower archetype |
| witnesses_testimony | ☐ | event-hearing only |

## ResearchContext (Phase III review) — 4 checks

| Check | Status | Notes |
|---|---|---|
| boundary | ☐ | Uses `ctx.regenerated_body` lazy cache |
| coverage | ☐ | Target-node body inspection |
| description_token_drift | ✅ | Anchored to `5b1ea03` (Check #6 introduction; dogfooded on first run — caught Fravor's "Congressional" drift, fixed in i5). Same evidentiary axis as prose_drift but rendered-output layer; algorithmically distinct (proper-nouns + designators + numbers + quoted strings vs lowercase content words) — distinction locked in by 2026-05-05 lockstep refactor renaming the tokenizer. Severity model: error per unmatched token (rendered surface, not artifact field). |
| stub_linking | ☐ | Cross-layer link resolution |

---

## Sequencing recommendation

Batch remaining work by Context type so per-batch idioms compound:

1. **Tighten the pilot 7 to ✅.** Trace each via
   `git log --diff-filter=A`; record the production-issue anchor.
   Cheap; closes the loose-anchor debt before new investigation.
2. **NodeContext light batch** — schema_version_compat,
   status_archetype_kind, doc_form_archival_status, finding_cross_ref.
3. **ResearchContext entry-list batch** — the 17 per-section
   `_research_utils`-using checks beyond affiliations.
4. **Pre-parse pair** — yaml_colon_space (yaml_hash_truncation done).
5. **NodeContext medium batch** — required_sections, link_resolution,
   section_rules, table_cell_word_budget, chronological_tables.
6. **Heavy batch** — verbatim_quotes, prose_drift,
   description_token_drift, governance_files, manifest_checksums.
7. **Phase III batch** — coverage, boundary, stub_linking.

The order is a recommendation, not a contract — re-sequence per
session focus.
