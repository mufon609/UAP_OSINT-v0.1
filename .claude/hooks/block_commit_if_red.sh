#!/usr/bin/env bash
# PreToolUse(Bash) — anti-bypass guard for the commit gate.
#
# The gate chain runs at COMMIT EXECUTION time via the repo-versioned
# `.githooks/pre-commit` (armed through `git config core.hooksPath
# .githooks`), so a compound `fix && git commit` is gated on its post-fix
# state. This hook keeps that floor un-droppable; on the happy path it does
# not run the chain itself:
#   1. arms `core.hooksPath` on every commit attempt (fresh clones included);
#   2. denies the bypass routes — `--no-verify` (and prefix abbreviations),
#      a short-flag cluster carrying `-n`, any `core.hooksPath` manipulation.
#      The scan (commit_guard.py) shlex-tokenizes with heredoc bodies
#      stripped first, so commit-message prose about these flags never
#      trips it;
#   3. if `.githooks/pre-commit` is missing or hooksPath cannot be armed,
#      falls back to running the chain right here, at PreToolUse time —
#      the floor never drops.
#
# Exit 0 = allow (the commit-time hook then gates the commit). Exit 2 = block.
set -u
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
GUARD="$REPO_ROOT/.claude/hooks/commit_guard.py"

payload="$(cat)"

verdict=""
if [ -f "$GUARD" ]; then
    verdict="$(printf '%s' "$payload" | python3 "$GUARD" 2>/dev/null)" || verdict=""
fi
if [ -z "$verdict" ]; then
    # Degraded mode (guard missing or crashed): substring-detect a commit
    # and run the chain in place — the pre-githook behavior.
    case "$payload" in
        *"git commit"*) verdict="fallback" ;;
        *) exit 0 ;;
    esac
fi

case "$verdict" in
    allow) exit 0 ;;
    deny*)
        echo "Commit blocked — ${verdict#deny }." >&2
        echo "The gate chain runs inside git commit via .githooks/pre-commit;" >&2
        echo "bypass routes are denied. Fix any red gates instead." >&2
        exit 2 ;;
esac

# verdict: commit — arm the commit-time hook, then let `git commit` run it.
if [ "$verdict" = "commit" ]; then
    hp="$(git -C "$REPO_ROOT" config core.hooksPath 2>/dev/null || true)"
    if [ "$hp" != ".githooks" ]; then
        git -C "$REPO_ROOT" config core.hooksPath .githooks 2>/dev/null || true
        hp="$(git -C "$REPO_ROOT" config core.hooksPath 2>/dev/null || true)"
    fi
    if [ "$hp" = ".githooks" ] && [ -x "$REPO_ROOT/.githooks/pre-commit" ]; then
        exit 0
    fi
fi

# Floor fallback — hook missing or hooksPath couldn't be armed: run the
# chain here, exactly as before the githook existed.
out="$(cd "$REPO_ROOT" && bash scripts/tests/pre-commit.sh 2>&1)"
if [ $? -ne 0 ]; then
    echo "Commit blocked — the pre-commit gate chain failed (this guard runs" >&2
    echo "regardless of --no-verify). Fix the failures, then commit:" >&2
    printf '%s\n' "$out" | tail -25 >&2
    exit 2
fi
exit 0
