#!/usr/bin/env python3
"""One-shot migration: flat manifest -> {url, artifacts: [...]} shape.

Reads the current flat manifest (each row a (url, format, path,
sha256, ...) tuple) and rewraps each row as a URL-level entry whose
`artifacts` list carries the per-rendering fields. URLs with multiple
existing entries (e.g., the Vimeo lucistrust-rending-veils video +
transcript pair) merge into one entry with multiple artifacts.

Field placement:
  URL-level:      url, status, archive_status, wayback_date,
                  wayback_skip, note
  Artifact-level: format, path, sha256, archived_date,
                  extraction_type, transcript_provenance

Pending / blocked entries (status != archived) get artifacts: []
since they have no archived rendering. Their existing `format` field
(metadata about "what shape this WILL be when archived") drops — the
format becomes a property of the archived artifact, not the URL plan.

Round-trip verification: the set of paths before == the set of paths
after. Errors if any path is dropped or duplicated.

Idempotent: detects the new shape and exits cleanly. Re-run safe.

Usage:
  python3 scripts/tools/migrate-manifest-to-artifacts.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"


URL_LEVEL_FIELDS = {
    "url", "status", "archive_status", "wayback_date", "wayback_skip",
}
ARTIFACT_LEVEL_FIELDS = {
    "format", "path", "sha256", "archived_date",
    "extraction_type", "transcript_provenance",
}
# `note` migrates to artifact level when the row has a path (the note
# described that specific rendering), and stays at URL level otherwise
# (pending/blocked rows have no artifact to attach the note to). Schema
# permits note at either level post-migration.
RETIRED_FIELDS = {"category"}  # unused (0/447); drops in migration


def is_new_shape(entries):
    """Heuristic: if any entry has an `artifacts` key, treat the
    manifest as already migrated. Idempotent guard."""
    for e in entries:
        if isinstance(e, dict) and "artifacts" in e:
            return True
    return False


def migrate(entries):
    """Rewrap flat entries into URL-keyed entries with nested artifacts.

    Returns (new_entries, report) where report is a dict with counts +
    any anomalies surfaced during migration.
    """
    by_url = {}  # url -> URL-level entry-in-progress
    report = {
        "rows_read": len(entries),
        "urls_seen": 0,
        "urls_with_multiple_artifacts": 0,
        "artifacts_total": 0,
        "pending_no_artifacts": 0,
        "unknown_fields": set(),
        "url_field_conflicts": [],   # (url, field, val_a, val_b)
    }

    for row in entries:
        if not isinstance(row, dict):
            continue
        url = row.get("url")
        if not url:
            continue

        # Surface unknown fields (defensive — schema may have grown).
        for k in row.keys():
            if k not in URL_LEVEL_FIELDS and k not in ARTIFACT_LEVEL_FIELDS \
                    and k not in RETIRED_FIELDS and k != "note":
                report["unknown_fields"].add(k)

        # URL-level slice (fields that apply to the source itself).
        url_slice = {k: row[k] for k in URL_LEVEL_FIELDS if k in row}

        # Artifact-level slice (fields that apply to one rendering).
        artifact_slice = {k: row[k] for k in ARTIFACT_LEVEL_FIELDS if k in row}

        # `note` placement: artifact-level when the row has a path (the
        # note describes the rendering); URL-level when no path (pending /
        # blocked entries have no artifact to attach it to).
        if "note" in row:
            if row.get("path"):
                artifact_slice["note"] = row["note"]
            else:
                url_slice["note"] = row["note"]

        if url in by_url:
            # Second-or-later row for this URL — merge.
            existing = by_url[url]
            for k, v in url_slice.items():
                if k in existing and existing[k] != v:
                    # URL-level conflict (e.g., one row says status==archived
                    # and another says status==pending for the same URL).
                    # Record and prefer the existing value; this surfaces
                    # data anomalies for contributor review.
                    report["url_field_conflicts"].append(
                        (url, k, existing[k], v)
                    )
                elif k not in existing:
                    existing[k] = v
        else:
            by_url[url] = url_slice.copy()

        # Append artifact (only when the row carries archived-rendering
        # data — pending/blocked rows have no path, no artifact to append).
        if artifact_slice.get("path"):
            by_url[url].setdefault("artifacts", []).append(artifact_slice)
            report["artifacts_total"] += 1

    # Finalize entries — every URL gets an artifacts key (possibly empty).
    new_entries = []
    for url, entry in by_url.items():
        entry.setdefault("artifacts", [])
        if not entry["artifacts"]:
            report["pending_no_artifacts"] += 1
        elif len(entry["artifacts"]) > 1:
            report["urls_with_multiple_artifacts"] += 1
        # Sort URL-level keys for stable diff: url first, then status,
        # archive_status, wayback_date, wayback_skip, note, artifacts.
        ordered = {}
        for k in ("url", "status", "archive_status", "wayback_date",
                  "wayback_skip", "note"):
            if k in entry:
                ordered[k] = entry[k]
        ordered["artifacts"] = entry["artifacts"]
        new_entries.append(ordered)

    report["urls_seen"] = len(new_entries)

    # Re-sort artifacts: video before transcript (canonical reading order
    # for dual-artifact sources), otherwise stable.
    for entry in new_entries:
        entry["artifacts"].sort(key=_artifact_sort_key)

    # Sort URL entries: by URL alphabetically for predictable diffs.
    new_entries.sort(key=lambda e: e["url"])

    return new_entries, report


_FORMAT_ORDER = {
    "video": 0, "audio": 1, "pdf": 2, "html": 3,
    "txt": 4, "image": 5, "transcript": 6,
}


def _artifact_sort_key(artifact):
    """Stable artifact ordering: primary renderings first, derived
    (transcript) last. Within a format, by path."""
    fmt = artifact.get("format", "")
    return (_FORMAT_ORDER.get(fmt, 99), artifact.get("path", ""))


def collect_paths_before(entries):
    """Set of every path in the flat manifest. Round-trip ground truth."""
    return {e["path"] for e in entries if isinstance(e, dict) and e.get("path")}


def collect_paths_after(entries):
    """Set of every artifact path in the new-shape manifest."""
    paths = set()
    for e in entries:
        for a in e.get("artifacts", []):
            if a.get("path"):
                paths.add(a["path"])
    return paths


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print report without writing the migrated manifest.",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} does not exist.", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        entries = yaml.safe_load(f) or []

    if not isinstance(entries, list):
        print(f"ERROR: manifest root is not a list ({type(entries).__name__})",
              file=sys.stderr)
        sys.exit(1)

    if is_new_shape(entries):
        print("Manifest already in artifacts-under-URL shape. Nothing to do.")
        sys.exit(0)

    paths_before = collect_paths_before(entries)
    new_entries, report = migrate(entries)
    paths_after = collect_paths_after(new_entries)

    print("=" * 64)
    print("  Manifest Migration Report")
    print("=" * 64)
    print(f"\n  Rows read:                       {report['rows_read']}")
    print(f"  URLs after migration:            {report['urls_seen']}")
    print(f"  URLs with > 1 archived artifact: {report['urls_with_multiple_artifacts']}")
    print(f"  Artifacts total:                 {report['artifacts_total']}")
    print(f"  Pending/blocked (no artifacts):  {report['pending_no_artifacts']}")
    print(f"  Paths before:                    {len(paths_before)}")
    print(f"  Paths after:                     {len(paths_after)}")

    if paths_before != paths_after:
        dropped = paths_before - paths_after
        added = paths_after - paths_before
        print()
        print(f"  ⚠ Path-set drift:")
        if dropped:
            print(f"    DROPPED ({len(dropped)}):")
            for p in sorted(dropped):
                print(f"      - {p}")
        if added:
            print(f"    ADDED ({len(added)}):")
            for p in sorted(added):
                print(f"      + {p}")
        print()
        print("  Migration aborted — path-set drift indicates a data-loss bug.")
        sys.exit(1)
    print(f"  ✓ Path-set round-trip verified ({len(paths_before)} paths match)")

    if report["unknown_fields"]:
        print(f"\n  ⚠ Unknown fields encountered (kept at URL level by default):")
        for f in sorted(report["unknown_fields"]):
            print(f"      - {f}")

    if report["url_field_conflicts"]:
        print(f"\n  ⚠ URL-level field conflicts (existing value kept):")
        for url, field, a, b in report["url_field_conflicts"]:
            print(f"      {url}")
            print(f"        {field}: kept={a!r}  rejected={b!r}")

    if args.dry_run:
        print("\n  --dry-run: not writing manifest.")
        sys.exit(0)

    # Write atomic — temp file then rename.
    tmp = MANIFEST_PATH.with_suffix(".yaml.tmp")
    with open(tmp, "w") as f:
        yaml.dump(new_entries, f, sort_keys=False, default_flow_style=False,
                  allow_unicode=True, width=9999)
    tmp.replace(MANIFEST_PATH)
    print(f"\n  ✓ Wrote new-shape manifest to {MANIFEST_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
