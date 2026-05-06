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
| governance_files | ✅ | Anchored to `30b7fc3` (BACKLOG #3 close — "Add check #13 — governance-file frontmatter validation"). Defensive design against template-drift blast-radius (drifted schema_version in template → propagates to every scaffolded node). Two-route design: templates regex (placeholders break YAML), governance docs YAML parse. Migration consolidated `parse_frontmatter` (`7f5f86f`) and `schema_version_compat_messages` (`2f3effb` / BACKLOG #8) into `lib/_common.py`. |
| manifest_archive_status | ✅ | Anchored to `7a01d8b` (field + check introduced together — defensive, paired with the `archive.py` recheck-skip optimization). Concrete adjacent failure class: BACKLOG #30 (`d6732e1`, archive.py fire-and-forget) — check catches any regression of that shape. |
| manifest_checksums | ✅ | Foundational from initial commit (`af5f789` — "SHA256 integrity on every archived file" called out as toolkit core feature). Source-integrity backstop that downstream source-using checks rely on (verbatim_quotes / prose_drift / description_token_drift / coverage all extract via lib._common). Pairs with manifest_archive_status: content-byte integrity vs state-bit consistency. Notable: was the C11 cluster PILOT module (`472e547`), chosen for stand-alone shape + few helpers. |
| manifest_extraction_type | ✅ | Two-stage reactive anchor: `978221a` (BACKLOG #19 Phase A — {text-native, ocr-scan} from Grusch PPD-19 OCR artifacts `UAP-telated` / `compatrtmented`); `4b4d7fb` (Phase F Tier 1 — added `extraction-lossy` from hearing transcript Unicode-mapping artifact `11½` → `11‡`). Lightweight enum guard preventing typos from disabling sibling-preference logic. Closes the three-check manifest family (state + content + ingestion-metadata). |

## NodeContext (per-content-node) — 13 checks

| Check | Status | Notes |
|---|---|---|
| chronological_tables | ✅ | Anchored to F.1a (`8007ef1` — paired with the schema's `chronological: true` flag). Defensive design (created with the schema rule, not reactive to a bug). Severity model split: warn on unparseable dates, error on out-of-order pairs. Migration nuance: shipped to per-module shape at `d65451b` BEFORE NodeContext lazy caches landed at `60bb88d`; retrofitted at `ecabd52` to use `h2_sections` + `section_text` shared with 4 sibling section-walkers. |
| conditionally_required | ✅ | Anchored to `26969ba` (source-taxonomy consolidation surfaced two simultaneous conditionals — archival_status when doc_form==book, Media Versioning when derivation_of). Dispatcher pattern chosen over two hardcoded `if` blocks to keep schema as the single source of truth. Both routes (field-key + section-name) currently exercised. |
| doc_form_archival_status | ✅ | Foundational from `af5f789`. NOT subsumed by conditionally_required (the audit-tracking note was wrong) — orthogonal-concern guard. conditionally_required gates required-presence under a condition; this check gates value-validity whenever the field is set, regardless of the conditional gate. Covers two distinct cases: doc_form WARN-on-unknown (extensible vocabulary; no equivalent elsewhere), archival_status ERROR-on-invalid even when conditional gate doesn't fire. |
| finding_cross_ref | ✅ | Foundational from `af5f789` (check #10 in original validate.py docstring). Forward-defensive ("designed but dormant"): codifies bidirectional-link convention pre-corpus; finding type has 0 instances (F.7 renderer is last unbuilt phase). New sub-shape under foundational. WARN severity — bidirectional links encouraged not required. Pending rename per BACKLOG A4 (finding → investigation). |
| frontmatter_required | ✅ | Foundational schema discipline; present in initial commit (`af5f789`). No specific incident — class of failure protected against is dispatcher-correctness (downstream archetype/kind dispatch fails if required fields are absent). Presence-only by design; downstream enum checks (`status_archetype_kind`) catch nullified values. |
| id_path_match | ✅ | Foundational schema discipline; present in initial commit (`af5f789`). Class of failure protected against: cross-reference correctness (broken-link registry, associate.py auto-generator, inter-node links all key off the slug). Paired with frontmatter_required; together they have an accepted layering gap on nullified id (no downstream enum defense for id; defensive coverage not justified absent a real incident). |
| link_resolution | ✅ | Anchored to initial commit (`af5f789`, check #7 in original validate.py). Foundational metadata-only design: broken stubs are backlog signal, not violations — required by the one-node-per-session hard rule combined with cross-reference graph integrity. The ONE deliberate exception to the "checks yield Issues" contract; writes to `ctx.broken_links` out-of-band channel per C11 design doc Q2. C11 (`60bb88d`) refactored from per-call return tuple to ctx-channel; behavior preserved. |
| required_sections | ☐ | H2 presence per type_spec |
| schema_version_compat | ☐ | Light; uses `lib._common` helper |
| section_rules | ✅ | Foundational at `af5f789` with 4 rule shapes (prose_only / split / requires_quote_verification / auto_generated). Multi-stage check evolution: `4dcb1ad` removed unused `auto_generated` (dead-code pass); `31e03fa` (BACKLOG #19 Phase B / A2) renamed `requires_quote_verification` → `requires_quote_attribution` with semantic shift (output-trust-marker → input-attribution-shape after Verified marker removal). C11 design doc §6 explicitly preserved the three-sub-rule walker as one module — sub-checks share NodeContext lazy caches; splitting would fragment without buying isolation. |
| status_archetype_kind | ☐ | Frontmatter enum validation |
| table_cell_word_budget | ☐ | Soft cap warning |
| verbatim_quotes | ✅ | Anchored directly to `pilot-failure-2026-04-17.md` postmortem. The toolkit's load-bearing backstop: 10 pilot nodes passed structural validation 0/0, post-build fact-check found composite quotes / paraphrases / mis-attributions; same-day fix was a mechanical substring-match against extracted sources. All three F1/F2/F3 fabrication shapes fail this check. The conventions.md "Confirmation is a precondition for inclusion" principle rests on this module. |

## ResearchContext (pre-parse) — 2 checks

| Check | Status | Notes |
|---|---|---|
| yaml_colon_space | ✅ | Anchored to `d9a63a1` (BACKLOG #11) + 2026-04-20 Cluster B hearing-event pilot incident — NewsNation submission title with inner `: ` broke a publication_record entry. Structural parallel to yaml_hash_truncation; word-count threshold differs (≥2 vs ≥3) due to different false-positive shapes (no `# WIP`-style equivalent for inner colons). |
| yaml_hash_truncation | ✅ | Anchored to F.4c FLIR1 pilot (`c065e4a`) — methodology field truncated at `validate.py check #11 returns warn`. 3-word heuristic calibrated against that shape; accepts short `#N` references as known false-negative. |

## ResearchContext (per-artifact) — 26 checks

| Check | Status | Notes |
|---|---|---|
| affiliations | ✅ | Anchored to F.1b (`491e6f3`) — person renderer required structured `affiliations[]` to emit the Confirmed/Flagged-split table sorted by period_start. Extended D.4-era entry-list pattern to affiliations + relationships; later F.X work extended again to the full 18-check family. Same template applies to the 17 sibling entry-list checks. |
| artifact_top_level | ✅ | Most-reductive multi-stage in the codebase. Foundational at `af5f789` with 17 required keys; 5 removed across 4 distinct commits as surrounding-system simplifications landed: `efd4588` (description → conditional on non-person), `cde69cf` (claims[] elimination), `1a8ddbb` (iteration log removal), `7ec1d61` (Open Questions / research_gaps removal). Distinct REDUCTIVE multi-stage sub-shape vs additive (quotes) and dual-evolution (entities). Schema-grammar gap: description-on-non-person uses inline rule because conditional_keys can't express NOT-IN; inline kept at n=1 per code comment. |
| contracts | ☐ | gov-contractor only; multi-field shape |
| corroboration_items | ✅ | Anchored to F.1a (`8007ef1`) — one of six entry-list-pattern checks landed together for the F.1a person redesign (alongside chronological_tables + four sibling archetype-conditional surfaces). Renderer-coupled-defensive shape; predates affiliations (F.1b). C15 added encounter-event kind to scope (the OR-disjunction case for the grammar upgrade; witnesses_testimony was the AND-conjunction case). Cross-reference surface, NOT statement surface; .note out of prose-drift scope per 2026-04-21 second scope cut. |
| cross_refs | ✅ | Hybrid additive-AND-reductive multi-stage. Foundational at `af5f789` with 6 sections; gained 15 across F.1a–F.6 renderer landings (timeline + 4 archetype-conditional + 2 event + speakers + media_versioning + 3 organization + 3 location); lost 2 (`cde69cf` claims; `7ec1d61` research_gaps). Currently 21 sections. Warn-not-error severity intentional — external refs allowed by `entry_lifecycle_fields` spec; cross-artifact resolver is BACKLOG A3/E.3. |
| entities | ✅ | Foundational from `af5f789` with 6 types + quote_id+claim_id refs. Dual-evolution anchor — first investigated check spanning BOTH multi-stage-check (type list expanded to 8 at `26969ba`; claim_id refs removed at `cde69cf`) AND evolving-discipline (alex-dietrich rebuild surfaced "named in prose but not registered" → feedback_interview_node_entities; bumped Dietrich broken links 17 → 36). Cross-reference graph backbone: wrap_path drives broken-link registry + Associated Nodes + stub_linking. |
| iff_section | ✅ | Anchored to BACKLOG C15 (`dc95d39`). Forcing case for the schema-driven dispatcher + grammar upgrade was `witnesses_testimony` (event-hearings only, not transcript-hearings; `hearing` is shared across both kinds → flat OR-keys couldn't express the AND-conjunction). |
| key_personnel | ☐ | leadership_class sub-grouping |
| location_relationships | ☐ | Heterogeneous entity_path |
| media_versioning | ☐ | derivation_of conditional |
| naming_quirks | ✅ | Foundational from initial commit (`af5f789`) — schema + check + resolution enum complete from day one ("Leslie Keane → Leslie Kean" example was even in the original schema comment). New anchor pattern: STABLE CHECK / EVOLVING DISCIPLINE. The check's entry shape didn't change, but the contributor practices around `preserve-as-sic-in-quotes` evolved through F.1c (Lue/Luis), Cluster B (Bigalow, lockie Martin), and `13f9e91` codification of three-step OCR-scan discipline in conventions.md. |
| org_relationships | ☐ | relationship_type enum |
| ownership_timeline | ☐ | Period + use_status |
| participants | ☐ | capacity enum dispatch |
| primary_sources | ☐ | path + format |
| program_involvement | ☐ | institutional-actor archetype |
| prose_drift | ✅ | Anchored to F.1c Fravor pilot audit (introducing commit `d9bc684`) — RCA found contributor-prose drift unchecked despite verbatim quotes being source-verified. Threshold-tuning history at `836f96a` (revised from differentiated 80% to impartial single-rule) established the "validator surfaces drift, doesn't classify it" principle — reference before proposing any threshold change. Per-entry fields pool against top-level union, not per-entry source. |
| publication_record | ☐ | reporter archetype |
| quotes | ✅ | Multi-anchor history: foundational at `af5f789` (text + source + manifest) → F.1a `8007ef1` (observation_type for person artifacts) → `83b19c6` REACTIVE F.1b-audit fix (context required on person — Attributed-to row was being silently omitted) → `cde69cf` (claims-elimination wave elevated quotes[] to universal evidentiary primitive). Layered enforcement: this check verifies entry-shape; verbatim_quotes verifies source text; coverage verifies artifact↔node. |
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
| boundary | ✅ | Anchored to D.4 introduction (`0a56989`); self-validating dogfood — caught real Fravor divergence on first run (5 errors at smoke). Three drift classes: artifact→node desync, hand-edits, renderer changes. Byte-equal comparison after Associated Nodes excision. Subprocess + caching moved to `ResearchContext.regenerated_body` lazy property at `4b1cfd3` (BACKLOG C16) — defensive design despite no second consumer (rationale: future cross-layer checks shouldn't re-implement). |
| coverage | ✅ | Anchored to D.4 introduction (`0a56989`). Originally checked both claims[].statement and quotes[].text; simplified to quotes-only at `cde69cf` (claims[] layer elimination). Forms a paired-check family with verbatim_quotes that brackets the source ← quote → node-body integrity chain (verbatim_quotes catches fabrication entering the artifact; coverage catches artifact-vs-rendered-node drift). Both share `lib._common.normalize_for_compare`. |
| description_token_drift | ✅ | Anchored to `5b1ea03` (Check #6 introduction; dogfooded on first run — caught Fravor's "Congressional" drift, fixed in i5). Same evidentiary axis as prose_drift but rendered-output layer; algorithmically distinct (proper-nouns + designators + numbers + quoted strings vs lowercase content words) — distinction locked in by 2026-05-05 lockstep refactor renaming the tokenizer. Severity model: error per unmatched token (rendered surface, not artifact field). |
| stub_linking | ✅ | Anchored to D.4 introduction (`0a56989`) + reactive refinement at `efd4588` (Graves pilot surfaced self-reference false-positive — added skip when wrap_path matches target_node). Catches "phantom registered entity" — entities in entities_referenced[] without corresponding wrap-link in node prose. Inverse direction (named in prose without registration) is contributor discipline per `feedback_interview_node_entities`, not check signal. |

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
