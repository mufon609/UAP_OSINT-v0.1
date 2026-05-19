#!/usr/bin/env python3
"""
Regenerate a content-node body from its research artifact (Phase II).

This is the orchestrator. Per-type rendering logic lives in
``scripts/build/renderers/`` — one module per node type
(document / person / event / transcript / media / organization /
location / finding / investigation), plus ``_common.py`` (shared
helpers) and ``_universal.py`` (sections shared across types).

The orchestrator handles:

  - argparse + main()
  - artifact and frontmatter loading (via ``renderers._common``)
  - top-level dispatch by node_type to the per-type ``render_body_X``
  - node-body composition (frontmatter + body)
  - pre-flight + post-build validator invocation (subprocesses)
  - post-build ``scripts/build/associate.py`` invocation

The body of any individual node type is regenerated from its research
artifact via:

  python3 scripts/build/build-from-research.py meta/research/{slug}.yaml

Flags:
  --dry-run        : render to stdout only — do not write or invoke associate/validate
  --no-validate    : skip pre-flight research-artifact validation and
                     post-build node validation (speed / debugging)

PIPELINE WIRING:
  Pre-flight:  python3 scripts/build/validate-research.py {artifact} --quiet
  Regenerate:  this script (writes node body)
  Post-step:   python3 scripts/build/associate.py {node}   (rewrites Associated Nodes)
  Validate:    python3 scripts/build/validate.py {node}
"""

import argparse
import subprocess
import sys
from pathlib import Path


# scripts/build/build-from-research.py — put the scripts/ parent on
# sys.path so `from lib._common` and `from renderers.X` resolve from
# this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (
    REPO_ROOT,
    content_type_dirs,
    supported_types,
)

from renderers._common import load_artifact, load_frontmatter
from renderers.document import render_body_document
from renderers.person import render_body_person
from renderers.event import render_body_event
from renderers.transcript import render_body_transcript
from renderers.media import render_body_media
from renderers.organization import render_body_organization
from renderers.location import render_body_location
from renderers.finding import render_body_finding
from renderers.investigation import render_body_investigation


BUILD_DIR = REPO_ROOT / "scripts" / "build"
VALIDATE_RESEARCH = BUILD_DIR / "validate-research.py"
VALIDATE_NODE = BUILD_DIR / "validate.py"
ASSOCIATE = BUILD_DIR / "associate.py"

# Content-node type → directory, derived from schema. Single source
# of truth across every contributor script.
TYPE_DIRS = content_type_dirs()


# =============================================================================
# Top-level dispatch
# =============================================================================

def render_body(artifact, node_type, fm):
    """Dispatch by node_type. `fm` is the existing node frontmatter
    (needed for kind / archetype context the renderer can't derive from
    the artifact alone)."""
    if node_type == "document":
        return render_body_document(artifact, fm.get("kind"))
    if node_type == "person":
        return render_body_person(artifact, fm.get("archetype"))
    if node_type == "event":
        return render_body_event(artifact, fm.get("kind"))
    if node_type == "transcript":
        return render_body_transcript(artifact, fm.get("kind"), fm)
    if node_type == "media":
        return render_body_media(artifact, fm.get("kind"), fm)
    if node_type == "organization":
        return render_body_organization(artifact, fm.get("kind"))
    if node_type == "location":
        return render_body_location(artifact, fm)
    if node_type == "finding":
        return render_body_finding(artifact, fm)
    if node_type == "investigation":
        return render_body_investigation(artifact, fm)
    sys.exit(f"ERROR: build-from-research.py does not yet support node_type {node_type!r}")


def compose_node(raw_frontmatter, body):
    return raw_frontmatter.rstrip() + "\n\n" + body.lstrip()


# =============================================================================
# Pre-flight / post-build validators
# =============================================================================

def preflight_validate_artifact(artifact_path):
    proc = subprocess.run(
        ["python3", str(VALIDATE_RESEARCH), str(artifact_path), "--quiet"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        sys.exit("ERROR: research artifact failed validation — aborting build.")


def post_build_validate(node_path):
    proc = subprocess.run(
        ["python3", str(VALIDATE_NODE), str(node_path)],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def run_associate(node_path):
    subprocess.run(
        ["python3", str(ASSOCIATE), str(node_path)],
        check=False,
    )


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("artifact", help="Path to research artifact (meta/research/{slug}.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Render to stdout, do not write node or invoke associate/validate")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip pre-flight research-validation and post-build node-validation")
    args = parser.parse_args()

    artifact_path = Path(args.artifact).resolve()
    if not artifact_path.exists():
        sys.exit(f"ERROR: artifact not found: {artifact_path}")

    if not args.no_validate:
        preflight_validate_artifact(artifact_path)

    artifact = load_artifact(artifact_path)

    target_node = artifact.get("target_node") or ""
    if "/" not in target_node:
        sys.exit(f"ERROR: artifact target_node {target_node!r} is malformed")
    dir_name, slug = target_node.split("/", 1)
    reverse = {v: k for k, v in TYPE_DIRS.items()}
    node_type = reverse.get(dir_name)
    if node_type is None:
        sys.exit(f"ERROR: unknown content-dir {dir_name!r} in target_node")
    if node_type not in supported_types():
        sys.exit(f"ERROR: build-from-research.py currently supports "
                 f"{sorted(supported_types())} only (got {node_type!r}).")

    node_path = REPO_ROOT / dir_name / f"{slug}.md"
    if not node_path.exists():
        sys.exit(f"ERROR: target node does not exist: {node_path.relative_to(REPO_ROOT)}\n"
                 f"  Run scripts/build/new.py to scaffold the node first.")

    fm, raw_fm = load_frontmatter(node_path)
    if fm is None or raw_fm is None:
        sys.exit(f"ERROR: cannot parse frontmatter of {node_path.relative_to(REPO_ROOT)}")

    body = render_body(artifact, node_type, fm)
    new_text = compose_node(raw_fm, body)

    if args.dry_run:
        sys.stdout.write(new_text)
        return

    node_path.write_text(new_text)
    print(f"✓ Regenerated {node_path.relative_to(REPO_ROOT)} "
          f"from {artifact_path.relative_to(REPO_ROOT)}")

    run_associate(node_path)

    if not args.no_validate:
        ok = post_build_validate(node_path)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
