#!/usr/bin/env bash
# Pre-commit gate — chain all repository validators into a single
# exit-code gate. Non-zero exit on any failure blocks the commit.
#
# Runs, in order:
#   1. scripts/tests/help-check.sh           — scripts/**/*.py --help doesn't crash
#   2. scripts/tests/test_stopwords.py       — STOPWORDS shape + no content-word
#                                              contamination (lib/_common.py)
#   3. scripts/tests/smoke.sh                — fixture scaffold + validate per type
#   4. python3 scripts/build/validate.py     — structural + verbatim-quote +
#                                              governance-file + conditionally_required
#   5. python3 scripts/build/validate-research.py
#                                            — research-artifact structural check
#   6. python3 scripts/build/review-coverage.py --all
#                                            — cross-layer check (artifact ↔ rendered
#                                              node): coverage / boundary /
#                                              stub-linking / description-drift
#   7. python3 scripts/build/build-state.py --check
#                                            — CLAUDE.md build-state block in sync
#   8. scripts/tests/file-size-check.sh      — git-tracked files within
#                                              GitHub's size thresholds (warn
#                                              50MB / error 100MB)
#   9. scripts/tests/cookies-check.sh        — no tracked file contains
#                                              Netscape cookies content or
#                                              Google session cookies in
#                                              Netscape-shape rows (defensive
#                                              backstop to .gitignore patterns)
#
# Adding or removing a gate: edit the `steps` array below. Step
# numbering ("N/total") regenerates automatically from the array length.
#
# ─── Installation (contributor-driven; not auto-wired) ──────────────────
#
# From the repository root (REFACTOR/):
#
#     ln -sf "$(pwd)/scripts/tests/pre-commit.sh" .git/hooks/pre-commit
#     chmod +x .git/hooks/pre-commit
#
# Or, if your working tree is a worktree / the hooks path is elsewhere:
#
#     git config core.hooksPath scripts/tests
#     mv scripts/tests/pre-commit.sh scripts/tests/pre-commit     # git looks for `pre-commit`, no extension
#     chmod +x scripts/tests/pre-commit
#
# To skip the hook on a single commit (e.g., WIP) — only when you're
# certain the commit isn't production-ready:
#
#     git commit --no-verify
#
# ─── Why this isn't auto-installed ──────────────────────────────────────
#
# Installing git hooks rewrites contributor-local git state. That's
# explicit, opt-in behavior. CI can chain the same commands as this
# script without needing the hook installed locally.
#
# ────────────────────────────────────────────────────────────────────────

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

step() {
    echo "======================================================================"
    echo " $1"
    echo "======================================================================"
}

fail_count=0
step_results=()

run_step() {
    local label="$1"; shift
    step "$label"
    if "$@"; then
        step_results+=("  ✓ $label")
    else
        step_results+=("  ✗ $label  (exit $?)")
        fail_count=$((fail_count + 1))
    fi
    echo
}

# Each entry pairs a step label with a tab-delimited command. Step
# numbering ("N/total") is generated below from this list — adding or
# removing an entry renumbers the rest.
#
# Constraint: command tokens are split on whitespace at iteration time
# (unquoted $cmd word-splits via IFS). Safe for the current command
# shapes (no embedded spaces in args). If a future gate needs an arg
# with spaces, switch to a different command-storage idiom.
steps=(
    $'help-check\tbash scripts/tests/help-check.sh'
    $'test_stopwords\tpython3 scripts/tests/test_stopwords.py'
    $'smoke\tbash scripts/tests/smoke.sh'
    $'validate.py\tpython3 scripts/build/validate.py'
    $'validate-research.py\tpython3 scripts/build/validate-research.py'
    $'review-coverage.py\tpython3 scripts/build/review-coverage.py --all'
    $'build-state.py --check\tpython3 scripts/build/build-state.py --check'
    $'file-size-check\tbash scripts/tests/file-size-check.sh'
    $'cookies-check\tbash scripts/tests/cookies-check.sh'
)

total=${#steps[@]}
n=0
for entry in "${steps[@]}"; do
    n=$((n + 1))
    label="${entry%%$'\t'*}"
    cmd="${entry#*$'\t'}"
    run_step "$n/$total  $label" $cmd
done

# Summary
echo "======================================================================"
echo " pre-commit summary"
echo "======================================================================"
echo
for line in "${step_results[@]}"; do
    echo "$line"
done
echo

if [ "$fail_count" -gt 0 ]; then
    echo "FAILED — $fail_count step(s) did not pass. Commit blocked."
    echo
    echo "Fix the failures and re-run, or use --no-verify to bypass (not"
    echo "recommended unless you know the specific failure is expected)."
    exit 1
fi

echo "PASSED — all gates green. Commit may proceed."
exit 0
