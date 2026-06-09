#!/usr/bin/env bash
# Pre-commit gate — chain all repository validators into a single
# exit-code gate. Non-zero exit on any failure blocks the commit.
#
# Runs, in order:
#   1. scripts/tests/help-check.sh           — scripts/**/*.py --help doesn't crash
#   2. scripts/tests/test_stopwords.py       — STOPWORDS shape + no content-word
#                                              contamination (lib/_common.py)
#   3. scripts/tests/smoke.py                — fixture scaffold + validate per type
#   4. python3 scripts/build/validate.py     — structural + verbatim-quote +
#                                              governance-file + conditionally_required
#   5. python3 scripts/build/validate-research.py
#                                            — research-artifact structural check
#      python3 scripts/build/validate-speaker-attribution.py --quiet
#                                            — speaker-attribution sibling structural
#                                              check (incl. verified = no rationale/
#                                              verifier_notes scaffolding)
#   6. python3 scripts/build/review-coverage.py --all
#                                            — cross-layer check (artifact ↔ rendered
#                                              node): coverage / boundary /
#                                              stub-linking / description-drift
#   7. python3 scripts/build/build-state.py --check
#                                            — CLAUDE.md build-state block in sync
#   8. python3 scripts/build/associate.py --check
#                                            — every node's '## Associated Nodes'
#                                              section matches the links derived
#                                              from its own body (no drift)
#   9. python3 scripts/build/renderer-coverage.py
#                                            — every schema-required section is
#                                              renderer-producible (schema
#                                              required/optional/conditional
#                                              sections ⊆ renderer EMITS)
#  10. python3 scripts/build/phase_routing_parity.py
#                                            — every --phase token in prompts/
#                                              + .claude/ is valid per
#                                              scripts/checks/_phases.py, and
#                                              every canonical phase is
#                                              documented in build-protocol/
#                                              SKILL.md
#  11. scripts/tests/skills-check.sh         — .claude/ skills + subagents have
#                                              valid frontmatter, hard-code no
#                                              topic token (fork-portable), and
#                                              settings.json parses
#  12. scripts/tests/file-size-check.sh      — git-tracked files within
#                                              GitHub's size thresholds (warn
#                                              50MB / error 100MB)
#  13. scripts/tests/cookies-check.sh        — no tracked file contains
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
# To skip the OPTIONAL git symlink on a single commit (e.g., WIP) — only
# when you're certain the commit isn't production-ready:
#
#     git commit --no-verify
#
# --no-verify skips ONLY this git symlink. The Claude Code PreToolUse
# commit-gate hook (.claude/hooks/block_commit_if_red.sh) re-runs this same
# chain at the tool boundary and is NOT bypassable by --no-verify.
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
    $'smoke\tpython3 scripts/tests/smoke.py'
    $'validate.py\tpython3 scripts/build/validate.py'
    $'validate-research.py\tpython3 scripts/build/validate-research.py'
    $'validate-speaker-attribution.py\tpython3 scripts/build/validate-speaker-attribution.py --quiet'
    $'review-coverage.py\tpython3 scripts/build/review-coverage.py --all'
    $'build-state.py --check\tpython3 scripts/build/build-state.py --check'
    $'associate.py --check\tpython3 scripts/build/associate.py --check'
    $'renderer-coverage.py\tpython3 scripts/build/renderer-coverage.py --quiet'
    $'phase-routing-parity\tpython3 scripts/build/phase_routing_parity.py --quiet'
    $'skills-check\tbash scripts/tests/skills-check.sh'
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
    echo "Fix the failures and re-run. (git --no-verify skips only the"
    echo "optional .git/hooks symlink — NOT the Claude Code PreToolUse"
    echo "commit-gate hook, which re-runs this chain un-bypassably.)"
    exit 1
fi

echo "PASSED — all gates green. Commit may proceed."
exit 0
