#!/usr/bin/env bash
# Pre-commit gate — chain all repository validators into a single exit-
# code gate. Non-zero exit on any failure blocks the commit.
#
# Runs, in order:
#   1. scripts/tests/help-check.sh      — scripts/*.py --help doesn't crash
#   2. scripts/tests/smoke.sh           — fixture scaffold + validate per type
#   3. python3 scripts/validate.py      — structural + verbatim-quote +
#                                         governance-file + conditionally_required
#   4. python3 scripts/validate-research.py
#                                       — research-artifact structural check
#   5. python3 scripts/build-state.py --check
#                                       — CLAUDE.md build-state block in sync
#
# Covers: BACKLOG "Testing infrastructure" step 4 (pre-commit hook).
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

run_step "1/5  help-check"              bash scripts/tests/help-check.sh
run_step "2/5  smoke"                   bash scripts/tests/smoke.sh
run_step "3/5  validate.py"             python3 scripts/validate.py
run_step "4/5  validate-research.py"    python3 scripts/validate-research.py
run_step "5/5  build-state.py --check"  python3 scripts/build-state.py --check

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
