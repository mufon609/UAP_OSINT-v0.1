#!/usr/bin/env bash
# File-size pre-commit gate — error on any git-tracked file over 100MB
# (GitHub's hard reject threshold) and warn on any file over 50MB
# (GitHub's display warning threshold).
#
# Per `meta/sources-access.md` "Large primary-source files (>100MB)",
# oversized primary sources are kept locally and registered in
# `sources/manifest.yaml` with URL + sha256, but excluded from the git
# remote via `.gitignore`. This gate confirms no oversized file slipped
# past that discipline before a push attempt forces a costly history
# rewrite.
#
# Walks the git index (`git ls-files`) — gitignore'd files are
# intentionally excluded, by design.
#
# Exits 0 on success (all files at-or-under 100MB); 1 if any file
# exceeds the hard limit. 50–100MB files print as warnings but do not
# block.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

WARN_BYTES=$((50 * 1024 * 1024))
ERROR_BYTES=$((100 * 1024 * 1024))

warnings=()
errors=()

while IFS= read -r path; do
    [ -f "$path" ] || continue
    bytes=$(stat -c '%s' "$path" 2>/dev/null || echo 0)
    if [ "$bytes" -gt "$ERROR_BYTES" ]; then
        mb=$((bytes / 1024 / 1024))
        errors+=("$path  (${mb}MB — exceeds 100MB GitHub hard limit)")
    elif [ "$bytes" -gt "$WARN_BYTES" ]; then
        mb=$((bytes / 1024 / 1024))
        warnings+=("$path  (${mb}MB — over 50MB GitHub warn threshold)")
    fi
done < <(git ls-files)

echo "======================================================================"
echo " File-size check (git-tracked; warn 50MB / error 100MB)"
echo "======================================================================"
echo

if [ ${#errors[@]} -eq 0 ] && [ ${#warnings[@]} -eq 0 ]; then
    echo "  All git-tracked files within size limits."
    exit 0
fi

if [ ${#warnings[@]} -gt 0 ]; then
    echo "Warnings (50MB–100MB; printed, not blocking):"
    for w in "${warnings[@]}"; do
        echo "  - $w"
    done
    echo
fi

if [ ${#errors[@]} -gt 0 ]; then
    echo "Errors (over 100MB — GitHub will reject the push):"
    for e in "${errors[@]}"; do
        echo "  - $e"
    done
    echo
    echo "  Recovery: per meta/sources-access.md \"Large primary-source"
    echo "  files (>100MB)\", oversized primary sources stay local and"
    echo "  register in sources/manifest.yaml (URL + sha256) but are"
    echo "  excluded from git via .gitignore. To remove a file from the"
    echo "  git index without deleting the local copy:"
    echo "    git rm --cached <path>"
    echo "    git commit --amend --no-edit"
    exit 1
fi

# Warnings only — informational; do not fail the gate.
exit 0
