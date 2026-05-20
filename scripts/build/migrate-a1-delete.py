#!/usr/bin/env python3
"""A1.4 — delete redundant entities_referenced[] entries (corpus migration).

Consumes the A1.1 audit (``audit-a1-vocab.py`` → ``audit.json``) and
removes the redundant entries — every entry NOT classified
``a-preserve`` at the audit's substantive threshold — from each research
artifact, keeping the curated substantive entries and their
``references[]``. Per plan B (``meta/roadmap.md`` "A1"):
``entities_referenced`` becomes a small curated synthesis surface.

SURGICAL, text-level removal. Only the deleted entries' line-spans are
spliced out; every other byte (comments, single-quoted scalars,
ordering, formatting) is preserved exactly. This is deliberately NOT a
YAML load-and-dump — round-tripping through PyYAML would reformat the
whole file, drop hand-authored comments, and normalize the
single-quoted-scalar prose style the artifacts require.

Each planned edit is verified before it is trusted: the post-removal
text must re-parse, and the resulting ``entities_referenced`` id-set
must equal (original ids − deleted ids) — or, when every entry on an
artifact is redundant, the key is removed entirely (the field is
optional after A1.3). A diff is also rendered so contributor review
sees exactly what changes.

DRY-RUN by default (report only, no writes). Pass ``--apply`` to write.

Safety note: A1.1 verified end-to-end that deleting EVERY
entities_referenced entry corpus-wide adds zero new
description_token_drift errors (ACTIVE gate risk = 0). This migration
therefore deletes purely on the substantive/redundant classification;
the threshold is the contributor's keep-dial, not a safety control.
Re-run validate.py + review-coverage.py after --apply as the regression
guard.

Usage:
  # 1. classify at the chosen threshold:
  audit-a1-vocab.py --all --substantive-threshold N
  # 2. preview the deletion (dry-run):
  migrate-a1-delete.py
  # 3. apply:
  migrate-a1-delete.py --apply
"""

import argparse
import difflib
import json
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
DEFAULT_AUDIT = Path("/tmp/a1-vocab-audit/audit.json")
DEFAULT_OUT = Path("/tmp/a1-delete-plan")

PRESERVE = "a-preserve"

_HEADER_RE = re.compile(r"^entities_referenced:[ \t]*$")
_TOP_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:")
_ENTRY_ID_RE = re.compile(r"^[ \t]*-?[ \t]*id:[ \t]*['\"]?([\w-]+)")


class SurgeryError(Exception):
    """A planned edit failed its self-check; the file is left untouched."""


def _find_block(lines):
    """Return (header_idx, entry_indent, block_end_idx) for the
    block-form ``entities_referenced:`` section, or None when the file
    has no block-form entries (inline ``[]`` or absent)."""
    header_idx = next(
        (i for i, l in enumerate(lines) if _HEADER_RE.match(l)), None)
    if header_idx is None:
        return None
    # First entry line after the header gives the entry indent.
    entry_indent = None
    i = header_idx + 1
    while i < len(lines):
        l = lines[i]
        if l.strip() == "" or l.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([ \t]*)-[ \t]", l)
        if m:
            entry_indent = m.group(1)
        break
    if entry_indent is None:
        return None  # header present but no list entries (e.g. ": []" handled by regex miss)
    # Block ends at the next top-level key (col-0) or EOF.
    block_end = len(lines)
    for j in range(header_idx + 1, len(lines)):
        if _TOP_KEY_RE.match(lines[j]):
            block_end = j
            break
    return header_idx, entry_indent, block_end


def _entry_spans(lines, entry_indent, start, end):
    """Yield (id, span_start, span_end) for each entry in [start, end).
    An entry begins at a line ``{entry_indent}- `` and runs to the next
    such line or to ``end``."""
    dash = re.compile(rf"^{re.escape(entry_indent)}-[ \t]")
    starts = [i for i in range(start, end) if dash.match(lines[i])]
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else end
        eid = None
        for i in range(s, e):
            m = _ENTRY_ID_RE.match(lines[i])
            if m:
                eid = m.group(1)
                break
        yield eid, s, e


