#!/usr/bin/env bash
# PreToolUse(Edit|Write) — block hand-edits to rendered node bodies.
#
# A node body under a content-node directory is renderer output, regenerated
# from its research artifact ("fix the data, never the node body"). The
# renderer (build-from-research.py) writes these files via Python file I/O,
# NOT through the Edit/Write tool, so it is unaffected by this hook — only an
# agent's Edit/Write tool call is gated. Artifacts (meta/research/*.yaml)
# remain freely editable; this only blocks the rendered `{type}/{slug}.md`.
#
# Exit 0 = allow. Exit 2 = block.
set -u
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Normalize to a clean repo-relative path in Python (collapses ./, //, .., and
# a trailing slash on REPO_ROOT) — a literal prefix-strip alone leaves forms
# like ./people/foo.md or /repo//people/foo.md unmatched by the case below.
rel="$(REPO_ROOT="$REPO_ROOT" python3 -c 'import sys, json, os
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
fp = d.get("tool_input", {}).get("file_path", "")
if not fp:
    sys.exit(0)
root = os.path.normpath(os.environ["REPO_ROOT"])
ap = os.path.normpath(fp if os.path.isabs(fp) else os.path.join(root, fp))
print(os.path.relpath(ap, root))')"

[ -n "$rel" ] || exit 0

case "$rel" in
    people/*.md|organizations/*.md|documents/*.md|events/*.md|transcripts/*.md|media/*.md|locations/*.md|findings/*.md|investigations/*.md)
        echo "Blocked — $rel is a rendered node body (renderer output)." >&2
        echo "Node bodies are regenerated from the research artifact. Edit" >&2
        echo "meta/research/ instead, then rebuild with build-from-research.py." >&2
        exit 2 ;;
esac
exit 0
