#!/usr/bin/env python3
"""
Manage sources/manifest.yaml — the source-archival index.

Manifest shape: each entry is one URL with zero or more archived
artifacts (renderings). URL-level fields (status, archive_status,
wayback_date, wayback_skip, note) describe the source; artifact-level
fields (format, path, archived_date, extraction_type,
transcript_provenance, note) describe each rendering. See
meta/schema.yaml manifest_entry / artifact_entry for the canonical
spec.

Commands:
  manifest.py add URL --path PATH [--format FMT] [--note TEXT]
  manifest.py status URL               # show URL entry with all artifacts
  manifest.py pending                  # list URLs needing archival
  manifest.py usage URL                # list nodes citing URL
  manifest.py orphans                  # manifest entries no node cites
  manifest.py missing                  # URLs cited in nodes not in manifest
  manifest.py summary                  # counts by status / format
  manifest.py verify-paths             # check every artifact path exists
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# scripts/tools/manifest.py — put the scripts/ parent on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Wayback-URL detection + manifest I/O share helpers with archive.py
# via lib._common.
from lib._common import (  # noqa: E402
    MANIFEST_PATH,
    REPO_ROOT,
    SOURCES_DIR,
    WAYBACK_URL_RE,
    content_dirs,
    format_from_path,
    is_gitignored,
    iter_artifacts,
    load_manifest,
    normalize_source_rel_path,
    save_manifest,
    wayback_url_date,
)

CONTENT_DIRS = content_dirs()

URL_PATTERN = re.compile(r"https?://[^\s\|\)>`\]]+")


def scan_urls_in_nodes():
    usage = defaultdict(set)
    for d in CONTENT_DIRS:
        cd = REPO_ROOT / d
        if not cd.is_dir():
            continue
        for node in cd.glob("*.md"):
            text = node.read_text()
            for url in URL_PATTERN.findall(text):
                url = url.rstrip(";,.)]*")
                usage[url].add(str(node.relative_to(REPO_ROOT)))
    return usage


def _find_entry(entries, url):
    """Return the entry dict for a URL, or None."""
    return next((e for e in entries if e.get("url") == url), None)


def _refresh_archive_status(entry):
    """Recompute archive_status bits for a URL entry. Bit 0 = locally
    archived (status==archived AND at least one artifact); bit 1 =
    Wayback present (wayback_date set)."""
    has_local = (
        entry.get("status") == "archived"
        and bool(entry.get("artifacts"))
    )
    has_wayback = bool(entry.get("wayback_date"))
    entry["archive_status"] = (1 if has_local else 0) | (2 if has_wayback else 0)


def cmd_add(args):
    """Register URL + path + format. Three cases:

    - URL not in manifest: create a new entry with the artifact.
    - URL exists, path is new to this URL: append a new artifact.
    - URL exists, path matches an existing artifact for this URL:
      idempotent no-op (logs which artifact matched).

    Errors loudly if the supplied path is already registered under a
    DIFFERENT URL (path uniqueness across the manifest).
    """
    entries = load_manifest()
    path = normalize_source_rel_path(args.path) if args.path else None

    # Path uniqueness check: a given file path must belong to exactly
    # one URL. (Same file can't be a rendering of two different URLs.)
    if path:
        for e in entries:
            if e.get("url") == args.url:
                continue
            for a in e.get("artifacts") or []:
                if a.get("path") == path:
                    print(
                        f"ERROR: sources/{path} is already registered under a "
                        f"different URL: {e['url']}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

    entry = _find_entry(entries, args.url)

    if entry is None:
        # Brand-new URL entry.
        entry = {
            "url": args.url,
            "status": "archived" if path else "pending",
        }
        wb_date = wayback_url_date(args.url)
        if wb_date:
            entry["wayback_date"] = wb_date
        if args.wayback_skip:
            entry["wayback_skip"] = True
        if args.note and not path:
            # URL-level note only when no artifact accompanies (pending /
            # blocked entries). When a path is supplied, the note attaches
            # to the artifact below.
            entry["note"] = args.note
        entry["artifacts"] = []
        # Insert at the URL-sorted position so the write touches only this new
        # entry. save_manifest no longer globally re-sorts (that churned
        # unrelated entries on every write); a sorted manifest stays sorted,
        # and a drifted one still gets a clean single-entry diff.
        pos = next((i for i, e in enumerate(entries)
                    if e.get("url", "") > args.url), len(entries))
        entries.insert(pos, entry)
        created_url_entry = True
    else:
        created_url_entry = False

    appended_artifact = None
    if path:
        artifacts = entry.setdefault("artifacts", [])
        existing = next((a for a in artifacts if a.get("path") == path), None)
        if existing:
            print(f"Already in manifest: {args.url}")
            print(f"  artifact path: sources/{path}  format: {existing.get('format')!r}")
            return
        artifact = {
            "format": args.format or format_from_path(path) or "html",
            "path": path,
            "archived_date": date.today().isoformat(),
        }
        full_path = SOURCES_DIR / path
        if not full_path.exists():
            print(f"WARNING: path does not exist (archival incomplete): "
                  f"sources/{path}", file=sys.stderr)
        if args.extraction_type:
            artifact["extraction_type"] = args.extraction_type
        if args.transcript_provenance:
            artifact["transcript_provenance"] = args.transcript_provenance
        if args.note:
            artifact["note"] = args.note
        artifacts.append(artifact)
        appended_artifact = artifact
        # If the URL was previously pending (no artifacts) and we just
        # archived an artifact, promote status to archived.
        if entry.get("status") != "archived":
            entry["status"] = "archived"

    _refresh_archive_status(entry)

    if getattr(args, "dry_run", False):
        verb = "add new URL entry" if created_url_entry else "append to existing URL"
        print(f"[dry-run] would {verb}: {args.url}")
        if appended_artifact:
            print(f"[dry-run]   artifact: sources/{path}  "
                  f"format: {appended_artifact['format']!r}")
        print("[dry-run] validation OK (URL / path / format / path-uniqueness); "
              "manifest not written")
        return

    save_manifest(entries)

    if created_url_entry and appended_artifact:
        print(f"✓ Added: {args.url}")
        print(f"  artifact: sources/{path}  format: {appended_artifact['format']!r}")
    elif created_url_entry:
        print(f"✓ Added (no artifact): {args.url}")
    elif appended_artifact:
        print(f"✓ Appended artifact to existing URL: {args.url}")
        print(f"  artifact: sources/{path}  format: {appended_artifact['format']!r}")
    print(f"  archive_status: {entry['archive_status']}")
    if entry.get("wayback_date"):
        print(f"  wayback_date:   {entry['wayback_date']}")


def cmd_status(args):
    entries = load_manifest()
    entry = _find_entry(entries, args.url)
    if not entry:
        print(f"Not in manifest: {args.url}")
        sys.exit(1)
    print(yaml.dump(entry, sort_keys=False, default_flow_style=False,
                    allow_unicode=True))


def cmd_pending(args):
    entries = load_manifest()
    pending = [e for e in entries if e.get("status") != "archived"]
    for e in pending:
        status = e.get("status", "?")
        print(f"{status:15}  {e['url']}")
    print(f"\n{len(pending)} pending of {len(entries)} total URLs")


def cmd_usage(args):
    usage = scan_urls_in_nodes()
    citers = usage.get(args.url, set())
    if not citers:
        print(f"No node cites: {args.url}")
        return
    for n in sorted(citers):
        print(f"  {n}")
    print(f"\n{len(citers)} citing node(s)")


def cmd_orphans(args):
    entries = load_manifest()
    usage = scan_urls_in_nodes()
    orphans = [e for e in entries if e["url"] not in usage]
    for e in orphans:
        print(f"  {e['url']}")
    print(f"\n{len(orphans)} manifest entries not cited by any node")


def cmd_missing(args):
    entries = load_manifest()
    manifest_urls = {e["url"] for e in entries}
    usage = scan_urls_in_nodes()
    missing = {u: src for u, src in usage.items() if u not in manifest_urls}
    for url in sorted(missing.keys()):
        print(f"\n  {url}")
        for s in sorted(missing[url]):
            print(f"    <- {s}")
    print(f"\n{len(missing)} URLs cited in nodes not in manifest")


def cmd_summary(args):
    entries = load_manifest()
    by_status = Counter(e.get("status", "?") for e in entries)
    by_format = Counter(a.get("format", "?") for _, a in iter_artifacts(entries))
    n_artifacts = sum(1 for _ in iter_artifacts(entries))
    print(f"Total URLs:      {len(entries)}")
    print(f"Total artifacts: {n_artifacts}")
    print("\nBy URL status:")
    for s, n in by_status.most_common():
        print(f"  {s:25} {n}")
    print("\nBy artifact format:")
    for f, n in by_format.most_common():
        print(f"  {f:25} {n}")


def cmd_verify_paths(args):
    """Confirm every archived artifact's file exists on disk. A missing
    git-TRACKED file is real breakage (exit 1); a missing git-IGNORED file
    (the large sources/video/ media kept out of the remote) is
    expected-absent on a fresh clone — reported, but not a failure."""
    entries = load_manifest()
    missing = []           # git-tracked, absent — real breakage
    expected_absent = []   # git-ignored media, absent — expected on a clone
    for entry, artifact in iter_artifacts(entries):
        path = artifact.get("path")
        if not path or (SOURCES_DIR / path).exists():
            continue
        bucket = expected_absent if is_gitignored(f"sources/{path}") else missing
        bucket.append((entry["url"], path))
    for url, path in missing:
        print(f"  MISSING  sources/{path}")
        print(f"           (for {url})")
    if expected_absent:
        print(f"\n{len(expected_absent)} git-ignored media absent locally "
              f"(expected on a fresh clone; recover via source URL / Wayback)")
    print(f"\n{len(missing)} git-tracked artifacts with missing local files")
    sys.exit(1 if missing else 0)


COMMANDS = {
    "add": cmd_add,
    "status": cmd_status,
    "pending": cmd_pending,
    "usage": cmd_usage,
    "orphans": cmd_orphans,
    "missing": cmd_missing,
    "summary": cmd_summary,
    "verify-paths": cmd_verify_paths,
}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("add")
    p.add_argument("url")
    p.add_argument("--path")
    p.add_argument("--format")
    p.add_argument("--note")
    p.add_argument(
        "--extraction-type",
        choices=["text-native", "ocr-scan", "extraction-lossy"],
        help="How the source's text is extracted "
             "(default: text-native; field omitted from entry when default)")
    p.add_argument(
        "--transcript-provenance",
        choices=["stenographic", "published-transcript",
                 "human-corrected-caption", "auto-caption", "unknown"],
        help="How a format=transcript source's text was produced "
             "(default: unknown; field omitted from entry when unset). "
             "See schema.yaml artifact_entry.transcript_provenance_values "
             "for the per-value semantics.")
    p.add_argument(
        "--wayback-skip",
        action="store_true",
        help="Mark the URL entry as ineligible for Wayback submission "
             "(synthetic deep-link URLs that won't resolve at archive time)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the add (URL / path / format / path-uniqueness) and "
             "report what would change, without writing the manifest. Lets the "
             "External Investigator self-check a lead before the Archive agent "
             "commits it.")

    p = subparsers.add_parser("status")
    p.add_argument("url")

    subparsers.add_parser("pending")

    p = subparsers.add_parser("usage")
    p.add_argument("url")

    subparsers.add_parser("orphans")
    subparsers.add_parser("missing")
    subparsers.add_parser("summary")
    subparsers.add_parser("verify-paths")

    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
