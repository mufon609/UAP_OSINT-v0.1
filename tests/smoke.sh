#!/usr/bin/env bash
# Fixture-based smoke tests.
#
# For every node-type + archetype/kind combination, scaffold via new.py,
# validate via validate.py, delete. Also scaffold a research artifact
# for the document fixture and validate it via validate-research.py.
#
# Catches regressions in:
#   - new.py scaffolding (template rendering, conditional-block
#     filtering by --archetype / --kind, placeholder substitution)
#   - meta/templates/*.md content (if a required section is removed
#     from a template, the scaffolded node fails validation here — the
#     check_governance_files() pass catches template frontmatter drift,
#     but only THIS test catches body-section drift)
#   - validate.py's required-section / archetype-conditional /
#     kind-conditional enforcement
#   - research-scaffold.py and validate-research.py on an empty-
#     content artifact
#
# Runtime: seconds. Intended for pre-commit / CI.
# Exits 0 if every case passes; 1 if any fail.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

pass=0
fail=0
failures=()
created_files=()

cleanup() {
    for f in "${created_files[@]}"; do
        [ -f "$f" ] && rm -f "$f"
    done
}
trap cleanup EXIT

test_scaffold() {
    local label="$1"; shift
    local out
    out="$(python3 scripts/new.py "$@" 2>&1)"
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("$label — scaffold failed (rc=$rc): $(echo "$out" | head -1)")
        fail=$((fail + 1))
        return
    fi

    # new.py's first line of success output is "✓ Created {path}"
    local file_path
    file_path=$(printf '%s\n' "$out" | awk '/^✓ Created/ {print $3; exit}')
    if [ -z "$file_path" ]; then
        failures+=("$label — couldn't parse scaffold path from new.py output")
        fail=$((fail + 1))
        return
    fi
    created_files+=("$file_path")

    out="$(python3 scripts/validate.py "$file_path" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("$label — validate.py failed on scaffold: $(echo "$out" | grep ERROR | head -2)")
        fail=$((fail + 1))
        return
    fi

    pass=$((pass + 1))
}

# --- person: all 4 archetypes ---
test_scaffold "person eyewitness"         person --archetype eyewitness         --slug __smoke-person-eyewitness
test_scaffold "person whistleblower"      person --archetype whistleblower      --slug __smoke-person-whistleblower
test_scaffold "person institutional-actor" person --archetype institutional-actor --slug __smoke-person-iact
test_scaffold "person reporter"           person --archetype reporter           --slug __smoke-person-reporter

# --- organization: all 3 kinds ---
test_scaffold "org gov"            organization --kind gov            --slug __smoke-org-gov
test_scaffold "org gov-contractor" organization --kind gov-contractor --slug __smoke-org-contractor
test_scaffold "org private"        organization --kind private        --slug __smoke-org-private

# --- document: both kinds ---
test_scaffold "document gov-doc"     document --kind gov-doc     --form testimony --slug __smoke-doc-gov
test_scaffold "document non-gov-doc" document --kind non-gov-doc --form article   --slug __smoke-doc-non-gov

# --- event: both kinds ---
test_scaffold "event hearing"   event --kind hearing   --slug __smoke-event-hearing
test_scaffold "event encounter" event --kind encounter --slug __smoke-event-encounter

# --- transcript: both kinds ---
test_scaffold "transcript hearing"   transcript --kind hearing   --slug __smoke-trans-hearing
test_scaffold "transcript interview" transcript --kind interview --slug __smoke-trans-interview

# --- single-variant types ---
test_scaffold "news"     news     --slug __smoke-news
test_scaffold "book"     book     --slug __smoke-book
test_scaffold "location" location --slug __smoke-location
test_scaffold "finding"  finding  --slug __smoke-finding --entities "/people/a,/organizations/b,/events/c"

# --- research artifact (uses the gov-doc fixture as target) ---
artifact_out="$(python3 scripts/research-scaffold.py --target documents/__smoke-doc-gov 2>&1)"
rc=$?
if [ "$rc" -ne 0 ]; then
    failures+=("research-scaffold — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
    fail=$((fail + 1))
else
    created_files+=("research/__smoke-doc-gov.yaml")
    artifact_out="$(python3 scripts/validate-research.py research/__smoke-doc-gov.yaml --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research artifact — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
fi

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
