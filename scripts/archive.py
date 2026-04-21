#!/usr/bin/env python3
"""
Submit manifest URLs to the Internet Archive Wayback Machine.

Reads sources/manifest.yaml. For each entry:
  - Skip if `wayback_skip: true` (structurally unarchivable URL)
  - Skip if `archive_status & 2` (bit 1 already set — Wayback confirmed)
  - Otherwise: query CDX, submit via Save Page Now if absent, and on
    success record `wayback_date` AND OR bit 1 into `archive_status`
    (so the next run skips it — no retry storms on confirmed entries)

`--recheck-all` forces CDX re-query on all entries (still respects
`wayback_skip` — those URLs cannot be archived, recheck is pointless).

Usage:
  archive.py                     # check + submit missing
  archive.py --check-only        # check only; don't submit
  archive.py --submit URL        # submit a single URL
  archive.py --recheck-all       # force recheck of confirmed entries
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"

CDX_API = "http://web.archive.org/cdx/search/cdx"
SAVE_API = "https://web.archive.org/save/"
WAYBACK_BASE = "https://web.archive.org/web/"

USER_AGENT = "UAP-Research-Archiver/2.0"


def load_manifest():
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f) or []


def save_manifest(entries):
    entries.sort(key=lambda e: e.get("url", ""))
    with open(MANIFEST_PATH, "w") as f:
        yaml.dump(entries, f, sort_keys=False, default_flow_style=False,
                  allow_unicode=True, width=9999)


def check_wayback(url):
    params = urllib.parse.urlencode({
        "url": url,
        "output": "json",
        "limit": "1",
        "sort": "reverse",
        "filter": "statuscode:200",
    })
    try:
        req = urllib.request.Request(
            f"{CDX_API}?{params}",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1:
                ts = data[1][1]
                return ts[:4] + "-" + ts[4:6] + "-" + ts[6:8]
    except (urllib.error.URLError, json.JSONDecodeError, IndexError, TimeoutError):
        pass
    return None


def submit_wayback(url):
    try:
        req = urllib.request.Request(
            f"{SAVE_API}{url}",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            final = resp.url if hasattr(resp, "url") else resp.geturl()
            if "web.archive.org" in final:
                return True, final
            return True, f"Submitted — check {WAYBACK_BASE}*/{url}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return False, str(e)


def cmd_submit_one(url):
    print(f"Submitting: {url}")
    ok, result = submit_wayback(url)
    if ok:
        print(f"  OK: {result}")
    else:
        print(f"  FAILED: {result}")
    sys.exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--submit", metavar="URL", help="Submit a single URL")
    parser.add_argument("--recheck-all", action="store_true")
    args = parser.parse_args()

    if args.submit:
        cmd_submit_one(args.submit)
        return

    entries = load_manifest()
    if not entries:
        print("No entries in manifest.")
        return

    to_check = []
    skipped_unarchivable = 0
    skipped_confirmed = 0
    for e in entries:
        if e.get("wayback_skip"):
            skipped_unarchivable += 1
            continue
        if not args.recheck_all and (e.get("archive_status", 0) & 2):
            skipped_confirmed += 1
            continue
        to_check.append(e)

    print("=" * 64)
    print("  Wayback Machine Archival")
    print("=" * 64)
    print(f"\n  Total entries:        {len(entries)}")
    print(f"  Already confirmed:    {skipped_confirmed}")
    print(f"  Unarchivable (skip):  {skipped_unarchivable}")
    print(f"  To check:             {len(to_check)}")
    print(f"  Mode:                 {'check only' if args.check_only else 'check + submit'}\n")

    found = submitted = errors = 0

    for i, e in enumerate(to_check):
        url = e["url"]
        short = url[:80] + "..." if len(url) > 80 else url
        print(f"  [{i+1}/{len(to_check)}] {short}")

        ts = check_wayback(url)
        if ts:
            e["wayback_date"] = ts
            e["archive_status"] = e.get("archive_status", 0) | 2
            found += 1
            print(f"           FOUND snapshot {ts}")
        else:
            print(f"           NOT IN WAYBACK")
            if not args.check_only:
                time.sleep(15)  # rate limit
                ok, result = submit_wayback(url)
                if ok:
                    e["wayback_date"] = datetime.now().strftime("%Y-%m-%d")
                    e["archive_status"] = e.get("archive_status", 0) | 2
                    submitted += 1
                    print(f"           SUBMITTED")
                else:
                    errors += 1
                    print(f"           FAILED: {result}")

        # Save incrementally so partial progress is preserved
        save_manifest(entries)

        if i < len(to_check) - 1:
            time.sleep(1)

    print("\n" + "=" * 64)
    print(f"  Found:     {found}")
    print(f"  Submitted: {submitted}")
    print(f"  Errors:    {errors}")
    print("=" * 64)


if __name__ == "__main__":
    main()
