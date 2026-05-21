#!/usr/bin/env bash
# PreToolUse(Bash) — enforce the one-new-synthesis-node-per-session rule.
#
# A new person/organization node is a large free-prose surface (the
# drift-prone types). The 2026-04-17 pilot failure established: scaffold only
# one such node until it is populated, validated, and COMMITTED. This hook
# makes that mechanical — it blocks a `new.py person|organization` scaffold
# while an uncommitted new person/org node body already exists. Lighter types
# (document/event/transcript/media/location/finding/investigation) batch
# freely and are never blocked.
#
# "Uncommitted new" = a person/org node `.md` that git reports as untracked
# (??) or added-not-committed (A) — i.e. exactly "not yet committed".
#
# Exit 0 = allow. Exit 2 = block.
set -u
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

cmd="$(python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get("tool_input", {}).get("command", ""))')"

case "$cmd" in
    *"new.py person"*|*"new.py organization"*) ;;   # synthesis-heavy types only
    *) exit 0 ;;
esac

uncommitted="$(cd "$REPO_ROOT" && git status --porcelain -- people organizations 2>/dev/null \
    | grep -E '^(\?\?|A.) (people|organizations)/[^/]+\.md$')"

if [ -n "$uncommitted" ]; then
    echo "Blocked — an uncommitted new person/organization node already exists" >&2
    echo "this session. One new synthesis-heavy node (person/org) at a time:" >&2
    echo "finish, validate, and COMMIT it before scaffolding another (the" >&2
    echo "2026-04-17 batching rule). Lighter types may batch freely." >&2
    echo "Uncommitted new synthesis node(s):" >&2
    printf '%s\n' "$uncommitted" >&2
    exit 2
fi
exit 0
