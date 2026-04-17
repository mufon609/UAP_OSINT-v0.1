#!/usr/bin/env python3
"""
Manage sources/manifest.yaml — the source-archival index.

Commands:
  manifest.py add URL --path PATH [--format FMT] [--note TEXT]
  manifest.py status URL               # show entry for URL
  manifest.py pending                  # list entries needing archival
  manifest.py usage URL                # list nodes citing URL
  manifest.py orphans                  # manifest entries no node cites
  manifest.py missing                  # URLs cited in nodes not in manifest
  manifest.py summary                  # counts by status and format
  manifest.py verify-paths             # check every archived path exists on disk
"""

import argparse
import hashlib
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

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"
SOURCES_DIR = REPO_ROOT / "sources"

CONTENT_DIRS = [
    "people", "organizations", "documents", "events",
    "transcripts", "news", "books", "locations", "findings",
]

URL_PATTERN = re.compile(r"https?://[^\s\|\)>`\]]+")

FORMAT_BY_EXT = {
    ".pdf": "pdf",
    ".html": "html",
    ".htm": "html",
    ".txt": "txt",
    ".md": "transcript",
    ".json": "json",
}


def load_manifest():
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    return data or []


def save_manifest(entries):
    entries.sort(key=lambda e: e.get("url", ""))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        yaml.dump(entries, f, sort_keys=False, default_flow_style=False,
                  allow_unicode=True, width=9999)


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


def format_from_path(path):
    if not path:
        return None
    return FORMAT_BY_EXT.get(Path(path).suffix.lower(), "html")


def compute_sha256(file_path):
    """Compute SHA256 of a file. Returns hex digest, or None on read error."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def cmd_add(args):
    entries = load_manifest()
    if any(e["url"] == args.url for e in entries):
        print(f"Already in manifest: {args.url}")
        return
    entry = {
        "url": args.url,
        "format": args.format or format_from_path(args.path) or "html",
        "status": "archived" if args.path else "pending",
    }
    if args.path:
        entry["path"] = args.path
        entry["archived_date"] = date.today().isoformat()
        # Compute sha256 of archived file — integrity backstop per schema.yaml
        full_path = SOURCES_DIR / args.path
        if full_path.exists():
            sha = compute_sha256(full_path)
            if sha:
                entry["sha256"] = sha
            else:
                print(f"WARNING: Could not compute sha256 for {full_path}", file=sys.stderr)
        else:
            print(f"WARNING: path does not exist (archival incomplete): sources/{args.path}", file=sys.stderr)
    if args.note:
        entry["note"] = args.note
    entries.append(entry)
    save_manifest(entries)
    print(f"✓ Added: {args.url}")
    if entry.get("sha256"):
        print(f"  sha256: {entry['sha256']}")


def cmd_status(args):
    entries = load_manifest()
    entry = next((e for e in entries if e["url"] == args.url), None)
    if not entry:
        print(f"Not in manifest: {args.url}")
        sys.exit(1)
    print(yaml.dump(entry, sort_keys=False, default_flow_style=False, allow_unicode=True))


def cmd_pending(args):
    entries = load_manifest()
    pending = [e for e in entries if e.get("status") != "archived"]
    for e in pending:
        status = e.get("status", "?")
        print(f"{status:15}  {e['url']}")
    print(f"\n{len(pending)} pending of {len(entries)} total")


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
    by_format = Counter(e.get("format", "?") for e in entries)
    print(f"Total entries: {len(entries)}")
    print("\nBy status:")
    for s, n in by_status.most_common():
        print(f"  {s:25} {n}")
    print("\nBy format:")
    for f, n in by_format.most_common():
        print(f"  {f:25} {n}")


def cmd_verify_paths(args):
    entries = load_manifest()
    missing = []
    for e in entries:
        path = e.get("path")
        if path and e.get("status") == "archived":
            full = SOURCES_DIR / path
            if not full.exists():
                missing.append((e["url"], path))
    for url, path in missing:
        print(f"  MISSING  sources/{path}")
        print(f"           (for {url})")
    print(f"\n{len(missing)} archived entries with missing local files")
    sys.exit(1 if missing else 0)


def cmd_verify_checksums(args):
    """Re-compute sha256 for every archived entry; compare against stored value.
    Flags silent file corruption, substitution, or overwrite.
    """
    entries = load_manifest()
    missing_sha = []   # entries that lack a sha256 but should have one
    mismatches = []    # entries where recomputed sha differs from stored
    missing_files = [] # entries where the file doesn't exist
    backfilled = 0     # entries where we populated a missing sha256 during this run

    for e in entries:
        if e.get("status") != "archived":
            continue
        path = e.get("path")
        if not path:
            continue
        full = SOURCES_DIR / path
        if not full.exists():
            missing_files.append((e["url"], path))
            continue
        current = compute_sha256(full)
        stored = e.get("sha256")
        if stored is None:
            # Backfill — legitimate one-time per entry when the field is being adopted
            e["sha256"] = current
            backfilled += 1
        elif stored != current:
            mismatches.append((e["url"], path, stored[:12], current[:12]))

    if backfilled:
        save_manifest(entries)
        print(f"Backfilled sha256 for {backfilled} entries without a prior checksum.")
        print("(Future runs will verify these; manual re-archive if any of these "
              "files was already corrupt at backfill time.)\n")

    if missing_files:
        print(f"\n{len(missing_files)} archived entries have missing local files:")
        for url, path in missing_files:
            print(f"  MISSING  sources/{path}")

    if mismatches:
        print(f"\n{len(mismatches)} CHECKSUM MISMATCHES (possible corruption or substitution):")
        for url, path, stored, current in mismatches:
            print(f"  MISMATCH  sources/{path}")
            print(f"            stored  : {stored}...")
            print(f"            current : {current}...")
            print(f"            url     : {url}")

    if not missing_files and not mismatches:
        print(f"✓ All {len([e for e in entries if e.get('status') == 'archived'])} archived files verified.")

    sys.exit(1 if (missing_files or mismatches) else 0)


COMMANDS = {
    "add": cmd_add,
    "status": cmd_status,
    "pending": cmd_pending,
    "usage": cmd_usage,
    "orphans": cmd_orphans,
    "missing": cmd_missing,
    "summary": cmd_summary,
    "verify-paths": cmd_verify_paths,
    "verify-checksums": cmd_verify_checksums,
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

    p = subparsers.add_parser("status")
    p.add_argument("url")

    subparsers.add_parser("pending")

    p = subparsers.add_parser("usage")
    p.add_argument("url")

    subparsers.add_parser("orphans")
    subparsers.add_parser("missing")
    subparsers.add_parser("summary")
    subparsers.add_parser("verify-paths")
    subparsers.add_parser("verify-checksums")

    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
