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

fp="$(python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get("tool_input", {}).get("file_path", ""))')"

[ -n "$fp" ] || exit 0
rel="${fp#"$REPO_ROOT"/}"   # normalize absolute -> repo-relative

case "$rel" in
    people/*.md|organizations/*.md|documents/*.md|events/*.md|transcripts/*.md|media/*.md|locations/*.md|findings/*.md|investigations/*.md)
        echo "Blocked — $rel is a rendered node body (renderer output)." >&2
        echo "Node bodies are regenerated from the research artifact. Edit" >&2
        echo "meta/research/ instead, then rebuild with build-from-research.py." >&2
        exit 2 ;;
esac
exit 0
