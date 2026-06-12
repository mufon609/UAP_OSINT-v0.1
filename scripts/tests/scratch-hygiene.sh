#!/usr/bin/env bash
# Scratch-hygiene pre-commit gate — the .scratch/ tree cannot accrue junk
# past the session that made it.
#
# One scratch tree, three lifecycle tiers (tracked via .scratch/.gitignore +
# per-tier .gitkeep so the layout exists on fresh clones; everything else
# inside is local):
#   .scratch/drafts/   durable agent-draft DATA (expensive in-flight
#                      pipeline artifacts that must survive /tmp cleanup)
#   .scratch/queries/  throwaway exploratory query SCRIPTS
#   .scratch/cache/    regenerable-but-expensive derived state (engine reads)
#
# Rules:
#   1. STRUCTURE — only the three tiers (+ .gitignore) may sit at the
#      .scratch/ top level. A stale writer using a pre-tier path fails the
#      next commit instead of getting grace.
#   2. REFERENCED-OR-FRESH (drafts/ + queries/, the durable-parking
#      contract) — a top-level tier entry is legitimate only while
#        (a) it is REFERENCED by path from meta/BACKLOG.md or
#            meta/roadmap.md — parked cross-session work must be named by
#            the open work item that will consume it, or
#        (b) it is FRESH — modified within GRACE_DAYS (in-flight work in
#            the current session/week that no entry needs to name yet).
#      Anything else blocks the commit until a contributor deletes it or
#      files the work item that owns it. Deletion stays HUMAN: age-based
#      auto-deletion is exactly the /tmp behavior that destroyed multi-hour
#      drafts and forced .scratch/ to exist — this gate automates detection,
#      never destruction.
#   3. CACHE SIZE — cache/ is exempt from referenced-or-fresh (a
#      content-addressed cache is not parked work, and forcing deletion of
#      a good cache is worse than /tmp). Engine-version bumps orphan old
#      keys with no other drift signal, so the gate prints a non-blocking
#      size note past CACHE_NOTE_MB.
#
# GRACE_DAYS=7: spans an in-flight week between commits; anything parked
# longer is cross-session by definition and must be BACKLOG/roadmap-named.
#
# Exits 0 when the tree is clean; 1 with the offending entries listed.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

GRACE_DAYS=7
GOVERNANCE=(meta/BACKLOG.md meta/roadmap.md)
SCRATCH=.scratch
TIERS=(drafts queries)
CACHE_NOTE_MB=1024

violations=()
kept=0

# 1. Structure: only the three tiers + .gitignore at the top level.
if [ -d "$SCRATCH" ]; then
    while IFS= read -r -d '' entry; do
        name="$(basename "$entry")"
        case "$name" in .gitignore|drafts|queries|cache) continue ;; esac
        violations+=("$SCRATCH/$name  (not a tier — only drafts/, queries/, cache/ live here)")
    done < <(find "$SCRATCH" -mindepth 1 -maxdepth 1 -print0 | sort -z)
fi

# 2. Referenced-or-fresh, per policed tier.
for tier in "${TIERS[@]}"; do
    root="$SCRATCH/$tier"
    [ -d "$root" ] || continue
    while IFS= read -r -d '' entry; do
        name="$(basename "$entry")"
        [ "$name" = ".gitkeep" ] && continue
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
echo " Scratch hygiene (.scratch/ tiers — structure + referenced-or-fresh)"
echo "======================================================================"
echo

# 3. Cache size — note only, never blocks.
if [ -d "$SCRATCH/cache" ]; then
    cache_mb=$(( $(du -sk "$SCRATCH/cache" 2>/dev/null | cut -f1) / 1024 ))
    if [ "$cache_mb" -gt "$CACHE_NOTE_MB" ]; then
        echo "  note: $SCRATCH/cache at ${cache_mb} MiB — prune-safe anytime" \
             "(the owning tool regenerates on a miss)."
        echo
    fi
fi

if [ ${#violations[@]} -eq 0 ]; then
    echo "  Clean: no stray top-level entry, no unreferenced entry older" \
         "than ${GRACE_DAYS} days (${kept} in-flight/parked entr$( [ "$kept" -eq 1 ] && echo y || echo ies ))."
    exit 0
fi

echo "Stale or misplaced scratch (structure violation, or unreferenced by"
echo "meta/BACKLOG.md / meta/roadmap.md and untouched for over ${GRACE_DAYS} days):"
for v in "${violations[@]}"; do
    echo "  - $v"
done
echo
echo "  Closing work includes sweeping its scratch. For each entry: delete"
echo "  it (the shipped artifact/commit is the record), or — if it parks"
echo "  genuinely open cross-session work — name its path from the BACKLOG/"
echo "  roadmap entry that owns it. Non-tier top-level entries move into"
echo "  drafts/, queries/, or cache/."
exit 1