def remove_entries(text, delete_ids, keep_ids):
    """Return new text with the entries whose id ∈ delete_ids spliced
    out. Raises SurgeryError if the result doesn't re-parse or the
    surviving id-set doesn't match keep_ids."""
    lines = text.splitlines(keepends=True)
    found = _find_block(lines)
    if found is None:
        raise SurgeryError("no block-form entities_referenced section found")
    header_idx, entry_indent, block_end = found

    spans = list(_entry_spans(lines, entry_indent, header_idx + 1, block_end))
    file_ids = [eid for eid, _, _ in spans]
    if any(eid is None for eid in file_ids):
        raise SurgeryError("an entry has no extractable id")
    survivors = [eid for eid in file_ids if eid not in delete_ids]

    if not survivors:
        # Every entry redundant → remove the key entirely (optional field).
        new_lines = lines[:header_idx] + lines[block_end:]
    else:
        drop = set()
        for eid, s, e in spans:
            if eid in delete_ids:
                drop.update(range(s, e))
        new_lines = [l for i, l in enumerate(lines) if i not in drop]

    new_text = "".join(new_lines)

    # --- self-check ---
    try:
        parsed = yaml.safe_load(new_text)
    except yaml.YAMLError as ex:
        raise SurgeryError(f"post-removal text does not parse: {ex}")
    got = parsed.get("entities_referenced") if isinstance(parsed, dict) else None
    got_ids = [e.get("id") for e in got] if isinstance(got, list) else []
    if not survivors:
        if got not in (None, []):
            raise SurgeryError(
                f"expected key removed/empty, got {len(got_ids)} entries")
    else:
        if got_ids != survivors:
            raise SurgeryError(
                f"surviving ids {got_ids} != expected {survivors}")
        if set(got_ids) != set(keep_ids):
            raise SurgeryError(
                f"surviving id-set {sorted(set(got_ids))} != "
                f"audit keep-set {sorted(set(keep_ids))}")
    return new_text


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", default=str(DEFAULT_AUDIT),
                    help=f"audit.json from audit-a1-vocab.py (default {DEFAULT_AUDIT})")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run, report only)")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"dry-run diff/report dir (default {DEFAULT_OUT})")
    args = ap.parse_args()

    audit_path = Path(args.audit)
    if not audit_path.exists():
        print(f"ERROR: audit not found: {audit_path}\n"
              f"Run: audit-a1-vocab.py --all --substantive-threshold N",
              file=sys.stderr)
        sys.exit(1)
    audit = json.loads(audit_path.read_text())
    threshold = audit.get("substantive_threshold")

    out_dir = Path(args.out)
    if not args.apply:
        out_dir.mkdir(parents=True, exist_ok=True)

    total_del = total_keep = files_changed = files_emptied = 0
    errors = []
    rows = []

    for art in audit["artifacts"]:
        slug = art["slug"]
        entries = art["entries"]
        delete_ids = {e["id"] for e in entries if e["bucket"] != PRESERVE}
        keep_ids = {e["id"] for e in entries if e["bucket"] == PRESERVE}
        if not delete_ids:
            total_keep += len(keep_ids)
            continue
        path = RESEARCH_DIR / f"{slug}.yaml"
        if not path.exists():
            errors.append(f"{slug}: artifact file missing")
            continue
        text = path.read_text()
        try:
            new_text = remove_entries(text, delete_ids, keep_ids)
        except SurgeryError as ex:
            errors.append(f"{slug}: {ex}")
            continue

        files_changed += 1
        total_del += len(delete_ids)
        total_keep += len(keep_ids)
        if not keep_ids:
            files_emptied += 1
        deleted_names = [e["name"] for e in entries if e["id"] in delete_ids]
        rows.append((slug, len(keep_ids), len(delete_ids), deleted_names))

        if args.apply:
            path.write_text(new_text)
        else:
            diff = "".join(difflib.unified_diff(
                text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{slug}.yaml", tofile=f"b/{slug}.yaml"))
            (out_dir / f"{slug}.diff").write_text(diff)

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print("=" * 64)
    print(f" A1.4 — entities_referenced redundant-entry deletion [{mode}]")
    print("=" * 64)
    print(f"\n  Audit threshold (substantive = keep): >= {threshold} "
          f"context_summary token(s) absent from body")
    print(f"  Artifacts changed:   {files_changed}")
    print(f"  Artifacts emptied (key removed): {files_emptied}")
    print(f"  Entries deleted:     {total_del}")
    print(f"  Entries kept:        {total_keep}")
    if errors:
        print(f"\n  !! {len(errors)} artifact(s) SKIPPED (surgery self-check failed):")
        for e in errors:
            print(f"     - {e}")
    if not args.apply:
        print(f"\n  Per-artifact diffs written to: {out_dir}/")
        print("  Review them, then re-run with --apply.")
    else:
        print("\n  Applied. Run validate.py + validate-research.py + "
              "review-coverage.py as the regression guard.")
    # Non-zero exit if any artifact failed its self-check.
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
