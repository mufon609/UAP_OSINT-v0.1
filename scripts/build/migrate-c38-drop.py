#!/usr/bin/env python3
"""C38.3 — drop `entities_referenced[]` from every research artifact.

Per `meta/roadmap.md` "C38" (drop chosen; C38.1 triage found the
relocatable set ≈ 0): removes the entire `entities_referenced:` block
from each artifact. Body `[`/path`]` wraps are untouched — they remain
the cross-reference mechanism (broken-link registry + Associated
Nodes), so the registry is unchanged by construction.

SURGICAL, text-level removal. Only the `entities_referenced` block
(header + its entries) is spliced out; every other byte is preserved
exactly. NOT a YAML load-and-dump (that would reformat the file and
drop hand-authored comments / single-quoted scalars). Each edit is
self-checked: the post-removal text must re-parse and must no longer
carry an `entities_referenced` key.

DRY-RUN by default (report only). Pass `--apply` to write.

Usage:
  migrate-c38-drop.py            # dry-run → /tmp/c38-drop-plan/
  migrate-c38-drop.py --apply
"""

import argparse
import difflib
import glob
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT  # noqa: E402

RESEARCH_DIR = REPO_ROOT / "meta" / "research"
DEFAULT_OUT = Path("/tmp/c38-drop-plan")

_HEADER_RE = re.compile(r"^entities_referenced:[ \t]*$")
_TOP_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:")


class DropError(Exception):
    """A planned edit failed its self-check; the file is left untouched."""


def drop_block(text):
    """Return (new_text, n_entries_removed). Removes the block-form
    `entities_referenced:` section (header + entries). Raises DropError
    if the result doesn't re-parse or still carries the key."""
    lines = text.splitlines(keepends=True)
    header_idx = next(
        (i for i, l in enumerate(lines) if _HEADER_RE.match(l)), None)
    if header_idx is None:
        raise DropError("no block-form entities_referenced section found")

    block_end = len(lines)
    for j in range(header_idx + 1, len(lines)):
        if _TOP_KEY_RE.match(lines[j]):
            block_end = j
            break

    # Count entries from the parsed list, not by counting dash lines —
    # nested `- quote_id:` items under references[] are also dashes and
    # would inflate a line-based count.
    try:
        parsed_before = yaml.safe_load(text)
        n_entries = len((parsed_before or {}).get("entities_referenced") or [])
    except yaml.YAMLError:
        n_entries = 0
    new_lines = lines[:header_idx] + lines[block_end:]
    new_text = "".join(new_lines)

    # --- self-check ---
    try:
        parsed = yaml.safe_load(new_text)
    except yaml.YAMLError as ex:
        raise DropError(f"post-removal text does not parse: {ex}")
    if not isinstance(parsed, dict):
        raise DropError("post-removal root is not a mapping")
    if "entities_referenced" in parsed:
        raise DropError("entities_referenced key still present after removal")
    return new_text, n_entries


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run, report only)")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"dry-run diff/report dir (default {DEFAULT_OUT})")
    args = ap.parse_args()

    out_dir = Path(args.out)
    if not args.apply:
        out_dir.mkdir(parents=True, exist_ok=True)

    files_changed = total_entries = 0
    errors = []

    for f in sorted(glob.glob(str(RESEARCH_DIR / "*.yaml"))):
        text = Path(f).read_text()
        if not any(_HEADER_RE.match(l) for l in text.splitlines()):
            continue  # no block-form entities_referenced (already dropped / absent)
        slug = Path(f).stem
        try:
            new_text, n = drop_block(text)
        except DropError as ex:
            errors.append(f"{slug}: {ex}")
            continue
        files_changed += 1
        total_entries += n
        if args.apply:
            Path(f).write_text(new_text)
        else:
            diff = "".join(difflib.unified_diff(
                text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{slug}.yaml", tofile=f"b/{slug}.yaml"))
            (out_dir / f"{slug}.diff").write_text(diff)

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print("=" * 64)
    print(f" C38.3 — drop entities_referenced from all artifacts [{mode}]")
    print("=" * 64)
    print(f"\n  Artifacts with the field:  {files_changed}")
    print(f"  Entries removed:           {total_entries}")
    if errors:
        print(f"\n  !! {len(errors)} artifact(s) SKIPPED (self-check failed):")
        for e in errors:
            print(f"     - {e}")
    if not args.apply:
        print(f"\n  Per-artifact diffs: {out_dir}/  — review, then re-run --apply.")
    else:
        print("\n  Applied. Run validate.py + validate-research.py + "
              "review-coverage.py as the regression guard.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
