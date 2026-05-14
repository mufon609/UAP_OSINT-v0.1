#!/usr/bin/env bash
# Help-invocation smoke test for contributor-facing scripts.
#
# For every Python script under scripts/build/ and scripts/tools/ (the
# two contributor-facing tiers), invoke `--help` and confirm:
#   1. Exit code is 0 (argparse's --help exits 0; non-zero here signals an
#      import error, syntax error, or argparse regression that crashes
#      before help is printed).
#   2. Combined stdout+stderr contains no "Traceback" (a traceback means
#      the script crashed while loading or while parsing args, even if it
#      somehow returned 0).
#
# Scope: build/ + tools/ only. scripts/checks/*.py are per-check modules
# dispatched by the validators (not invoked directly with --help) and
# scripts/lib/ holds shared helpers (no CLI surface).
#
# Catches:
#   - Syntax errors in the script
#   - Import errors (missing dependency, broken import path)
#   - Argparse regressions (required positional consumed before --help,
#     malformed subparser config, typoed default values, etc.)
#
# Fast; no fixtures; safe to wire into CI or a pre-commit hook later.
# Exits 0 if every script passes; exits 1 if any script fails.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/scripts"

if [ ! -d "$SCRIPTS_DIR/build" ] || [ ! -d "$SCRIPTS_DIR/tools" ]; then
    echo "ERROR: scripts/build/ and/or scripts/tools/ missing at $SCRIPTS_DIR" >&2
    exit 1
fi

pass=0
fail=0
failures=()

for tier in build tools; do
    for script in "$SCRIPTS_DIR/$tier"/*.py; do
        [ -e "$script" ] || continue  # no *.py match
        name="$tier/$(basename "$script")"
        out="$(python3 "$script" --help 2>&1)"
        rc=$?
        if [ "$rc" -ne 0 ]; then
            failures+=("$name — exit $rc")
            fail=$((fail + 1))
            continue
        fi
        if printf '%s\n' "$out" | grep -q "Traceback"; then
            failures+=("$name — traceback in --help output")
            fail=$((fail + 1))
            continue
        fi
        pass=$((pass + 1))
    done
done

echo "======================================================================"
echo " scripts/{build,tools}/*.py --help smoke test"
echo "======================================================================"
echo
echo "  Passed: $pass"
echo "  Failed: $fail"

if [ "$fail" -gt 0 ]; then
    echo
    echo "Failures:"
    for f in "${failures[@]}"; do
        echo "  - $f"
    done
    exit 1
fi

exit 0
