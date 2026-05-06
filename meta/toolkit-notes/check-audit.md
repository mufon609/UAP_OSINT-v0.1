---
id: meta/toolkit-notes/check-audit
type: meta
schema_version: 1
created: 2026-05-05
---

# Per-check audit + unit-test tracking (BACKLOG C17)

Tracks the C17 audit pass — for each named validator check at
`scripts/checks/{check_name}.py`, confirms:

1. **Docstring + comments concept-anchored** — no dates, no session
   lore, no didactic examples. Anchored to BACKLOG IDs, schema field
   names, file paths, conventions.md sections per the comment
   discipline in the C17 brief.
2. **Synthetic broken-input fixture exercises the check's error path.**
   A test that constructs a Context where the check's guard condition
   is violated, invokes the check, and asserts the expected Issue
   fires (level / check_name / message substring).
3. **Clean-input fixture confirms the check stays silent.** Mirror
   case — clean Context produces no Issues.
4. **Test module wired into the runner.** Lives at
   `scripts/tests/check_tests/{check_name}_test.py`; picked up
   automatically by `scripts/tests/run-check-tests.py` (pre-commit
   gate 4).

Status legend:

| Mark | Meaning |
|---|---|
| ✅ | docstring audited, broken + clean fixtures land, test module wired |
| ⏳ | in flight (current session) |
| ☐ | pending |

The pilot session wired the runner + fixture helpers
(`scripts/tests/check_tests/_fixtures.py`) and audited 7 representative
checks across all five dispatcher shapes. Remaining checks pick up the
pattern; `_fixtures.py` covers Context construction so per-check tests
stay focused on input-shape variations.

---

## BaseContext (global) — 4 checks

| Check | Status | Test count | Notes |
|---|---|---|---|
| governance_files | ☐ | — | Walks `meta/`; substantial — schedule with heavy-checks batch |
| manifest_archive_status | ✅ | 11 | 2-bit bitmask + wayback_skip contradiction |
| manifest_checksums | ☐ | — | File-IO + sha256; needs tmpfile fixture pattern |
| manifest_extraction_type | ☐ | — | Light; pairs with manifest_archive_status |

## NodeContext (per-content-node) — 13 checks

| Check | Status | Test count | Notes |
|---|---|---|---|
| chronological_tables | ☐ | — | H2 table parsing + chronology ordering |
| conditionally_required | ✅ | 9 | Schema-driven dispatch, both routes |
| doc_form_archival_status | ☐ | — | Likely subsumed by conditionally_required pattern |
| finding_cross_ref | ☐ | — | Cross-references entities[] from finding |
| frontmatter_required | ✅ | 4 | Required-field walk |
| id_path_match | ✅ | 4 | rel ↔ fm.id consistency |
| link_resolution | ☐ | — | Writes to `ctx.broken_links` (out-of-band) |
| required_sections | ☐ | — | H2 presence per type_spec |
| schema_version_compat | ☐ | — | Light; uses `lib._common` helper |
| section_rules | ☐ | — | Walker — split / prose-only / quote-attribution |
| status_archetype_kind | ☐ | — | Frontmatter enum validation |
| table_cell_word_budget | ☐ | — | Soft cap warning |
| verbatim_quotes | ☐ | — | Heavy — exercises `lib._common` source extraction |

## ResearchContext (pre-parse) — 2 checks

| Check | Status | Test count | Notes |
|---|---|---|---|
| yaml_colon_space | ☐ | — | Pairs with yaml_hash_truncation |
| yaml_hash_truncation | ✅ | 6 | Raw-line scan + heuristic |

## ResearchContext (per-artifact) — 26 checks

| Check | Status | Test count | Notes |
|---|---|---|---|
| affiliations | ✅ | 10 | Entry-list helpers (`_research_utils`) |
| artifact_top_level | ☐ | — | Top-level required keys |
| contracts | ☐ | — | gov-contractor only; multi-field shape |
| corroboration_items | ☐ | — | eyewitness archetype + encounter kind |
| cross_refs | ☐ | — | Cross-entity link consistency |
| entities | ☐ | — | entity_entry shape |
| iff_section | ✅ | 7 | Schema-driven placement (AND / OR rules) |
| key_personnel | ☐ | — | leadership_class sub-grouping |
| location_relationships | ☐ | — | Heterogeneous entity_path |
| media_versioning | ☐ | — | derivation_of conditional |
| naming_quirks | ☐ | — | resolution enum + observed/canonical |
| org_relationships | ☐ | — | relationship_type enum |
| ownership_timeline | ☐ | — | Period + use_status |
| participants | ☐ | — | capacity enum dispatch |
| primary_sources | ☐ | — | path + format |
| program_involvement | ☐ | — | institutional-actor archetype |
| prose_drift | ☐ | — | Heavy — exercises lib tokenizer |
| publication_record | ☐ | — | reporter archetype |
| quotes | ☐ | — | Universal evidentiary primitive; observation_type |
| relationships | ☐ | — | person↔person edges |
| rumors | ☐ | — | rumor status enum |
| speakers | ☐ | — | transcript-only |
| timeline | ☐ | — | Person/org/event/finding shapes |
| uap_scope_activity | ☐ | — | Location-only |
| vouching_chain | ☐ | — | whistleblower archetype |
| witnesses_testimony | ☐ | — | event-hearing only |

## ResearchContext (Phase III review) — 4 checks

| Check | Status | Test count | Notes |
|---|---|---|---|
| boundary | ☐ | — | Uses `ctx.regenerated_body` lazy cache |
| coverage | ☐ | — | Target-node body inspection |
| description_token_drift | ☐ | — | Different tokenizer than prose_drift; preserve distinction |
| stub_linking | ☐ | — | Cross-layer link resolution |

---

## Audit pass progress

- **Pilot (this session):** 7 checks across all 5 shapes; 51 tests
  total. Fixture helpers + runner landed; gate 4 in pre-commit chain.
- **Remaining:** 42 checks. Realistic per-check time: 15 min light,
  25 min medium, 45 min heavy. Estimate ~15–20 hours focused over
  5–8 sessions.

## Sequencing recommendation

After pilot, batch remaining work by Context type so the per-check
tests inside a batch share fixture idioms:

1. **NodeContext light batch** — schema_version_compat, status_archetype_kind,
   doc_form_archival_status, finding_cross_ref. Pairs with the
   already-piloted frontmatter / id_path / conditionally_required
   pattern.
2. **ResearchContext entry-list batch** — the 18 per-section
   `_research_utils`-using checks (affiliations is already done).
   Test shape repeats; should batch fast once the first 2–3 set
   precedent.
3. **Pre-parse pair** — yaml_colon_space (yaml_hash_truncation
   already done).
4. **NodeContext medium batch** — required_sections, link_resolution,
   section_rules, table_cell_word_budget, chronological_tables.
   Section-aware checks; lazy-cache exercise.
5. **Heavy batch (last)** — verbatim_quotes, prose_drift,
   description_token_drift, governance_files, manifest_checksums.
   Each needs its own fixture pattern (source extraction, file IO,
   tokenizer); slow per-check.
6. **Phase III batch** — coverage, boundary, stub_linking. Cross-
   layer fixture pattern exercise.

The order is a recommendation, not a contract — re-sequence per
session focus.
