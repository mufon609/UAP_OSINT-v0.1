#!/usr/bin/env python3
"""
Phase III — Coverage review between a research artifact and its regenerated node.

Mechanical consistency checks run after Phase II build. Complements
validate.py (node structure + verbatim quotes) and validate-research.py
(artifact structure); this script compares the two layers against each
other.

Per-check modules live in scripts/checks/. This file is the orchestrator:
loads schema + manifest, iterates artifacts, dispatches the four cross-
layer checks (coverage, boundary, stub_linking, description_token_drift)
via an explicit step list. Skips on unsupported types (only runs against
types whose renderer ships in build-from-research.py).

This script handles mechanical rules only. Semantic / narrative-coherence
review (agent-assisted) is a separate pass referenced in
``prompts/build.md``.

Usage:
  review-coverage.py {artifact_path}
  review-coverage.py --all
  review-coverage.py --quiet

Expected execution order per prompts/build.md:
  validate-research.py {artifact}  →  build-from-research.py {artifact}
    →  validate.py {node}  →  review-coverage.py {artifact}
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
    REPO_ROOT,
    SOURCES_DIR,
    SUPPORTED_TYPES,
    append_issue_log,
    content_type_dirs,
    extract_source_text,
    load_manifest_paths,
    load_schema,
    resolve_cli_path,
)

from checks import BaseContext, Issue, ResearchContext
from checks import artifact_parse as ck_artifact_parse
from checks import boundary as ck_boundary
from checks import coverage as ck_coverage
from checks import description_token_drift as ck_description_token_drift
from checks import phase_iii_inputs as ck_phase_iii_inputs
from checks import stub_linking as ck_stub_linking


# =============================================================================
# Constants
# =============================================================================

RESEARCH_DIR = REPO_ROOT / "meta" / "research"


# =============================================================================
# Step list
# =============================================================================

_REVIEW_CHECKS = [
    ck_coverage,
    ck_boundary,
    ck_stub_linking,
    ck_description_token_drift,
]


# =============================================================================
# Helpers
# =============================================================================

def target_node_path(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    return REPO_ROOT / f"{target}.md"


def target_node_type(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    dir_name = target.split("/", 1)[0]
    reverse = {v: k for k, v in content_type_dirs().items()}
    return reverse.get(dir_name)


def _gather_source_text(artifact):
    """Concatenate plaintext of every archived primary source on the
    artifact. Returns (combined_text, missing_paths) where missing_paths
    is any primary_sources[].path that could not be extracted."""
    chunks = []
    missing = []
    for ps in (artifact.get("primary_sources") or []):
        if not isinstance(ps, dict):
            continue
        rel_path = ps.get("path")
        if not rel_path:
            continue
        # Binary primary sources (image/video/audio) are not text-
        # extractable by design — silent skip rather than warn.
        if ps.get("format") in ("image", "video", "audio"):
            continue
        full = SOURCES_DIR / rel_path
        if not full.exists():
            missing.append(rel_path)
            continue
        text = extract_source_text(full)
        if text is None:
            missing.append(rel_path)
            continue
        chunks.append(text)
    return "\n".join(chunks), missing


# =============================================================================
# Per-artifact orchestration
# =============================================================================

def review_artifact(artifact_path, base_ctx):
    """Return ``(issues, skipped_reason_or_None)``.

    Two-stage preflight before the main ``_REVIEW_CHECKS`` chain:
      1. ``artifact_parse`` — file exists, YAML parses, root is dict.
         Fatal short-circuits.
      2. ``phase_iii_inputs`` — target_node points to a real file +
         primary_sources are extractable. Fatal short-circuits (target
         missing); non-fatal warnings about source extraction flow into
         the final issue stream.

    Unsupported target types skip cleanly (skip != error) and never
    reach the preflight, since the four review checks are renderer-
    coupled and only meaningful where the renderer ships.
    """
    rel = artifact_path.relative_to(REPO_ROOT)
    issues = []

    # Single load + parse. YAMLError captured into parse_error; missing
    # file leaves both data and parse_error None (artifact_parse catches
    # the missing-file case via ctx.path.exists()).
    artifact = None
    parse_error = None
    if artifact_path.exists():
        try:
            with open(artifact_path) as f:
                artifact = strict_yaml_load(f)
        except yaml.YAMLError as e:
            parse_error = str(e)
        except OSError:
            pass

    pre_ctx = ResearchContext(
        base_ctx, path=artifact_path, rel=rel, raw_lines=[],
        data=artifact, parse_error=parse_error,
    )

    parse_issues = list(ck_artifact_parse.check(pre_ctx))
    issues.extend(parse_issues)
    if any(i.fatal for i in parse_issues):
        return issues, None

    # Parse preflight passed; downstream Context reuses the parsed dict.
    node_type = target_node_type(artifact)
    if node_type not in SUPPORTED_TYPES:
        return issues, f"node type {node_type!r} has no renderer; review checks skipped"

    node_path = target_node_path(artifact)
    node_text = node_path.read_text() if (node_path and node_path.exists()) else None
    source_text, _ = _gather_source_text(artifact) if node_text else ("", [])

    ctx = ResearchContext(
        base_ctx, path=artifact_path, rel=rel,
        raw_lines=[],  # not needed by review-coverage checks
        data=artifact,
        parse_error=parse_error,
        node_path=node_path,
        node_text=node_text,
        source_text=source_text,
    )

    # Phase III input integrity preflight — target_node existence
    # (fatal) + per-source extraction health (non-fatal).
    inputs_issues = list(ck_phase_iii_inputs.check(ctx))
    issues.extend(inputs_issues)
    if any(i.fatal for i in inputs_issues):
        return issues, None

    for check_module in _REVIEW_CHECKS:
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
    return issues, None


def collect_artifacts():
    if not RESEARCH_DIR.is_dir():
        return []
    return sorted(RESEARCH_DIR.glob("*.yaml"))


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?",
                        help="Research artifact path (meta/research/{slug}.yaml)")
    parser.add_argument("--all", action="store_true",
                        help="Review every artifact under meta/research/")
    parser.add_argument("--quiet", action="store_true",
                        help="Errors only; suppress info/skip notices")
    args = parser.parse_args()

    if args.path:
        artifacts = [resolve_cli_path(args.path)]
    elif args.all:
        artifacts = collect_artifacts()
    else:
        parser.print_help()
        sys.exit(0)

    schema = load_schema()
    manifest_paths = load_manifest_paths()
    base_ctx = BaseContext(schema=schema, manifest_paths=manifest_paths)

    all_issues = []
    reviewed = 0
    skipped = []

    for p in artifacts:
        issues, skip_reason = review_artifact(p, base_ctx)
        if skip_reason:
            skipped.append((p.relative_to(REPO_ROOT), skip_reason))
            continue
        reviewed += 1
        all_issues.extend(issues)

    # Append every emitted Issue to the issue log for time-series audit.
    for issue in all_issues:
        append_issue_log(issue, source="validator", phase="review-coverage")

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warn"]

    print("=" * 64)
    print(" Phase III — Coverage Review")
    print("=" * 64)
    print(f"\n  Artifacts reviewed: {reviewed}")
    print(f"  Skipped:            {len(skipped)}")
    print(f"  Errors:             {len(errors)}")
    if not args.quiet:
        print(f"  Warnings:           {len(warnings)}")

    if skipped and not args.quiet:
        print("\n" + "-" * 64)
        print(" Skipped")
        print("-" * 64)
        for p, reason in skipped:
            print(f"  {p} — {reason}")

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

    print("\n" + "=" * 64)
    if errors:
        print(f"  FAILED — {len(errors)} error(s)")
        sys.exit(1)
    print(f"  PASSED — {len(warnings)} warning(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
