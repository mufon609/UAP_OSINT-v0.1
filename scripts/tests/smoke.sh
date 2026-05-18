#!/usr/bin/env bash
# Fixture-based smoke tests — parallelized.
#
# For every node-type + archetype / kind combination, scaffold via
# new.py, validate via validate.py, then delete. Also scaffold a
# research artifact for each fixture and exercise
# validate-research.py + build-from-research.py + review-coverage.py
# where the renderer ships.
#
# Catches regressions in:
#   - new.py scaffolding (template rendering, conditional-block
#     filtering by --archetype / --kind, placeholder substitution)
#   - meta/templates/*.md body content (the governance-files check
#     catches template frontmatter drift; only this test catches
#     body-section drift)
#   - validate.py's required-section / archetype-conditional /
#     kind-conditional enforcement
#   - research-scaffold.py + validate-research.py on empty-content
#     artifacts; build-from-research.py + review-coverage.py for the
#     types whose renderer ships
#
# Concurrency model: independent fixtures run in parallel via `&` +
# `wait`. Three phases sequenced by data dependency:
#   Phase 1 — 21 independent scaffolds (no inter-deps)
#   Phase 2 — 2 dependent scaffolds (transcript-other → doc-gov;
#             media-deriv → media-video)
#   Phase 3 — all research-artifact pipelines (independent per artifact)
# Each backgrounded job writes its result to a per-job file in a
# tempdir; the parent aggregates after each phase's `wait`. Variable
# mutations don't cross subshell boundaries in bash, so pass/fail
# counters can't be incremented inside a backgrounded function.
#
# Cleanup is pattern-based on the `__smoke-*` slug convention; fires
# on EXIT and at startup so a prior crashed run doesn't leave debris.
#
# Exits 0 if every case passes; 1 if any fail.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

RESULT_DIR="$(mktemp -d -t smoke-results.XXXXXX)"

cleanup_fixtures() {
    rm -f \
        people/__smoke-*.md \
        organizations/__smoke-*.md \
        documents/__smoke-*.md \
        events/__smoke-*.md \
        transcripts/__smoke-*.md \
        media/__smoke-*.md \
        locations/__smoke-*.md \
        findings/__smoke-*.md \
        investigations/__smoke-*.md \
        meta/research/__smoke-*.yaml
}

cleanup() {
    cleanup_fixtures
    [ -n "${RESULT_DIR:-}" ] && rm -rf "$RESULT_DIR"
}
trap cleanup EXIT

# Defensive pre-clean for any debris left by a prior crashed run.
cleanup_fixtures

# ─── Job helpers ────────────────────────────────────────────────────────
# Result-file format (one line per result file):
#   PASS|<label>
#   FAIL|<label>|<message>

