#!/usr/bin/env bash
# PreToolUse(Bash) — when the command is a `git commit`, run the full
# pre-commit gate chain and BLOCK the commit (exit 2) if anything is red.
#
# The harness runs this hook regardless of git flags, so `git commit
# --no-verify` cannot bypass it — this is the un-skippable floor that the
# opt-in `.git/hooks` symlink lacked. The pre-commit chain is the single
# source of truth for "is the repo committable"; this hook just enforces it
# at the commit boundary.
#
# Exit 0 = allow (not a commit, or all gates green). Exit 2 = block.
set -u
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

cmd="$(python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get("tool_input", {}).get("command", ""))')"

case "$cmd" in
    *"git commit"*) ;;   # act only on commit invocations
    *) exit 0 ;;
esac

out="$(cd "$REPO_ROOT" && bash scripts/tests/pre-commit.sh 2>&1)"
if [ $? -ne 0 ]; then
    echo "Commit blocked — the pre-commit gate chain failed (this hook runs" >&2
    echo "regardless of --no-verify). Fix the failures, then commit:" >&2
    printf '%s\n' "$out" | tail -25 >&2
    exit 2
fi
exit 0
