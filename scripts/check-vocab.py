#!/usr/bin/env python3
"""Pre-flight vocabulary check for prose-drift discipline.

Reports whether each provided token appears in the pooled
significant-token set of an artifact's primary sources, mirroring the
tokenization used by `validate-research.py`'s prose-drift check. Output
reflects what the validator would see — there is no parallel
implementation that can drift.

Use case: drafting `description` / `background` / `uap_relevance` /
`credibility_notes` prose (or per-entry synthesis content notes:
`ownership_timeline.note`, `key_personnel.note`, `contracts.note`,
`media_versioning.note`, `vouching_chain.attestation`). Per
`meta/conventions.md` "Prose-drift discipline on synthesis surfaces"
and the durable contributor policy in
`feedback_prose_drift_warnings_must_resolve.md`, every significant
token in those fields should be source-attested. This script lets a
contributor pre-flight a draft's vocabulary against the source pool
in a single tool call rather than iterating draft → validate → fix.

The canonical workflow is still iterative — draft prose, run
`validate-research.py`, fix surfaced warnings — and remains correct.
This script is a contributor convenience for cases where pre-flight
batch checking is genuinely useful (long source corpora, heavy
synthesis fields, drafting from cold context).

Usage:
    check-vocab.py --artifact research/{slug}.yaml token [token ...]

Examples:
    check-vocab.py --artifact research/oni.yaml affairs archived tenure
    check-vocab.py --artifact research/oni.yaml "senior civilian" "Public Affairs"

Output (per token):
    ✓ present  — every significant sub-token is in the source pool
    ✗ absent   — at least one significant sub-token is missing (listed)
    (skipped)  — input is shorter than min token length or all stopwords

Multi-word inputs are tokenized using the same logic as prose: each
significant sub-token is checked individually. "Public Affairs"
tokenizes to {public, affairs}; both must be present for the input to
register as ✓ present.

Exit codes:
    0 — diagnostic ran successfully (regardless of how many ✗ vs ✓);
        ✗ absent rows are informational findings, not errors
    1 — real error: artifact missing, artifact has no primary_sources,
        or every primary source failed extraction (pool would be empty)
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_validate_research():
    """Import scripts/validate-research.py via importlib so this script
    tracks the canonical tokenizer + extraction layer used by the
    validator. No duplicate implementation that can drift. The hyphen
    in the filename precludes a normal `import` statement.
    """
    spec = importlib.util.spec_from_file_location(
        "validate_research",
        SCRIPTS_DIR / "validate-research.py",
    )
    if spec is None or spec.loader is None:
        sys.exit("Could not locate scripts/validate-research.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Pre-flight vocabulary check for prose-drift discipline — "
            "reports whether each token appears in the pooled "
            "significant-token set of an artifact's primary sources, "
            "mirroring validate-research.py's tokenization."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  check-vocab.py --artifact research/oni.yaml affairs archived tenure\n"
            "  check-vocab.py --artifact research/oni.yaml \"senior civilian\" \"Public Affairs\"\n"
        ),
    )
    ap.add_argument(
        "--artifact",
        required=True,
        help="Path to research/{slug}.yaml — sources are pooled from its primary_sources list",
    )
    ap.add_argument(
        "tokens",
        nargs="+",
        help="One or more tokens (or multi-word phrases) to check against the pooled source vocabulary",
    )
    args = ap.parse_args()

    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        sys.exit(f"Artifact not found: {artifact_path}")

    with artifact_path.open() as f:
        artifact = yaml.safe_load(f)

    primary_sources = artifact.get("primary_sources") or []
    if not primary_sources:
        sys.exit(f"Artifact has no primary_sources: {artifact_path}")

    vr = _load_validate_research()

    pool = set()
    extracted_count = 0
    missing_sources = []
    for src in primary_sources:
        path = src.get("path") if isinstance(src, dict) else None
        if not path:
            continue
        tokens = vr.load_source_tokens(path)
        if tokens is None:
            missing_sources.append(path)
            continue
        pool |= tokens
        extracted_count += 1

    print(
        f"Pooled {len(pool)} significant tokens from "
        f"{extracted_count} of {len(primary_sources)} source(s)."
    )
    if missing_sources:
        print()
        print(f"⚠ {len(missing_sources)} source(s) failed extraction:")
        for p in missing_sources:
            print(f"  - {p}")

    if not pool:
        # Mirror validate-research.py's "no source text could be extracted"
        # short-circuit — diagnostic can't function with an empty pool.
        sys.exit(
            "\nError: pool is empty (no source text extracted). "
            "Check that primary_sources paths exist on disk and that "
            "pdftotext is available."
        )

    print()

    width = max(max(len(t) for t in args.tokens), 12)

    for raw in args.tokens:
        sub_tokens = vr.extract_significant_tokens(raw)
        if not sub_tokens:
            print(f"  {raw:<{width}}  (skipped — no significant tokens)")
            continue
        absent = sorted(t for t in sub_tokens if t not in pool)
        if absent:
            detail = ", ".join(absent)
            print(f"  {raw:<{width}}  ✗ absent  [{detail}]")
        else:
            print(f"  {raw:<{width}}  ✓ present")

    # ✗ absent findings are informational — diagnostic ran successfully.
    # Reserve non-zero exit for real errors (missing artifact / no
    # sources / pool empty), handled via sys.exit() above.
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
