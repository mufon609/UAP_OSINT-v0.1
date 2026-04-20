#!/usr/bin/env python3
"""
Audit-schedule tracker.

Scans /research/*.yaml for claims, quotes, entities, and research gaps
whose `last_audited_date + audit_cadence_days` is past today's date.
Lists overdue entries sorted by how long they've been overdue.

Operational but dormant until research artifacts exist with populated
`last_audited_date` fields. When no scannable data exists, it reports
the absence of the research layer rather than erroring.

Audit-cadence enforcement plumbing (wiring `--overdue` into a
pre-commit / CI hook so stale artifacts block commits past the grace
period) is tracked under Step E of the refactor roadmap.

Usage:
  audit-schedule.py               # list overdue entries
  audit-schedule.py --overdue     # exit 1 if any overdue past grace period
  audit-schedule.py --summary     # counts by status / cadence
"""

import argparse
import sys
from pathlib import Path
from datetime import date

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = REPO_ROOT / "research"

GRACE_PERIOD_DAYS = 30
ENTRY_CATEGORIES = ["claims", "quotes", "entities_referenced", "research_gaps"]


def load_research_artifacts():
    """Return list of (path, parsed_yaml) for every research artifact."""
    if not RESEARCH_DIR.is_dir():
        return []
    artifacts = []
    for f in sorted(RESEARCH_DIR.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh)
            if data:
                artifacts.append((f, data))
        except yaml.YAMLError as e:
            print(f"WARNING: could not parse {f}: {e}", file=sys.stderr)
    return artifacts


def days_since(date_str):
    """Days between a YYYY-MM-DD string and today. None if malformed."""
    try:
        d = date.fromisoformat(str(date_str))
    except (ValueError, TypeError):
        return None
    return (date.today() - d).days


def collect_overdue(artifacts):
    """Return list of (artifact_path, category, entry_id, days_overdue, entry)."""
    overdue = []
    for path, data in artifacts:
        for category in ENTRY_CATEGORIES:
            entries = data.get(category, []) or []
            for entry in entries:
                cadence = entry.get("audit_cadence_days")
                last_audit = entry.get("last_audited_date")
                if not cadence or not last_audit:
                    continue
                since = days_since(last_audit)
                if since is None:
                    continue
                days_overdue = since - cadence
                if days_overdue > 0:
                    overdue.append((path, category, entry.get("id", "?"), days_overdue, entry))
    # Sort most-overdue first
    overdue.sort(key=lambda x: x[3], reverse=True)
    return overdue


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--overdue", action="store_true",
                        help="Exit 1 if any entry is past its audit cadence by more than grace period")
    parser.add_argument("--summary", action="store_true",
                        help="Print aggregate counts instead of the overdue list")
    args = parser.parse_args()

    artifacts = load_research_artifacts()

    if not artifacts:
        if not RESEARCH_DIR.is_dir():
            print(f"No research/ directory yet ({RESEARCH_DIR}).")
            print("Research artifacts are produced by Phase I of the layered build")
            print("process and live at /research/*.yaml. Audit-schedule tracking")
            print("becomes operational once artifacts exist.")
            return 0
        print("No research artifacts found.")
        return 0

    overdue = collect_overdue(artifacts)

    if args.summary:
        print(f"Research artifacts scanned: {len(artifacts)}")
        by_cat = {}
        total_auditable = 0
        for _, data in artifacts:
            for category in ENTRY_CATEGORIES:
                entries = data.get(category, []) or []
                count = sum(1 for e in entries if e.get("audit_cadence_days"))
                by_cat[category] = by_cat.get(category, 0) + count
                total_auditable += count
        print(f"Total auditable entries:   {total_auditable}")
        print(f"Overdue entries:           {len(overdue)}")
        print("\nBy category:")
        for cat, n in by_cat.items():
            print(f"  {cat:25} {n}")
        return 0

    if not overdue:
        print(f"✓ No overdue entries across {len(artifacts)} research artifact(s).")
        return 0

    print(f"{'OVERDUE':>9}  {'ARTIFACT':<40}  {'CATEGORY':<22}  ID")
    print("-" * 90)
    for path, category, entry_id, days_overdue, _ in overdue:
        print(f"{days_overdue:>6}d    {path.name:<40}  {category:<22}  {entry_id}")

    if args.overdue:
        past_grace = [o for o in overdue if o[3] > GRACE_PERIOD_DAYS]
        if past_grace:
            print(f"\n{len(past_grace)} entries past {GRACE_PERIOD_DAYS}-day grace period.")
            return 1
        print(f"\nAll overdue entries within {GRACE_PERIOD_DAYS}-day grace period.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