run_scaffold() {
    local jobid="$1"; local label="$2"; shift 2
    local result_file="$RESULT_DIR/${jobid}.result"
    local out rc file_path
    out=$(python3 scripts/build/new.py "$@" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL|$label|scaffold failed (rc=$rc): $(echo "$out" | head -1)" > "$result_file"
        return
    fi
    file_path=$(printf '%s\n' "$out" | awk '/^✓ Created/ {print $3; exit}')
    if [ -z "$file_path" ]; then
        echo "FAIL|$label|couldn't parse scaffold path from new.py output" > "$result_file"
        return
    fi
    out=$(python3 scripts/build/validate.py "$file_path" --quiet 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL|$label|validate.py failed on scaffold: $(echo "$out" | grep ERROR | head -2)" > "$result_file"
        return
    fi
    echo "PASS|$label" > "$result_file"
}

run_research() {
    # Scaffold a research artifact for a target, then run validate-research
    # plus any of build / coverage requested via the steps string.
    # ``steps`` is a space-delimited subset of: validate build coverage.
    # Each step writes its own per-job result file.
    local jobid="$1"; local label="$2"; local target="$3"; local steps="$4"
    local result_prefix="$RESULT_DIR/${jobid}"
    local out rc slug artifact
    slug="${target##*/}"
    artifact="meta/research/${slug}.yaml"

    out=$(python3 scripts/build/research-scaffold.py --target "$target" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL|$label scaffold|research-scaffold failed (rc=$rc): $(echo "$out" | head -1)" \
            > "${result_prefix}-scaffold.result"
        return
    fi
    echo "PASS|$label scaffold" > "${result_prefix}-scaffold.result"

    out=$(python3 scripts/build/validate-research.py "$artifact" --quiet 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL|$label validate-research|validate-research failed: $(echo "$out" | grep ERROR | head -2)" \
            > "${result_prefix}-vr.result"
        return
    fi
    echo "PASS|$label validate-research" > "${result_prefix}-vr.result"

    if [[ " $steps " == *" build "* ]]; then
        out=$(python3 scripts/build/build-from-research.py "$artifact" 2>&1)
        rc=$?
        if [ "$rc" -ne 0 ]; then
            echo "FAIL|$label build-from-research|failed: $(echo "$out" | grep ERROR | head -2)" \
                > "${result_prefix}-build.result"
            return
        fi
        echo "PASS|$label build-from-research" > "${result_prefix}-build.result"
    fi

    if [[ " $steps " == *" coverage "* ]]; then
        out=$(python3 scripts/build/review-coverage.py "$artifact" 2>&1)
        rc=$?
        if [ "$rc" -ne 0 ]; then
            echo "FAIL|$label review-coverage|failed: $(echo "$out" | grep ERROR | head -2)" \
                > "${result_prefix}-cov.result"
            return
        fi
        echo "PASS|$label review-coverage" > "${result_prefix}-cov.result"
    fi
}

# ─── Phase 1: independent scaffolds ─────────────────────────────────────
# All 21 fixtures with no inter-deps. Forked in parallel.

run_scaffold p1 "person eyewitness"          person --archetype eyewitness          --slug __smoke-person-eyewitness &
run_scaffold p2 "person whistleblower"       person --archetype whistleblower       --slug __smoke-person-whistleblower &
run_scaffold p3 "person institutional-actor" person --archetype institutional-actor --slug __smoke-person-iact &
run_scaffold p4 "person reporter"            person --archetype reporter            --slug __smoke-person-reporter &

run_scaffold o1 "org gov"             organization --kind gov            --slug __smoke-org-gov &
run_scaffold o2 "org gov-contractor"  organization --kind gov-contractor --slug __smoke-org-contractor &
run_scaffold o3 "org private"         organization --kind private        --slug __smoke-org-private &

run_scaffold d1 "document gov-doc"      document --kind gov-doc     --form testimony   --slug __smoke-doc-gov &
run_scaffold d2 "document non-gov-doc"  document --kind non-gov-doc --form article     --slug __smoke-doc-non-gov &
run_scaffold d3 "document book"         document --kind non-gov-doc --form book --archival-status excerpts-only --slug __smoke-doc-book &
run_scaffold d4 "document social-post"  document --kind non-gov-doc --form social-post --slug __smoke-doc-social &

run_scaffold e1 "event hearing"    event --kind hearing   --slug __smoke-event-hearing &
run_scaffold e2 "event encounter"  event --kind encounter --slug __smoke-event-encounter &

run_scaffold t1 "transcript hearing" transcript --kind hearing --slug __smoke-trans-hearing &

run_scaffold m1 "media photo"         media --kind photo         --slug __smoke-media-photo &
run_scaffold m2 "media video"         media --kind video         --slug __smoke-media-video &
run_scaffold m3 "media audio"         media --kind audio         --slug __smoke-media-audio &
run_scaffold m4 "media imagery-other" media --kind imagery-other --slug __smoke-media-imagery &

run_scaffold s1 "location"       location      --slug __smoke-location &
run_scaffold s2 "finding"        finding       --slug __smoke-finding &
run_scaffold s3 "investigation"  investigation --slug __smoke-investigation --question "Does the test question resolve?" &

wait

# ─── Phase 2: dependent scaffolds ───────────────────────────────────────
# transcript-other points --derived-from at doc-gov; media-deriv points
# --derivation-of at media-video. Both Phase-1 prerequisites must exist
# on disk before these run. They don't depend on each other.

run_scaffold t2 "transcript other" \
    transcript --kind other --source-medium podcast \
    --derived-from /documents/__smoke-doc-gov \
    --slug __smoke-trans-other &
run_scaffold m5 "media derivative" \
    media --kind video --derivation-of /media/__smoke-media-video \
    --slug __smoke-media-deriv &

wait

# ─── Phase 3: research-artifact pipelines ───────────────────────────────
# Each operates on a distinct artifact file; all parallel.
# Steps cover the same matrix the prior sequential script ran:
#   - doc-gov: validate-research only
#   - transcripts (hearing + other): validate-research only
#   - media (all 5 kinds): validate-research + build + coverage
#   - location: validate-research + build + coverage
#   - organizations (all 3 kinds): validate-research + build + coverage
#   - finding + investigation: validate-research + build (no coverage —
#     review-coverage is reserved for entity nodes whose renderer ships
#     in the Phase III dispatch)

run_research rA  "doc-gov"         documents/__smoke-doc-gov                  "" &

run_research rM1 "media-photo"     media/__smoke-media-photo                  "build coverage" &
run_research rM2 "media-video"     media/__smoke-media-video                  "build coverage" &
run_research rM3 "media-audio"     media/__smoke-media-audio                  "build coverage" &
run_research rM4 "media-imagery"   media/__smoke-media-imagery                "build coverage" &
run_research rM5 "media-deriv"     media/__smoke-media-deriv                  "build coverage" &

run_research rT1 "trans-hearing"   transcripts/__smoke-trans-hearing          "" &
run_research rT2 "trans-other"     transcripts/__smoke-trans-other            "" &

run_research rL  "location"        locations/__smoke-location                 "build coverage" &

run_research rOg "org-gov"         organizations/__smoke-org-gov              "build coverage" &
run_research rOc "org-contractor"  organizations/__smoke-org-contractor       "build coverage" &
run_research rOp "org-private"     organizations/__smoke-org-private          "build coverage" &

run_research rF  "finding"         findings/__smoke-finding                   "build" &
run_research rI  "investigation"   investigations/__smoke-investigation       "build" &

wait

# ─── Aggregate results ──────────────────────────────────────────────────
pass=0
fail=0
failures=()

shopt -s nullglob
for f in "$RESULT_DIR"/*.result; do
    line=$(cat "$f")
    case "$line" in
        PASS\|*)
            pass=$((pass + 1)) ;;
        FAIL\|*)
            fail=$((fail + 1))
            failures+=("${line#FAIL|}") ;;
        *)
            fail=$((fail + 1))
            failures+=("$(basename "$f"): unparseable result line: $line") ;;
    esac
done
shopt -u nullglob

echo "======================================================================"
echo " Fixture smoke tests"
echo "======================================================================"
echo
echo "  Passed: $pass"
echo "  Failed: $fail"

if [ "$fail" -gt 0 ]; then
    echo
    echo "Failures:"
    for f in "${failures[@]}"; do
        echo "  - $f"
    done
    exit 1
fi

exit 0
