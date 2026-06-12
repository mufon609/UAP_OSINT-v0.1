#!/usr/bin/env bash
# Scratch-hygiene pre-commit gate — the two scratch tiers cannot accrue
# junk past the session that made it.
#
# Tiers covered (each tracked via a self-ignoring .gitignore so the
# directory exists on fresh clones; everything else inside is local):
#   .scratch/         durable agent-draft DATA (expensive in-flight
#                     pipeline artifacts that must survive /tmp cleanup)
#   scripts/scratch/  throwaway exploratory query SCRIPTS
#
# Lifecycle rule (the durable-parking contract): a top-level entry is
# legitimate only while
#   (a) it is REFERENCED by path from meta/BACKLOG.md or meta/roadmap.md
#       — parked cross-session work must be named by the open work item
#       that will consume it (a paused pipeline's BACKLOG entry pins its
#       draft paths), or
#   (b) it is FRESH — modified within GRACE_DAYS (in-flight work in the
#       current session/week that no entry needs to name yet).
# Anything else blocks the commit until a contributor deletes it or
# files the work item that owns it. Deletion stays HUMAN: age-based
# auto-deletion is exactly the /tmp behavior that destroyed multi-hour
# drafts and forced .scratch/ to exist — this gate automates detection,
# never destruction.
#
# GRACE_DAYS=7: spans an in-flight week between commits; anything parked
# longer is cross-session by definition and must be BACKLOG/roadmap-named.
#
# Exits 0 when both tiers are clean; 1 with the offending entries listed.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

GRACE_DAYS=7
GOVERNANCE=(meta/BACKLOG.md meta/roadmap.md)
ROOTS=(.scratch scripts/scratch)

violations=()
kept=0

for root in "${ROOTS[@]}"; do
    [ -d "$root" ] || continue
    while IFS= read -r -d '' entry; do
        name="$(basename "$entry")"
        [ "$name" = ".gitignore" ] && continue
        # (a) referenced from an open governance entry, by repo-relative path
        if grep -qF "$root/$name" "${GOVERNANCE[@]}" 2>/dev/null; then
            kept=$((kept + 1))
            continue
        fi
        # (b) fresh — any file inside modified within the grace window
        if [ -n "$(find "$entry" -mtime "-$GRACE_DAYS" -print -quit 2>/dev/null)" ]; then
            kept=$((kept + 1))
            continue
        fi
        violations+=("$root/$name")
    done < <(find "$root" -mindepth 1 -maxdepth 1 -print0 | sort -z)
done

echo "======================================================================"
echo " Scratch hygiene (.scratch/ + scripts/scratch/ — referenced or fresh)"
echo "======================================================================"
echo

if [ ${#violations[@]} -eq 0 ]; then
    echo "  Clean: no unreferenced entry older than ${GRACE_DAYS} days" \
         "(${kept} in-flight/parked entr$( [ "$kept" -eq 1 ] && echo y || echo ies ))."
    exit 0
fi

echo "Stale scratch (unreferenced by meta/BACKLOG.md / meta/roadmap.md and"
echo "untouched for over ${GRACE_DAYS} days):"
for v in "${violations[@]}"; do
    echo "  - $v"
done
echo
echo "  Closing work includes sweeping its scratch. For each entry: delete"
echo "  it (the shipped artifact/commit is the record), or — if it parks"
echo "  genuinely open cross-session work — name its path from the BACKLOG/"
echo "  roadmap entry that owns it."
exit 1
