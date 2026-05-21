#!/usr/bin/env python3
"""Route a failing validator check to the role that owns its fix.

This is the dissolved Error agent: a pure lookup over the phase routing
map (`scripts/checks/_phases.py`), not a judgment role. Given the
`check_name`s a validator reported, it prints, for each:

    check_name -> phase -> owning role -> target: data

The orchestrator (the `/build` skill) runs this when a build or audit
fails, then re-enters the owning role to fix the **artifact data** and
rebuilds. The fix target is ALWAYS the artifact data, never the rendered
node body (the body is regenerated, and a node-body edit is hook-blocked).

Routing lives in `_phases.py` (the single source of truth), so this script
holds no table of its own — add or rename a phase/role there and this
output follows.

Usage:
    route_failure.py prose_drift verbatim_quotes
    route_failure.py --json coverage boundary

A check name absent from the map routes to `render` (the default), and is
flagged as unrecognized so a typo in the input is visible.
"""

import argparse
import json
import sys
from pathlib import Path

# scripts/tools/route_failure.py — put the scripts/ parent on sys.path so
# `checks` resolves as a package (same idiom as validate.py / check-vocab.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checks._phases import CHECK_PHASE, PHASE_ROLE, phase_of, role_of  # noqa: E402

# render-phase checks that read cross-layer / whole-repo state: a failure
# here is rebuilt by the builder, but may signal an upstream gap (a missing
# quote, an unarchived source) rather than a pure re-render.
_CROSS_LAYER = {
    "coverage", "boundary", "link_resolution",
    "finding_source_in_entity_node", "description_token_drift",
}


def route(check_names):
    rows = []
    for name in check_names:
        phase = phase_of(name)
        role = role_of(name)
        rows.append({
            "check": name,
            "phase": phase,
            "owning_role": role,                 # None for preflight
            "target": "data",                    # never the node body
            "recognized": name in CHECK_PHASE,
            "cross_layer": phase == "render" and name in _CROSS_LAYER,
        })
    return rows


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description="Route failing validator checks to the role that owns "
        "the artifact-data fix (dissolved Error agent; reads "
        "scripts/checks/_phases.py).",
    )
    ap.add_argument("check_names", nargs="+", metavar="CHECK_NAME",
                    help="the check name(s) a validator reported as failing")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    rows = route(args.check_names)

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print("Fix the artifact DATA, never the node body. Re-enter the owning "
          "role, then rebuild.\n")
    for r in rows:
        owner = r["owning_role"] or "(last writer — re-check whoever wrote the artifact)"
        print(f"  {r['check']}")
        print(f"      phase:  {r['phase']}")
        print(f"      role:   {owner}")
        print(f"      target: data")
        if not r["recognized"]:
            print(f"      note:   '{r['check']}' is not a known check name — "
                  f"verify the spelling (routed to its default phase)")
        if r["cross_layer"]:
            print("      note:   cross-layer check — may signal an upstream "
                  "extract/archive gap, not just a re-render")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
