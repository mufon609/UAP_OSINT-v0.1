---
id: meta/toolkit-notes/c11-validator-decomposition-design
type: meta
schema_version: 1
created: 2026-05-05
---

# Validator decomposition — design (C11 / C13 / C14)

Forward-looking design record for the per-check module refactor of
`scripts/validate.py`, `scripts/validate-research.py`, and
`scripts/review-coverage.py`. BACKLOG entries C11, C13, C14 ship as one
coherent design pass; this doc captures the seven decisions.

## 1. `Issue` dataclass shape

```python
@dataclass
class Issue:
    path: str           # repo-relative path of the file the issue concerns
    level: str          # "error" | "warn" — string; review-coverage's "info" added if needed
    message: str        # human-readable; may embed line numbers when checks know them
    check_name: Optional[str] = None  # filled by each check via module-level CHECK_NAME
    fatal: bool = False               # True → orchestrator stops further checks on this file

    def __post_init__(self):
        self.path = str(self.path)    # coerce Path inputs; matches legacy Issue
```

`check_name` is set by each check itself (`check_name=CHECK_NAME`
convention) rather than decorated by the orchestrator at yield time.
Self-population keeps Issue provenance carried even when checks are
called standalone (tests, single-check debugging) without an
orchestrator decorating the stream.

`line` deliberately omitted — verbatim-quote etc. embed line numbers in
the message string today; lifting to a structured field forces every
check to either populate or leave `None`. Defer until a `--format json`
consumer needs it. No `Severity` enum — string keeps the migration
diff small; promote later.

## 2. Check callable signature

```python
def check(ctx: Context) -> Iterable[Issue]
```

`Iterable` (not `list`) so checks can `yield`. One-arg signature; all
shared state flows through `ctx`. Per-file checks receive `NodeContext`
or `ResearchContext` (subclasses); global checks receive `BaseContext`.

## 3. Context object

Two layers, kept minimal — only state ≥2 checks read.

**`BaseContext`** (loaded once at orchestrator entry):
- `schema` (parsed `meta/schema.yaml`)
- `manifest_paths: set[str]`
- `manifest_format: dict[str, str]` — already cached in `lib/_common.py`; expose via property
- `addenda: dict[str, list[str]]` — lazy cache, replaces per-call `load_addendum_sections`
- `broken_links: defaultdict(set)` — out-of-band metadata channel; link-resolution writes here, returns no Issues; orchestrator prints registry from this dict (per Q2 — confirmed)

**`NodeContext(BaseContext)`** — per-node state:
- `path`, `rel`, `text`, `raw_lines`
- `fm` (parsed frontmatter), `node_type`, `type_spec`
- `h2_sections` (lazy property — single extraction shared across `required_sections`, `section_rules`, `chronological_tables`, `table_cell_word_budget`)
- `section_text(name)` (lazy memoized)

**`ResearchContext(BaseContext)`** — per-artifact state:
- `path`, `rel`, `data` (parsed YAML), `raw_lines`
- `target_type`, `target_archetype`, `target_kind`, `target_derivation_of` (discovered from target node's frontmatter)

`lib/_common.py` source-extraction caches stay where they are (process-global). Context does not re-wrap them.

## 4. Module structure

Flat: `scripts/checks/{check_name}.py`. Each module exports
`def check(ctx) -> Iterable[Issue]` plus any check-private constants /
helpers. Rejected grouping into `scripts/checks/node/`,
`scripts/checks/research/`, etc. — the layer separation is already
mechanical via Context type; subdirectories repeat that information.
Matches the flat-content rule documented in `meta/conventions.md`
("Inside `/scripts/`").

**Naming convention.** Module file name = canonical topic name with
hyphens → underscores: `verbatim-quote check` → `verbatim_quote.py`.
Add a one-line note to `meta/conventions.md` "Check naming" during
migration. (Issue #11.)

## 5. Orchestrator shape

Explicit step lists, no auto-discovery (per BACKLOG C11 OUT-OF-SCOPE):

```python
GLOBAL_CHECKS = [manifest_checksums, manifest_archive_status,
                 manifest_extraction_type, governance_files, topic_overview_present]
PRE_PARSE_NODE_CHECKS = []                        # validate.py has none today
PRE_PARSE_ARTIFACT_CHECKS = [yaml_hash_truncation, yaml_colon_space]
NODE_CHECKS = [frontmatter_required, schema_version_compat, id_path_match,
               status_archetype_kind, doc_form_archival_status,
               conditionally_required, required_sections, section_rules,
               chronological_tables, verbatim_quotes, table_cell_word_budget,
               finding_cross_ref, link_resolution]
ARTIFACT_CHECKS = [top_level_keys, target_node_existence,
                   conditional_section_iff, person_keys, event_keys,
                   transcript_keys, media_keys, organization_keys, location_keys,
                   primary_sources, quotes, entities, naming_quirks, rumors,
                   timeline, corroboration_items, program_involvement,
                   publication_record, vouching_chain, affiliations, relationships,
                   participants, witnesses_testimony, speakers, media_versioning,
                   key_personnel, org_relationships, contracts, ownership_timeline,
                   uap_scope_activity, location_relationships, cross_refs, prose_drift]
```

Per-file loop: (1) pre-parse checks on raw lines; (2) parse + Context construction; if parse fails or frontmatter absent, emit fatal Issue and continue to next file; (3) post-parse checks; abort remaining checks for that file on any fatal Issue (per Q1 — confirmed).

## 6. Inline `validate_node` logic disposition

Lift the named inline pieces into their own check modules
(`frontmatter_required`, `schema_version_compat`, `id_path_match`,
`status_archetype_kind`, `doc_form_archival_status`). They're
substantively independent and were inline only because the megafile
made it convenient. The `section_rules` walker stays as ONE check
module (`section_rules.py`) — its three sub-checks (split / prose-only
/ requires_quote_attribution) share H2 extraction and per-section text;
splitting fragments shared state without buying isolation (Issue #7).

Frontmatter parsing itself stays in the orchestrator's Context
construction step; every check downstream reads `ctx.fm`.

## 7. CLI surface preservation

Unchanged. `validate.py [PATH] [--quiet]`, `validate-research.py [PATH] [--quiet]`,
`review-coverage.py {PATH | --all} [--quiet]`. Orchestrator print
formatting reproduces current output byte-for-byte at first to keep
pre-commit reports stable; format refactor can ship separately.

## Out of scope (separate BACKLOG entries)

- **Issue #9** — iff-section walker schema-driven consolidation. Coupled to `schema.yaml conditional_keys`, not to C11/C13/C14. New BACKLOG C-tier entry.
- **Issue #5** — `check_boundary` subprocess memoization. Speculative; no second consumer of regenerated body today.

## Guardrails for migration

- **Issue #12** — `extract_description_drift_tokens` (review-coverage description-drift) and `extract_significant_tokens` (lib prose-drift tokenizer) are different algorithms by design (commit-comment 2026-05-05). Carry the distinction-comment forward when checks move modules. Do not collapse.
- **Issue #8** — `schema_version` compat duplication (4 sites today) consolidates into a `lib/_common.py` helper *during* migration, not as a separate pre-step. Falls out naturally as the modules split.
- **Pre-commit must pass 0/0 after every migration commit.** Hybrid orchestrator (some checks lifted, some still inline) is acceptable mid-migration; broken pre-commit is not.
