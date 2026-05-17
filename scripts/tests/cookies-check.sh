#!/usr/bin/env bash
# cookies-check pre-commit gate — refuse any git-tracked file containing
# Netscape HTTP Cookie File content or load-bearing Google session cookies.
#
# Background: yt-dlp / Firefox cookies.txt files authenticate full Google
# account access (SID, SAPISID, __Secure-*PSID, LOGIN_INFO). They must
# never land in git history. This gate is the defensive backstop to the
# .gitignore patterns that block staging — if a file slips past gitignore
# (renamed, placed under a non-standard path), this catches it before
# commit.
#
# Detection (two independent checks; either triggers the gate):
#
#   1. First-3-lines header: `# Netscape HTTP Cookie File` — the
#      canonical export marker used by Firefox, Chrome extensions,
#      yt-dlp, curl, extract-firefox-cookies.py. Restricted to first 3
#      lines so the marker string appearing deeper in code (e.g., the
#      `extract-firefox-cookies.py` print statement that writes the
#      header) doesn't false-positive.
#
#   2. Netscape-shape lines with sensitive cookie names in field 6:
#      tab-separated, ≥7 fields per line, with `SAPISID` / `LOGIN_INFO` /
#      `__Secure-1PSID` / etc. as the field-6 cookie name. Catches the
#      case where someone strips the header but commits the rows.
#      HTML / JSON / prose files containing these strings as plain
#      text don't trigger because they lack the tab-delimited Netscape
#      shape.
#
# Walks `git ls-files` only — gitignore'd paths are intentionally
# excluded. Skips binaries and files >512KB to keep the gate fast.
#
# Exits 0 if clean; 1 if any tracked file matches either pattern.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

MAX_SCAN_BYTES=$((512 * 1024))

errors=()

while IFS= read -r path; do
    [ -f "$path" ] || continue
    # Self-exclusion: this script legitimately documents the detection
    # patterns it scans for (Netscape header + sensitive cookie names).
    # Without this skip, the gate trips on its own source.
    [ "$path" = "scripts/tests/cookies-check.sh" ] && continue
    bytes=$(stat -c '%s' "$path" 2>/dev/null || echo 0)
    [ "$bytes" -gt "$MAX_SCAN_BYTES" ] && continue
    case "$(file --mime-type -b "$path" 2>/dev/null)" in
        text/*|application/json|application/xml|application/x-yaml|inode/x-empty) ;;
        *) continue ;;
    esac

    # Check 1: canonical Netscape header in first 3 lines
    if head -3 "$path" 2>/dev/null | grep -qF '# Netscape HTTP Cookie File'; then
        errors+=("$path  (Netscape HTTP Cookie File header)")
        continue
    fi

    # Check 2: Netscape-shape rows with sensitive cookie names in field 6
    if awk -F'\t' '
        NF >= 7 && ($6 == "SAPISID" || $6 == "LOGIN_INFO" \
                || $6 == "__Secure-1PSID" || $6 == "__Secure-3PSID" \
                || $6 == "__Secure-1PAPISID" || $6 == "__Secure-3PAPISID" \
                || $6 == "HSID" || $6 == "SSID") { found=1; exit 0 }
        END { exit !found }' "$path" 2>/dev/null; then
        errors+=("$path  (sensitive Google session cookie in Netscape format)")
    fi
done < <(git ls-files)

echo "======================================================================"
echo " Cookies / session-credential check (git-tracked files)"
echo "======================================================================"
echo

if [ ${#errors[@]} -eq 0 ]; then
    echo "  No cookies / session-credential content in tracked files."
    exit 0
fi

echo "ERROR: tracked file(s) contain cookie / session-credential content:"
for e in "${errors[@]}"; do
    echo "  - $e"
done
echo
echo "These are session credentials (Google account auth tokens) and must"
echo "never land in git history. Remove from the index:"
echo
echo "    git rm --cached <path>"
echo "    git commit --amend --no-edit   # rewrites the offending commit"
echo
echo "Add the path (or a matching glob) to .gitignore to prevent re-add."
echo "If the file should never have existed locally either, shred it:"
echo
echo "    shred -u <path>"
exit 1
