#!/usr/bin/env python3
"""
Validate nodes against meta/schema.yaml.

Checks:

  Frontmatter — required fields + valid type/kind/archetype/status

  id-path-match — id frontmatter matches file path

  Required sections — per type + kind/archetype (+ corpus addendum)

  Confirmed/Flagged split — subsection splits (Flagged omitted when empty)

  Quote-verification blocks — in sections that require them

  Background prose-only — person nodes

  Internal-link resolution — body `[`/path`]` links + frontmatter
  node-path pointers (media.derivation_of, transcript.derived_from)
  share one existence-check pass. Missing targets register in the
  broken-link registry as backlog (not errors).

  Table-cell word-budget — soft warning

  Finding cross-ref consistency — entities listed must link back

  Verbatim-quote check — for every '> blockquote' followed by an
  attribution block whose Source row points at an archived file under
  `sources/`, extract the cited source to plaintext and confirm the
  quote appears as a substring (with whitespace/dash/quote-style
  normalization). Errors if the quote is not present, with a failure
  message naming the node, approximate line number of the block-quote,
  the cited source file, and a preview of the unmatched text.

  Runs unconditionally — confirmation against the underlying source
  is a precondition for inclusion in node bodies, not a marker the
  contributor opts into. The check has no rendered counterpart in node
  output (no Verified row) by design; the source link IS the evidence
  for readers, this check is the mechanical backstop against silent
  drift between an artifact's quote text and the source it claims to
  draw on. See meta/conventions.md.

  Requires `pdftotext` for PDF sources (poppler-utils on Linux);
  HTML/TXT sources read directly. PDFs flagged
  `extraction_type: ocr-scan` in sources/manifest.yaml prefer a
  same-stem `.txt` sibling (clean transcription) over pdftotext output.

  Manifest-checksum check — for every archived entry in
  sources/manifest.yaml, recompute SHA256 and compare to stored value.
  Errors on: file missing on disk, missing sha256 field when required,
  checksum mismatch (silent corruption / substitution). Run once per
  validator invocation, before the per-node checks.

  Governance-frontmatter check — every .md file under meta/ must carry
  id / type / schema_version / created; schema_version must be in
  schema.compatible_with; id must match file path. Templates routed
  through a placeholder-aware regex path because their `{{slug}}` /
  `{{today}}` values can't be YAML-parsed cleanly.

  Conditionally-required check — schema-driven enforcement of
  `types.{T}.conditionally_required` entries. Condition grammar:
  `<field> == <literal>`, `<field> is set`. Keys route to frontmatter-
  field presence+vocabulary checks (lowercase names) or section-
  presence checks (Title Case names).

  Chronological-ordering check — every markdown table with a date-
  bearing column (Date / Date / Time / Period / Start / Date Captured /
  Date Released / Dates) is ordered earliest-first. Range cells take
  the leftmost date; missing month / day default to 0 so
  '2004' < '2004-11' < '2004-11-14'. Rows in disorder error; cells
  with unparseable date strings warn. Universal discipline across
  every node type and section. Upgrades the schema's
  `chronological: true` flag from descriptive-only to enforced.

Usage:
  validate.py                    # all nodes
  validate.py PATH               # single node
  validate.py --quiet            # errors only

Cross-referencing: other docs / scripts refer to these checks by topic
name (e.g., `the verbatim-quote check`, `the prose-drift check` in
validate-research.py). See meta/conventions.md "Check naming".
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from lib._common import (
    strict_yaml_load,
    MANIFEST_PATH,
    REPO_ROOT,
    append_issue_log,
    content_dirs,
    load_schema,
    parse_frontmatter,
    resolve_cli_path,
)

# Per-check modules. Each named check lives at scripts/checks/{name}.py;
# orchestrator dispatches via the explicit step lists below.
from checks import BaseContext, Issue, NodeContext
from checks import chronological_tables as ck_chronological_tables
from checks import conditionally_required as ck_conditionally_required
from checks import doc_form_archival_status as ck_doc_form_archival_status
from checks import frontmatter_parse as ck_frontmatter_parse
from checks import frontmatter_required as ck_frontmatter_required
from checks import governance_files as ck_governance_files
from checks import id_path_match as ck_id_path_match
from checks import link_resolution as ck_link_resolution
from checks import manifest_archive_status as ck_manifest_archive_status
from checks import manifest_checksums as ck_manifest_checksums
from checks import manifest_extraction_type as ck_manifest_extraction_type
from checks import manifest_parse as ck_manifest_parse
from checks import manifest_value_enums as ck_manifest_value_enums
from checks import required_sections as ck_required_sections
from checks import schema_version_compat as ck_schema_version_compat
from checks import section_rules as ck_section_rules
from checks import status_archetype_kind as ck_status_archetype_kind
from checks import table_cell_word_budget as ck_table_cell_word_budget
from checks import verbatim_quotes as ck_verbatim_quotes

# =============================================================================
# Per-node validation orchestration
# =============================================================================


# Per-node check step list. Order matters where shared state in the
# NodeContext lazy caches benefits later checks (h2_sections /
# section_text), but each check is otherwise independent.
_NODE_CHECKS = [
    ck_frontmatter_required,
    ck_schema_version_compat,
    ck_id_path_match,
    ck_status_archetype_kind,
    ck_doc_form_archival_status,
    ck_conditionally_required,
    ck_required_sections,
    ck_section_rules,
    ck_verbatim_quotes,
    ck_chronological_tables,
    ck_link_resolution,            # writes to ctx.broken_links; yields no Issues
    ck_table_cell_word_budget,
]


def validate_node(path, base_ctx):
    """Run the per-node check chain against a single content node.

    Phase 1 — read text + parse frontmatter once. ``parse_frontmatter``
    is total (returns None on absent delimiters or YAMLError), so no
    try/except is needed; None signals failure.
    Phase 2 — preflight (``frontmatter_parse``) inspects ctx.fm and
    yields fatal Issues for missing FM, missing 'type', or unknown
    type. Fatal short-circuits the main chain.
    Phase 3 — full NodeContext reuses the parsed frontmatter; main
    ``_NODE_CHECKS`` chain dispatches.

    ``broken_links`` accumulate in ``base_ctx.broken_links``
    (out-of-band metadata channel); main() reads the registry after
    all nodes process.
    """
    issues = []
    text = path.read_text()
    rel = path.relative_to(REPO_ROOT)

    # Single frontmatter parse. None signals any failure mode (absent
    # delimiters, YAMLError) per parse_frontmatter's contract.
    fm, _ = parse_frontmatter(text)

    # Preflight against a minimal NodeContext (text + fm + base only).
    # The frontmatter_parse check inspects ctx.fm and yields fatal
    # Issues for malformed FM, missing 'type', or unknown type — all
    # preconditions for the main chain's NodeContext shape.
    preflight_ctx = NodeContext(base_ctx, path=path, rel=rel, text=text, fm=fm)
    preflight_issues = list(ck_frontmatter_parse.check(preflight_ctx))
    issues.extend(preflight_issues)
    if any(i.fatal for i in preflight_issues):
        return issues

    node_type = fm["type"]
    type_spec = base_ctx.schema["types"][node_type]

    # Full NodeContext for the main check chain. Reuses the parsed
    # frontmatter from above — single parse per node.
    node_ctx = NodeContext(
        base_ctx, path=path, rel=rel, text=text,
        fm=fm, node_type=node_type, type_spec=type_spec,
    )

    for check_module in _NODE_CHECKS:
        check_name = getattr(check_module, "CHECK_NAME", None) or check_module.__name__
        try:
            fresh = list(check_module.check(node_ctx))
        except Exception as e:
            import traceback
            fresh = [Issue(
                node_ctx.rel, "error",
                f"check {check_name!r} crashed: {type(e).__name__}: {e}\n"
                f"{traceback.format_exc()}",
                check_name=check_name, fatal=True,
            )]
        issues.extend(fresh)
        if any(i.fatal for i in fresh):
            break

    return issues


# =============================================================================
# Node collection
# =============================================================================


def collect_nodes():
    nodes = []
    for d in content_dirs():
        cd = REPO_ROOT / d
        if cd.is_dir():
            nodes.extend(sorted(cd.glob("*.md")))
    return nodes


# =============================================================================
# Main — CLI, orchestration, and report formatting
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help="Single node path (optional)")
    parser.add_argument("--quiet", action="store_true", help="Errors only")
    args = parser.parse_args()

    schema = load_schema()
    nodes = [resolve_cli_path(args.path)] if args.path else collect_nodes()

    all_issues = []

    # Single manifest load shared across the manifest-integrity checks
    # via BaseContext.manifest_entries. Parse failures fall through to
    # the ``manifest_parse`` preflight check, which produces the
    # contributor-facing diagnostic.
    manifest_entries = []
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH) as f:
                loaded = strict_yaml_load(f)
            if isinstance(loaded, list):
                manifest_entries = loaded
        except yaml.YAMLError:
            pass  # manifest_parse preflight yields the Issue

    base_ctx = BaseContext(schema=schema, manifest_entries=manifest_entries)

    # Manifest-integrity preflight. Skip downstream manifest checks on a
    # fatal Issue (parse failure / non-list root) — they would no-op on
    # the empty fallback and pollute the report.
    manifest_parse_issues = list(ck_manifest_parse.check(base_ctx))
    all_issues.extend(manifest_parse_issues)
    if not any(i.fatal for i in manifest_parse_issues):
        # Manifest-integrity family — content-byte integrity (sha256)
        # plus the manifest's closed enums (status / format /
        # extraction_type / archive_status). A checksum mismatch means
        # downstream quote verifications may be validating against
        # altered source material.
        all_issues.extend(ck_manifest_checksums.check(base_ctx))
        all_issues.extend(ck_manifest_archive_status.check(base_ctx))
        all_issues.extend(ck_manifest_extraction_type.check(base_ctx))
        all_issues.extend(ck_manifest_value_enums.check(base_ctx))

    # Governance-file validation. Runs regardless of --path argument
    # since template drift propagates to every node scaffolded afterward.
    all_issues.extend(ck_governance_files.check(base_ctx))

    for node in nodes:
        all_issues.extend(validate_node(node, base_ctx))

    # broken_links accumulate into base_ctx.broken_links via
    # ck_link_resolution — out-of-band metadata channel; broken stubs
    # are backlog signal, not violations, so they never appear as Issues.
    broken_links = base_ctx.broken_links

    # Append every emitted Issue to the issue log for time-series audit.
    # Validator-emitted entries; manual web-audit / contributor entries
    # are appended directly to the log file with the same shape.
    for issue in all_issues:
        append_issue_log(issue, source="validator", phase="validate")

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warn"]

    print("=" * 64)
    print(" Validation Report")
    print("=" * 64)
    print(f"\n  Nodes scanned: {len(nodes)}")
    print(f"  Errors:        {len(errors)}")
    if not args.quiet:
        print(f"  Warnings:      {len(warnings)}")
    print(f"  Broken links:  {len(broken_links)} unbuilt-stub targets (backlog)")

    if all_issues:
        print("\n" + "-" * 64)
        print(" Issues")
        print("-" * 64)
        by_file = defaultdict(list)
        for issue in all_issues:
            if args.quiet and issue.level != "error":
                continue
            by_file[issue.path].append(issue)
        for f in sorted(by_file.keys()):
            print(f"\n  {f}")
            for issue in by_file[f]:
                tag = "ERROR" if issue.level == "error" else "WARN "
                print(f"    [{tag}] {issue.message}")

    if broken_links and not args.quiet:
        print("\n" + "-" * 64)
        print(" Broken Link Registry")
        print("-" * 64)
        for link in sorted(broken_links.keys()):
            refs = sorted(broken_links[link])
            print(f"\n  {link} ({len(refs)} ref{'s' if len(refs) != 1 else ''})")
            for r in refs:
                print(f"    <- {r}")

    print("\n" + "=" * 64)
    if errors:
        print(f"  FAILED — {len(errors)} error(s)")
        sys.exit(1)
    print(f"  PASSED — {len(warnings)} warning(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
