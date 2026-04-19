#!/usr/bin/env bash
# Pre-commit gate — chain all repository validators into a single exit-
# code gate. Non-zero exit on any failure blocks the commit.
#
# Runs, in order:
#   1. tests/help-check.sh              — scripts/*.py --help doesn't crash
#   2. tests/smoke.sh                   — fixture scaffold + validate per type
#   3. python3 scripts/validate.py      — structural + verbatim-quote +
#                                         governance-file + conditionally_required
#   4. python3 scripts/validate-research.py
#                                       — research-artifact structural check
#   5. python3 scripts/build-state.py --check
#                                       — CLAUDE.md build-state block in sync
#   6. python3 scripts/audit-schedule.py --overdue
#                                       — research-artifact audit cadence
#                                         (skipped silently if the flag is
#                                         not supported by the shipped
#                                         audit-schedule.py — wiring is
#                                         forward-compatible)
#
# Covers: BACKLOG "Testing infrastructure" step 4 (pre-commit hook) +
# the audit-cadence half of Step E.1 on the roadmap.
#
# ─── Installation (contributor-driven; not auto-wired) ──────────────────
#
# From the repository root (REFACTOR/):
#
#     ln -sf "$(pwd)/tests/pre-commit.sh" .git/hooks/pre-commit
#     chmod +x .git/hooks/pre-commit
#
# Or, if your working tree is a worktree / the hooks path is elsewhere:
#
#     git config core.hooksPath tests
#     mv tests/pre-commit.sh tests/pre-commit     # git looks for `pre-commit`, no extension
#     chmod +x tests/pre-commit
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

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

run_step "1/6  help-check"              bash tests/help-check.sh
run_step "2/6  smoke"                   bash tests/smoke.sh
run_step "3/6  validate.py"             python3 scripts/validate.py
run_step "4/6  validate-research.py"    python3 scripts/validate-research.py
run_step "5/6  build-state.py --check"  python3 scripts/build-state.py --check

# audit-schedule.py --overdue: wired forward-compatibly. The --overdue
# flag is expected; if the shipped audit-schedule.py doesn't support it
# yet, treat as non-blocking so the pre-commit gate doesn't regress
# before the flag lands (tracked in Step E.1 on the roadmap).
step "6/6  audit-schedule.py --overdue"
if python3 scripts/audit-schedule.py --help 2>&1 | grep -q -- "--overdue"; then
    if python3 scripts/audit-schedule.py --overdue; then
        step_results+=("  ✓ 6/6  audit-schedule.py --overdue")
    else
        step_results+=("  ✗ 6/6  audit-schedule.py --overdue  (stale artifacts)")
        fail_count=$((fail_count + 1))
    fi
else
    echo "  (skipped — --overdue flag not implemented yet; tracked in"
    echo "   roadmap Step E.1. Will activate automatically once shipped.)"
    step_results+=("  — 6/6  audit-schedule.py --overdue  (skipped)")
fi
echo

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
