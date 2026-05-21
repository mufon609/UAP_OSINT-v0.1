#!/usr/bin/env python3
"""Parity gate: phase tokens in the docs/toolkit match _phases.py.

The phase routing map (`scripts/checks/_phases.py`) is the single source
of truth for the `--phase` vocabulary. The prompts and the `.claude/`
toolkit reference phase tokens in prose (`--phase extract`, ...). This gate
keeps those references from drifting:

  1. Every `--phase <token>` referenced under prompts/ and .claude/ is a
     value the flag actually accepts (a member of PHASE_CHOICES). Catches a
     typo (`--phase extarct`) or a reference to a phase that was renamed or
     removed in _phases.py.
  2. Every canonical phase (PHASES) is documented at least once in
     prompts/topology.md — so a phase newly added to _phases.py cannot ship
     undocumented.

Modeled on build-md-spec.py: prints detail unless --quiet; exits non-zero
on any mismatch (wired into pre-commit.sh).
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checks._phases import PHASE_CHOICES, PHASES  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# `--phase <token>` with a lowercase token (concrete phase names are all
# lowercase; placeholders are uppercase `X` or braced `{a,b}`/`<phase>`, so
# they're skipped by the character class).
_PHASE_REF = re.compile(r"--phase[= ]+([a-z][a-z-]*)")

# Where phase tokens are referenced in prose.
_SCAN_DIRS = ("prompts", ".claude")
_TOPOLOGY = REPO_ROOT / "prompts" / "topology.md"


def _iter_files():
    for d in _SCAN_DIRS:
        base = REPO_ROOT / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix in (".md", ".json"):
                yield p


def check():
    errors = []

    # 1. every referenced --phase token is valid
    for path in _iter_files():
        rel = path.relative_to(REPO_ROOT)
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for tok in _PHASE_REF.findall(line):
                if tok not in PHASE_CHOICES:
                    errors.append(
                        f"{rel}:{n}: --phase '{tok}' is not a valid phase "
                        f"(accepted: {', '.join(PHASE_CHOICES)})"
                    )

    # 2. every canonical phase is documented in topology.md
    if _TOPOLOGY.is_file():
        topo = _TOPOLOGY.read_text(encoding="utf-8")
        for phase in PHASES:
            if not re.search(rf"\b{re.escape(phase)}\b", topo):
                errors.append(
                    f"prompts/topology.md: canonical phase '{phase}' "
                    f"(from _phases.PHASES) is not documented"
                )
    else:
        errors.append("prompts/topology.md missing — cannot verify phase documentation")

    return errors


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--quiet", action="store_true",
                    help="exit code only; suppress detail")
    args = ap.parse_args()

    errors = check()

    if errors:
        if not args.quiet:
            print("phase-routing parity FAILED:\n")
            for e in errors:
                print(f"  ✗ {e}")
        else:
            print(f"phase-routing parity: {len(errors)} mismatch(es)")
        return 1

    if not args.quiet:
        print("phase-routing parity OK — all --phase references valid; "
              "all canonical phases documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
