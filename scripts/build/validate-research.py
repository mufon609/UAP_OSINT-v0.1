#!/usr/bin/env python3
"""
Validate research artifacts against meta/schema.yaml.

Structural checks only — does NOT compare against the target node
(that's scripts/build/review-coverage.py).

Per-check modules live in scripts/checks/. This file is the orchestrator:
loads schema + manifest, iterates artifacts, dispatches checks via
explicit step lists per design doc §5 (no auto-discovery — adding /
removing a check is one line in _PRE_PARSE_CHECKS or _ARTIFACT_CHECKS
below). Pre-commit gates each step.

Pre-parse checks (raw lines, before strict_yaml_load):
  - yaml_hash_truncation, yaml_colon_space

Per-artifact checks (after parse + ResearchContext construction):
  - artifact_top_level                — top-level required keys, schema-
                                         version compat, target_node
                                         existence, person/event prose
                                         keys, description-required.
  - primary_sources, quotes, entities, naming_quirks
  - rumors, timeline                  — type-conditional
  - corroboration_items, program_involvement, publication_record,
    vouching_chain                    — archetype/kind-conditional
  - affiliations, relationships       — person-conditional
  - participants, witnesses_testimony — event-conditional
  - speakers                          — transcript-conditional
  - media_versioning                  — media-conditional
  - key_personnel, org_relationships, contracts
                                       — organization / gov-contractor
  - ownership_timeline, top_scope_activity, location_relationships
                                       — location-conditional
  - cross_refs, prose_drift           — whole-artifact

Each check self-gates on target type/archetype/kind so the orchestrator
runs the full step list against every artifact and the check decides
whether to emit Issues.

Usage:
  validate-research.py                  # validate all meta/research/*.yaml
  validate-research.py PATH             # validate one file
  validate-research.py --quiet          # errors only
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

# scripts/build/validate-research.py — put the scripts/ parent on sys.path
# so `from lib._common` and `from checks` resolve from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (
    strict_yaml_load,
    REPO_ROOT,
    append_issue_log,
    content_type_dirs,
    load_manifest_paths,
    load_schema,
    resolve_cli_path,
)

from checks import BaseContext, Issue, ResearchContext

# Pre-parse checks (raw line scans before strict_yaml_load)
from checks import yaml_colon_space as ck_yaml_colon_space
from checks import yaml_hash_truncation as ck_yaml_hash_truncation

# Parse preflight (file existence + YAML root shape)
from checks import artifact_parse as ck_artifact_parse

# Per-artifact checks (after parse)
from checks import affiliations as ck_affiliations
from checks import artifact_top_level as ck_artifact_top_level
from checks import cited_findings as ck_cited_findings
from checks import closure_path as ck_closure_path
from checks import contracts as ck_contracts
from checks import contradictions as ck_contradictions
from checks import corroboration_items as ck_corroboration_items
from checks import cross_refs as ck_cross_refs
from checks import does_not_establish as ck_does_not_establish
from checks import entities_referenced as ck_entities_referenced
from checks import establishes as ck_establishes
from checks import finding_no_investigation_refs as ck_finding_no_investigation_refs
from checks import hypotheses as ck_hypotheses
from checks import iff_section as ck_iff_section
from checks import investigation_closure_path_when_paused as ck_investigation_closure_path_when_paused
from checks import investigation_hypothesis_citation as ck_investigation_hypothesis_citation
from checks import key_personnel as ck_key_personnel
from checks import location_relationships as ck_location_relationships
from checks import media_versioning as ck_media_versioning
from checks import naming_quirks as ck_naming_quirks
from checks import open_questions as ck_open_questions
from checks import org_relationships as ck_org_relationships
from checks import ownership_timeline as ck_ownership_timeline
from checks import participants as ck_participants
from checks import primary_sources as ck_primary_sources
from checks import program_involvement as ck_program_involvement
from checks import prose_drift as ck_prose_drift
from checks import publication_record as ck_publication_record
from checks import quotes as ck_quotes
from checks import relationships as ck_relationships
from checks import resolution_history as ck_resolution_history
from checks import rumors as ck_rumors
from checks import speakers as ck_speakers
from checks import timeline as ck_timeline
from checks import top_scope_activity as ck_top_scope_activity
from checks import vouching_chain as ck_vouching_chain
from checks import witnesses_testimony as ck_witnesses_testimony


# =============================================================================
# Constants
# =============================================================================
#
# REPO_ROOT, load_schema, load_manifest_paths, content_type_dirs() come
# from lib._common — shared with every other script that walks the
# content layer.

RESEARCH_DIR = REPO_ROOT / "meta" / "research"


# =============================================================================
# Loading
# =============================================================================

def _read_target_frontmatter(target_path):
    """Read a target-node file's frontmatter and return it as a dict
    (archetype / kind / etc.), or {} on any failure. Used to route
    archetype-specific and kind-specific section requirements.
    """
    try:
        text = target_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        return strict_yaml_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _discover_target(data):
    """Discover target_type / target_archetype / target_kind /
    target_derivation_of / target_status from the artifact's
    target_node and the target node's frontmatter. Returns 5-tuple
    of None when target_node isn't set or doesn't resolve.

    ``target_status`` is the node's frontmatter ``status`` value
    (e.g., ``open`` / ``paused`` / ``closed`` for investigation,
    ``documented`` / ``in-progress`` / ``superseded`` for finding).
    Used by checks that gate on the node's status — currently
    ``investigation_closure_path_when_paused``.
    """
    target_node = data.get("target_node") or ""
    if "/" not in target_node:
        return None, None, None, None, None

    content_dir_name = target_node.split("/", 1)[0]
    reverse_map = {v: k for k, v in content_type_dirs().items()}
    target_type = reverse_map.get(content_dir_name)

    target_path = REPO_ROOT / f"{target_node}.md"
    if not target_path.exists():
        return target_type, None, None, None, None

    fm = _read_target_frontmatter(target_path)
    target_archetype = fm.get("archetype") if target_type == "person" else None
    target_kind = (
        fm.get("kind") if target_type in ("event", "transcript", "organization") else None
    )
    target_derivation_of = fm.get("derivation_of") if target_type == "media" else None
    target_status = fm.get("status")

    return target_type, target_archetype, target_kind, target_derivation_of, target_status


# =============================================================================
# Per-check step lists
# =============================================================================
#
# Pre-parse checks operate on ctx.raw_lines before strict_yaml_load.
# Per-artifact checks operate on ctx.data after parse + target discovery.
# Each check self-gates by target_type/kind/archetype; the orchestrator
# runs every check against every artifact.

_PRE_PARSE_CHECKS = [
    ck_yaml_hash_truncation,
    ck_yaml_colon_space,
]

_ARTIFACT_CHECKS = [
    # Universal top-level metadata
    ck_artifact_top_level,
    # Schema-driven iff-section dispatch (placement errors based on
    # schema.yaml::conditional_keys). Per-section checks below gate
    # on section_in_scope and skip per-entry validation when the
    # section is wrongly placed; iff_section carries the placement
    # error so each placement issue produces one diagnostic, not many.
    ck_iff_section,
    # Universal entry-list checks
    ck_primary_sources,
    ck_quotes,
    ck_entities_referenced,
    ck_naming_quirks,
    # Type-conditional entry-list checks
    ck_rumors,
    ck_timeline,
    # Archetype / kind-conditional entry-list checks
    ck_corroboration_items,
    ck_program_involvement,
    ck_publication_record,
    ck_vouching_chain,
    ck_affiliations,
    ck_relationships,
    ck_participants,
    ck_witnesses_testimony,
    ck_speakers,
    ck_media_versioning,
    ck_key_personnel,
    ck_org_relationships,
    ck_contracts,
    ck_ownership_timeline,
    ck_top_scope_activity,
    ck_location_relationships,
    # Finding / investigation per-section entry-shape checks
    ck_establishes,
    ck_does_not_establish,
    ck_contradictions,
    ck_hypotheses,
    ck_cited_findings,
    ck_open_questions,
    ck_closure_path,
    ck_resolution_history,
    # Finding / investigation type-specific cross-cutting checks
    ck_finding_no_investigation_refs,
    ck_investigation_hypothesis_citation,
    ck_investigation_closure_path_when_paused,
    # Whole-artifact analytical checks
    ck_cross_refs,
    ck_prose_drift,
]


# =============================================================================
# Per-artifact orchestration
# =============================================================================

def validate_artifact(path, base_ctx):
    """Run the per-artifact check chain against a single research artifact.

    Phase 1 — read raw_lines + parse YAML once. YAMLError captured into
    ``parse_error``; OSError yields empty raw_lines (artifact_parse
    preflight catches the missing-file case via ctx.path.exists()).
    Phase 2 — pre-parse checks on raw lines (yaml_hash_truncation,
    yaml_colon_space).
    Phase 3 — parse preflight (``artifact_parse`` check) inspects
    ctx.path / ctx.parse_error / ctx.data and yields fatal Issues for
    missing file, parse error, or non-dict root. Fatal short-circuits.
    Phase 4 — target type/archetype/kind discovery from the target
    node's frontmatter; full ResearchContext reuses the parsed data.
    Phase 5 — each per-artifact check runs against the context. Each
    check self-gates on target_type/kind/archetype.
    """
    issues = []
    rel = path.relative_to(REPO_ROOT)

    # Single load + parse. raw_lines and data come from the same read
    # window so the orchestrator never opens the file twice.
    raw_lines = []
    data = None
    parse_error = None
    if path.exists():
        try:
            with open(path) as f:
                text = f.read()
            raw_lines = text.splitlines(keepends=True)
            try:
                data = strict_yaml_load(text)
            except yaml.YAMLError as e:
                parse_error = str(e)
        except OSError:
            pass  # raw_lines stays []; artifact_parse catches missing file

    # Pre-parse: ResearchContext minimal (raw_lines only; data + parse_error
    # carried for the artifact_parse preflight that follows).
    pre_ctx = ResearchContext(
        base_ctx, path=path, rel=rel, raw_lines=raw_lines,
        data=data, parse_error=parse_error,
    )
    for check_module in _PRE_PARSE_CHECKS:
        issues.extend(check_module.check(pre_ctx))

    # Parse preflight — yields fatal Issues for missing file / YAML
    # parse failure / non-dict root. Short-circuit chain on fatal since
    # downstream Context needs ctx.data populated.
    parse_issues = list(ck_artifact_parse.check(pre_ctx))
    issues.extend(parse_issues)
    if any(i.fatal for i in parse_issues):
        return issues

    # Target discovery (reads target node's frontmatter)
    (target_type, target_archetype, target_kind,
     target_derivation_of, target_status) = _discover_target(data)

    # Full ResearchContext for per-artifact checks. Reuses the parsed
    # data from above — single parse per artifact.
    ctx = ResearchContext(
        base_ctx, path=path, rel=rel, raw_lines=raw_lines, data=data,
        parse_error=parse_error,
        target_type=target_type, target_archetype=target_archetype,
        target_kind=target_kind, target_derivation_of=target_derivation_of,
        target_status=target_status,
    )

    for check_module in _ARTIFACT_CHECKS:
        check_name = getattr(check_module, "CHECK_NAME", None) or check_module.__name__
        try:
            fresh = list(check_module.check(ctx))
        except Exception as e:
            import traceback
            fresh = [Issue(
                ctx.rel, "error",
                f"check {check_name!r} crashed: {type(e).__name__}: {e}\n"
                f"{traceback.format_exc()}",
                check_name=check_name, fatal=True,
            )]
        issues.extend(fresh)
        if any(i.fatal for i in fresh):
            break

    return issues


# =============================================================================
# Main
# =============================================================================

def collect_artifacts():
    if not RESEARCH_DIR.is_dir():
        return []
    return sorted(RESEARCH_DIR.glob("*.yaml"))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="Single artifact path (optional)")
    parser.add_argument("--quiet", action="store_true", help="Errors only")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print full structured payload (e.g., the complete unmatched-"
             "token list on prose-drift warnings) inline below each issue. "
             "Default keeps the truncated terminal-friendly preview.")
    args = parser.parse_args()

    schema = load_schema()
    manifest_paths = load_manifest_paths()
    base_ctx = BaseContext(schema=schema, manifest_paths=manifest_paths)

    if args.path:
        artifacts = [resolve_cli_path(args.path)]
    else:
        artifacts = collect_artifacts()

    all_issues = []
    for p in artifacts:
        all_issues.extend(validate_artifact(p, base_ctx))

    # Append every emitted Issue to the issue log for time-series audit.
    for issue in all_issues:
        append_issue_log(issue, source="validator", phase="validate-research")

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warn"]

    print("=" * 64)
    print(" Research-Artifact Validation Report")
    print("=" * 64)
    print(f"\n  Artifacts scanned: {len(artifacts)}")
    print(f"  Errors:            {len(errors)}")
    if not args.quiet:
        print(f"  Warnings:          {len(warnings)}")

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
                if args.verbose and issue.tokens:
                    print(f"           full payload: {', '.join(issue.tokens)}")

    print("\n" + "=" * 64)
    if errors:
        print(f"  FAILED — {len(errors)} error(s)")
        sys.exit(1)
    print(f"  PASSED — {len(warnings)} warning(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
