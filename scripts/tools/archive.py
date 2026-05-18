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
import random
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

# scripts/tools/archive.py — put the scripts/ parent on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Wayback-URL detection + manifest I/O share helpers with manifest.py
# via lib._common.
from lib._common import (  # noqa: E402
    MANIFEST_PATH,
    WAYBACK_URL_RE,
    load_manifest,
    load_topic,
    save_manifest,
    wayback_url_date,
)

CDX_API = "http://web.archive.org/cdx/search/cdx"
SAVE_API = "https://web.archive.org/save/"
WAYBACK_BASE = "https://web.archive.org/web/"

# CDX network-retry policy. Exponential backoff (2 → 4 sec) with up
# to 50% jitter on top — avoids hammering the IA endpoint when it's
# returning transient failures across multiple manifest entries in a
# single run.
_CDX_RETRIES = 3
_CDX_BACKOFF_BASE = 2.0

USER_AGENT = f"{load_topic()['display_name']}-Research-Archiver/2.0"


def check_wayback(url):
    """Query CDX for the most recent 200-status snapshot of `url`.

    Returns (date_or_None, state):
      state == "found"   → snapshot exists; date = "YYYY-MM-DD"
      state == "absent"  → CDX returned cleanly with 0 rows
      state == "unknown" → CDX errored or timed out after one retry
                           (caller must NOT treat this as absent — no SPN
                           submit, no bit-1 update; just skip for this run)
    """
    params = urllib.parse.urlencode({
        "url": url,
        "output": "json",
        "limit": "1",
        "sort": "reverse",
        "filter": "statuscode:200",
    })
    cdx_url = f"{CDX_API}?{params}"

    for attempt in range(_CDX_RETRIES):
        try:
            req = urllib.request.Request(cdx_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1:
                ts = data[1][1]
                return ts[:4] + "-" + ts[4:6] + "-" + ts[6:8], "found"
            return None, "absent"
        except (urllib.error.URLError, TimeoutError):
            if attempt < _CDX_RETRIES - 1:
                backoff = _CDX_BACKOFF_BASE * (2 ** attempt)
                time.sleep(backoff + random.uniform(0, backoff * 0.5))
                continue
            return None, "unknown"
        except (json.JSONDecodeError, IndexError):
            # Malformed CDX response — treat as unknown, not absent
            return None, "unknown"


def submit_wayback(url):
    """Submit ``url`` to SPN. Returns ``(ok, result)``:
      ok=True  → SPN redirected to a confirmed web.archive.org snapshot
                 URL; result is that URL (timestamp extractable via
                 ``wayback_url_date``).
      ok=False → SPN response did not redirect to web.archive.org (could
                 not confirm the snapshot was actually created), or a
                 network / HTTP error occurred; result carries the
                 diagnostic string. The next sweep's CDX check is the
                 authoritative re-query.
    """
    try:
        req = urllib.request.Request(
            f"{SAVE_API}{url}",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            final = resp.url if hasattr(resp, "url") else resp.geturl()
            if "web.archive.org" in final:
                return True, final
            return False, (
                f"SPN response did not redirect to web.archive.org "
                f"(got: {final}) — snapshot not confirmed; next CDX "
                f"sweep will re-check"
            )
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return False, str(e)


def cmd_submit_one(url):
    if wayback_url_date(url):
        print(f"Refusing: {url}")
        print("  URL is already a Wayback snapshot — submitting it would archive")
        print("  the Wayback viewer, not the original content.")
        sys.exit(1)
    print(f"Submitting: {url}")
    ok, result = submit_wayback(url)
    if not ok:
        print(f"  FAILED: {result}")
        sys.exit(1)
    print(f"  OK: {result}")

    # On a successful single-URL submit, update the manifest entry
    # the same way the no-args sweep does — without this, a contributor
    # running --submit URL after registering a new source would be
    # left with archive_status: 1 (local only) and no wayback_date.
    entries = load_manifest()
    entry = next((e for e in entries if e.get("url") == url), None)
    if entry is None:
        print(f"  WARNING: URL not in manifest — submission succeeded but no")
        print(f"  entry to update. Add via `manifest.py add` to track the")
        print(f"  Wayback record.")
        sys.exit(0)
    wb_date = wayback_url_date(result) or datetime.now().strftime("%Y-%m-%d")
    entry["wayback_date"] = wb_date
    entry["archive_status"] = entry.get("archive_status", 0) | 2
    save_manifest(entries)
    print(f"  Manifest updated: wayback_date={wb_date}, archive_status |= 2")
    sys.exit(0)


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

    found = submitted = errors = unknown = native = 0

    for i, e in enumerate(to_check):
        url = e["url"]
        short = url[:80] + "..." if len(url) > 80 else url
        print(f"  [{i+1}/{len(to_check)}] {short}")

        # Short-circuit: URL is itself a Wayback snapshot (dead source
        # whose only surviving copy is the capture). Don't CDX-query a
        # wayback URL — the timestamp IS the archival record.
        wb_date = wayback_url_date(url)
        if wb_date:
            e["wayback_date"] = wb_date
            e["archive_status"] = e.get("archive_status", 0) | 2
            native += 1
            print(f"           ARCHIVE-NATIVE (from URL timestamp {wb_date})")
            save_manifest(entries)
            if i < len(to_check) - 1:
                time.sleep(1)
            continue

        ts, state = check_wayback(url)
        if state == "found":
            e["wayback_date"] = ts
            e["archive_status"] = e.get("archive_status", 0) | 2
            found += 1
            print(f"           FOUND snapshot {ts}")
        elif state == "unknown":
            # CDX errored/timed out — do NOT submit to SPN, do NOT set bit 1.
            # Leave the entry as-is so a later run can re-query.
            unknown += 1
            print(f"           CDX UNKNOWN — skipping this run")
        else:  # state == "absent"
            print(f"           NOT IN WAYBACK")
            if not args.check_only:
                time.sleep(15)  # rate limit
                ok, result = submit_wayback(url)
                if ok:
                    e["wayback_date"] = (
                        wayback_url_date(result)
                        or datetime.now().strftime("%Y-%m-%d")
                    )
                    e["archive_status"] = e.get("archive_status", 0) | 2
                    submitted += 1
                    print(f"           SUBMITTED ({result})")
                else:
                    errors += 1
                    print(f"           FAILED: {result}")

        # Save incrementally so partial progress is preserved
        save_manifest(entries)

        if i < len(to_check) - 1:
            time.sleep(1)

    print("\n" + "=" * 64)
    print(f"  Found:          {found}")
    print(f"  Archive-native: {native}  (URL is already a Wayback snapshot)")
    print(f"  Submitted:      {submitted}")
    print(f"  Unknown:        {unknown}  (CDX errored; will retry next run)")
    print(f"  Errors:         {errors}")
    print("=" * 64)


if __name__ == "__main__":
    main()
