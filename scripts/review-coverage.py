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
via an explicit step list. Skipped on unsupported types (finding pending
F.7 renderer).

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

from checks import BaseContext, Issue, ResearchContext
from checks import boundary as ck_boundary
from checks import coverage as ck_coverage
from checks import description_token_drift as ck_description_token_drift
from checks import stub_linking as ck_stub_linking
from lib._common import extract_source_text


# =============================================================================
# Constants
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
SOURCES_DIR = REPO_ROOT / "sources"
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"
RESEARCH_DIR = REPO_ROOT / "meta" / "research"

TYPE_DIRS = {
    "person": "people", "organization": "organizations", "document": "documents",
    "event": "events", "transcript": "transcripts", "media": "media",
    "location": "locations", "finding": "findings",
}

# Matches build-from-research.py SUPPORTED_TYPES. Expand in lockstep.
SUPPORTED_TYPES = {
    "document", "person", "event", "transcript", "media", "organization", "location",
}


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

def load_schema():
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def load_manifest_paths():
    if not MANIFEST_PATH.exists():
        return set()
    with open(MANIFEST_PATH) as f:
        entries = yaml.safe_load(f) or []
    return {e.get("path") for e in entries if e.get("path")}


def load_artifact(path):
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        sys.exit(f"ERROR: artifact parse failure: {e}")
    if not isinstance(data, dict):
        sys.exit(f"ERROR: artifact root is not a YAML mapping: {path}")
    return data


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
    reverse = {v: k for k, v in TYPE_DIRS.items()}
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
    """Return (issues, skipped_reason_or_None)."""
    rel = artifact_path.relative_to(REPO_ROOT)

    if not artifact_path.exists():
        return [Issue(rel, "error", "Artifact file does not exist",
                      check_name="review_coverage_load")], None

    artifact = load_artifact(artifact_path)

    node_path = target_node_path(artifact)
    if node_path is None or not node_path.exists():
        return [Issue(
            rel, "error",
            f"target_node {artifact.get('target_node')!r} does not point "
            f"to an existing file",
            check_name="review_coverage_load",
        )], None

    node_type = target_node_type(artifact)
    if node_type not in SUPPORTED_TYPES:
        return [], f"node type {node_type!r} not yet supported in Phase III (BACKLOG)"

    node_text = node_path.read_text()
    source_text, missing_sources = _gather_source_text(artifact)

    issues = []
    for path in missing_sources:
        full = SOURCES_DIR / path
        if not full.exists():
            issues.append(Issue(
                rel, "error",
                f"Description drift check: primary source {path!r} missing "
                f"— file not present on disk under sources/. Source-archival "
                f"integrity issue; verify the manifest entry and re-archive "
                f"if needed.",
                check_name="review_coverage_load",
            ))
        else:
            # File exists but isn't text-extractable — typical for binary
            # media. Non-blocking warn (matches verbatim-quote check
            # semantics in validate.py).
            issues.append(Issue(
                rel, "warn",
                f"Description drift check: primary source {path!r} not text-"
                f"extractable (likely binary media — video/audio/image). "
                f"Tokens from this source skipped; verbatim quote extraction "
                f"from media sources requires manual contributor verification.",
                check_name="review_coverage_load",
            ))

    ctx = ResearchContext(
        base_ctx, path=artifact_path, rel=rel,
        raw_lines=[],  # not needed by review-coverage checks
        data=artifact,
        node_path=node_path,
        node_text=node_text,
        source_text=source_text,
    )

    for check_module in _REVIEW_CHECKS:
        issues.extend(check_module.check(ctx))
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
        artifacts = [Path(args.path).resolve()]
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
