#!/usr/bin/env bash
# Behavior-diff harness — verifies that two validator-orchestrator
# states produce equivalent output on the corpus they each ship with.
#
# Per BACKLOG C18: the C11/C13/C14 cluster decomposed every named
# validator check into per-module callables. Behavioral parity is
# asserted via the corpus pass (0/0 on the live data, byte-identical
# to pre-migration). This harness is the stronger invariant — capture
# the pre-cluster validator's full output (errors + warnings + broken-
# link registry) and the post-cluster validator's full output, then
# diff. Empty diff (modulo intentional formatting changes like the
# check_name field) confirms behavioral identity beyond what 0/0
# implies.
#
# One-shot, not gate-invoked. The corpus 0/0 pre-commit pass remains
# the load-bearing signal; this diff is byte-identical confirmation
# for the cluster's behavioral-equivalence claim. Re-runnable for any
# future cluster of similar scale by passing different SHAs.
#
# Usage:
#   scripts/tests/behavior-diff.sh [PRE_SHA] [POST_REF]
#
# Defaults:
#   PRE_SHA  = 6a6726d  — parent of the C11/C13/C14 cluster's first code
#                         commit (472e547); last commit before any
#                         scripts/checks/ migration.
#   POST_REF = HEAD     — current state.
#
# Captures are preserved under scripts/tests/behavior-diff-baseline/
# (pre/ and post/ subdirs, each carrying .SHA + per-script
# {stdout, stderr, exit-code} files).
#
# Implementation: uses git worktree to materialize each ref in an
# isolated directory; main worktree is never checked-out away from.
# Validators read REPO_ROOT relative to their own file location so
# they run cleanly in any worktree.

set -e

PRE_SHA="${1:-6a6726d}"
POST_REF="${2:-HEAD}"

ROOT="$(git rev-parse --show-toplevel)"
OUT="$ROOT/scripts/tests/behavior-diff-baseline"

# Refuse to run dirty — captures must reflect committed state of the
# refs being diffed, not a hybrid with uncommitted local edits.
if ! git -C "$ROOT" diff-index --quiet HEAD --; then
  echo "Refusing to run with uncommitted changes — commit or stash first." >&2
  exit 1
fi

PRE_FULL=$(git -C "$ROOT" rev-parse "$PRE_SHA")
POST_FULL=$(git -C "$ROOT" rev-parse "$POST_REF")
PRE_SHORT=$(git -C "$ROOT" rev-parse --short "$PRE_FULL")
POST_SHORT=$(git -C "$ROOT" rev-parse --short "$POST_FULL")

mkdir -p "$OUT/pre" "$OUT/post"

WT_PRE=$(mktemp -d -t behavior-diff-pre.XXXXXX)
WT_POST=$(mktemp -d -t behavior-diff-post.XXXXXX)

cleanup() {
  git -C "$ROOT" worktree remove --force "$WT_PRE" 2>/dev/null || true
  git -C "$ROOT" worktree remove --force "$WT_POST" 2>/dev/null || true
  rmdir "$WT_PRE" "$WT_POST" 2>/dev/null || true
}
trap cleanup EXIT

git -C "$ROOT" worktree add -q --detach "$WT_PRE" "$PRE_FULL"
git -C "$ROOT" worktree add -q --detach "$WT_POST" "$POST_FULL"

capture() {
  local label=$1
  local wt=$2
  local outdir=$OUT/$label
  rm -f "$outdir"/*

  git -C "$wt" rev-parse HEAD > "$outdir/.SHA"
  echo "  $label  ($(git -C "$wt" rev-parse --short HEAD))"

  # Validators may exit non-zero on errors; capture rather than abort.
  set +e
  for s in validate validate-research; do
    (cd "$wt" && python3 "scripts/$s.py") > "$outdir/$s.txt" 2> "$outdir/$s.err"
    echo $? > "$outdir/$s.exit"
  done
  (cd "$wt" && python3 scripts/review-coverage.py --all) \
    > "$outdir/review-coverage.txt" 2> "$outdir/review-coverage.err"
  echo $? > "$outdir/review-coverage.exit"
  set -e
}

echo "Capturing validator output —"
capture pre "$WT_PRE"
capture post "$WT_POST"

echo
echo "=========================================="
echo " behavior-diff: $PRE_SHORT → $POST_SHORT"
echo "=========================================="

# Per-script summary + diff disposition. Each script's output is
# considered identical, differs-by-formatting, or differs-substantively
# based on the unified-diff line count. The harness does not
# adjudicate — it reports; the contributor categorizes.
overall_clean=1
for s in validate validate-research review-coverage; do
  echo
  echo "--- $s ---"
  pre_exit=$(cat "$OUT/pre/$s.exit")
  post_exit=$(cat "$OUT/post/$s.exit")
  echo "exit:  pre=$pre_exit  post=$post_exit"

  if diff -q "$OUT/pre/$s.txt" "$OUT/post/$s.txt" > /dev/null 2>&1; then
    echo "stdout: byte-identical"
  else
    overall_clean=0
    pre_lines=$(wc -l < "$OUT/pre/$s.txt")
    post_lines=$(wc -l < "$OUT/post/$s.txt")
    diff_lines=$(diff "$OUT/pre/$s.txt" "$OUT/post/$s.txt" | wc -l)
    echo "stdout: differs (pre=$pre_lines, post=$post_lines, unified-diff=$diff_lines lines)"
    echo "        captures: $OUT/{pre,post}/$s.txt"
  fi

  if ! diff -q "$OUT/pre/$s.err" "$OUT/post/$s.err" > /dev/null 2>&1; then
    overall_clean=0
    echo "stderr: differs — captures: $OUT/{pre,post}/$s.err"
  fi
done

echo
echo "=========================================="
if [ $overall_clean -eq 1 ]; then
  echo " RESULT: byte-identical across all three orchestrators."
  echo " Behavioral equivalence confirmed beyond the corpus 0/0 pass."
else
  echo " RESULT: differences captured — review per-script diffs."
  echo " Categorize each diff as: (a) intentional formatting (check_name"
  echo " field, banner change, message wording), (b) corpus-state delta"
  echo " between SHAs, or (c) potential behavior regression."
fi
echo "=========================================="
echo "Baseline captures preserved under $OUT/"
