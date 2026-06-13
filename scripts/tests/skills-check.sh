#!/usr/bin/env bash
# Lint for the .claude/ toolkit surface (skills, subagents, settings).
#
# Checks three things, all topic-neutral:
#   1. Frontmatter shape — every .claude/skills/*/SKILL.md has YAML
#      frontmatter with a `description:`; every .claude/agents/*.md has
#      `name:` and `description:`. (These drive auto-selection/delegation;
#      a skill/agent without them is silently undiscoverable.)
#   2. Topic-neutrality — no skill/agent body hard-codes this instance's
#      topic token. The token is read DYNAMICALLY from
#      meta/topic/overview.md (`topic:` + `display_name:`), so this gate
#      keeps working after a fork. Skill/agent bodies must use the
#      `{display_name}` placeholder, never the literal subject word — that
#      is what makes .claude/ survive `/fork-init`.
#   3. settings.json validity — if .claude/settings.json exists, it parses
#      as JSON.
#
# Missing .claude/skills or .claude/agents directories pass trivially
# (nothing to lint yet). Exits 0 if all pass; 1 on any failure.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

fail=0
err() { echo "  ✗ $1"; fail=$((fail + 1)); }

# ── 1. frontmatter shape ────────────────────────────────────────────────
has_frontmatter() {
    # first line is '---' and a closing '---' exists in the file
    [ "$(head -1 "$1")" = "---" ] && [ "$(grep -c '^---$' "$1")" -ge 2 ]
}
fm_field() {
    # value of a frontmatter key (lines before the 2nd '---')
    awk -v k="$2" '
        /^---$/ { d++; next }
        d==1 && $0 ~ "^" k ":" { print; exit }
    ' "$1"
}

if [ -d .claude/skills ]; then
    while IFS= read -r -d '' f; do
        has_frontmatter "$f" || { err "$f — missing/!malformed YAML frontmatter"; continue; }
        [ -n "$(fm_field "$f" description)" ] || err "$f — frontmatter has no 'description:'"
    done < <(find .claude/skills -name SKILL.md -print0)
fi

if [ -d .claude/agents ]; then
    while IFS= read -r -d '' f; do
        has_frontmatter "$f" || { err "$f — missing/malformed YAML frontmatter"; continue; }
        [ -n "$(fm_field "$f" name)" ]        || err "$f — frontmatter has no 'name:'"
        [ -n "$(fm_field "$f" description)" ] || err "$f — frontmatter has no 'description:'"
    done < <(find .claude/agents -maxdepth 2 -name '*.md' -print0)
fi

# ── 2. topic-neutrality ─────────────────────────────────────────────────
OVERVIEW="meta/topic/overview.md"
if [ -f "$OVERVIEW" ]; then
    # pull the values from the overview frontmatter
    topic="$(awk -F': *' '/^topic:/ {print $2; exit}' "$OVERVIEW" | tr -d '\r')"
    display="$(awk -F': *' '/^display_name:/ {print $2; exit}' "$OVERVIEW" | tr -d '\r')"
    for token in "$topic" "$display"; do
        [ -n "$token" ] || continue
        for dir in .claude/skills .claude/agents .claude/hooks; do
            [ -d "$dir" ] || continue
            # case-insensitive whole-word match for the subject token in any
            # body. -F (literal): a forked topic may contain regex metachars
            # (C++, A.B) — without it the token is a pattern and mis-matches.
            hits="$(grep -riwnF -- "$token" "$dir" 2>/dev/null || true)"
            if [ -n "$hits" ]; then
                err "topic token '$token' hard-coded in toolkit files (use the {display_name} placeholder so .claude/ survives a fork):"
                printf '%s\n' "$hits" | sed 's/^/        /'
            fi
        done
    done
fi

# ── 3. settings.json validity ───────────────────────────────────────────
if [ -f .claude/settings.json ]; then
    python3 -m json.tool .claude/settings.json >/dev/null 2>&1 || err ".claude/settings.json — not valid JSON"
fi

echo "======================================================================"
echo " .claude/ skills + subagents + settings lint"
echo "======================================================================"
if [ "$fail" -gt 0 ]; then
    echo
    echo "FAILED — $fail issue(s)."
    exit 1
fi
echo
echo "  ✓ frontmatter shape, topic-neutrality, settings.json all clean"
exit 0
