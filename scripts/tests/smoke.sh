#!/usr/bin/env bash
# Fixture-based smoke tests.
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
# Runtime: seconds. Intended for pre-commit / CI.
# Exits 0 if every case passes; 1 if any fail.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
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

# --- document: both kinds, several doc_forms (article + book +
#     social-post exercise the non-gov-doc paths; book exercises the
#     archival_status-required conditional) ---
test_scaffold "document gov-doc"         document --kind gov-doc     --form testimony --slug __smoke-doc-gov
test_scaffold "document non-gov-doc"     document --kind non-gov-doc --form article   --slug __smoke-doc-non-gov
test_scaffold "document book"            document --kind non-gov-doc --form book      --archival-status excerpts-only --slug __smoke-doc-book
test_scaffold "document social-post"     document --kind non-gov-doc --form social-post --slug __smoke-doc-social

# --- event: both kinds ---
test_scaffold "event hearing"   event --kind hearing   --slug __smoke-event-hearing
test_scaffold "event encounter" event --kind encounter --slug __smoke-event-encounter

# --- transcript: both kinds. The `other` fixture exercises
#     --derived-from pointing to the already-scaffolded doc-gov fixture
#     so the frontmatter-pointer existence check has a resolves-clean
#     case. ---
test_scaffold "transcript hearing" transcript --kind hearing --slug __smoke-trans-hearing
test_scaffold "transcript other"   transcript --kind other   --source-medium podcast --derived-from /documents/__smoke-doc-gov --slug __smoke-trans-other

# --- media: all 4 kinds + a derivative to exercise the DERIVATIVE
#     conditional-block filter and the derivation_of → Media Versioning
#     validator check ---
test_scaffold "media photo"         media --kind photo         --slug __smoke-media-photo
test_scaffold "media video"         media --kind video         --slug __smoke-media-video
test_scaffold "media audio"         media --kind audio         --slug __smoke-media-audio
test_scaffold "media imagery-other" media --kind imagery-other --slug __smoke-media-imagery
test_scaffold "media derivative"    media --kind video --derivation-of /media/__smoke-media-video --slug __smoke-media-deriv

# --- single-variant types ---
test_scaffold "location"      location      --slug __smoke-location
test_scaffold "finding"       finding       --slug __smoke-finding
test_scaffold "investigation" investigation --slug __smoke-investigation --question "Does the test question resolve?"

# --- research artifact (uses the gov-doc fixture as target) ---
artifact_out="$(python3 scripts/research-scaffold.py --target documents/__smoke-doc-gov 2>&1)"
rc=$?
if [ "$rc" -ne 0 ]; then
    failures+=("research-scaffold — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
    fail=$((fail + 1))
else
    created_files+=("meta/research/__smoke-doc-gov.yaml")
    artifact_out="$(python3 scripts/validate-research.py meta/research/__smoke-doc-gov.yaml --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research artifact — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
fi

# --- research artifact: media-type dispatch ---
# Scaffolder must emit media_versioning: [] on every media artifact
# regardless of kind. The validator's media-type conditional requires
# the key present; a clean validate pass on an empty scaffold confirms
# both the scaffolder and the conditional dispatch. Each fixture then
# exercises the renderer pipeline: build-from-research regenerates the
# node body, validate.py confirms structural integrity, review-coverage
# runs Coverage / Boundary / Stub-linking / Description-drift. The
# derivative fixture surfaces the validate-research warn for empty
# media_versioning + derivation_of set (non-blocking signal).
for m_target in "media/__smoke-media-photo" "media/__smoke-media-video" "media/__smoke-media-audio" "media/__smoke-media-imagery" "media/__smoke-media-deriv"; do
    artifact_out="$(python3 scripts/research-scaffold.py --target "$m_target" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $m_target — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
        fail=$((fail + 1))
        continue
    fi
    m_slug="${m_target##*/}"
    created_files+=("meta/research/$m_slug.yaml")
    artifact_out="$(python3 scripts/validate-research.py "meta/research/$m_slug.yaml" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $m_target — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    # Exercise the renderer pipeline
    artifact_out="$(python3 scripts/build-from-research.py "meta/research/$m_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("build-from-research $m_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    artifact_out="$(python3 scripts/review-coverage.py "meta/research/$m_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("review-coverage $m_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# --- research artifact: transcript scaffold ---
# Both transcript kinds (hearing, other) scaffold the same sections:
# description / primary_sources / document_intrinsic / context_extrinsic
# / quotes / speakers / entities_referenced / naming_quirks. A clean
# validate pass on an empty scaffold is the pass criterion.
for tk_target in "transcripts/__smoke-trans-hearing" "transcripts/__smoke-trans-other"; do
    artifact_out="$(python3 scripts/research-scaffold.py --target "$tk_target" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $tk_target — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
        fail=$((fail + 1))
        continue
    fi
    tk_slug="${tk_target##*/}"
    created_files+=("meta/research/$tk_slug.yaml")
    artifact_out="$(python3 scripts/validate-research.py "meta/research/$tk_slug.yaml" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $tk_target — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# --- research artifact: location dispatch ---
# Scaffolder emits ownership_timeline: [], top_scope_activity: [],
# location_relationships: [] on every location artifact. Validator
# enforces type-conditional presence (locations have no kinds).
# Renderer pipeline is exercised end-to-end: build-from-research
# emits the Overview fact-table + Description + Ownership Timeline +
# {display_name}-Scope Activity + Relationships with Confirmed /
# Flagged split.
for loc_target in "locations/__smoke-location"; do
    artifact_out="$(python3 scripts/research-scaffold.py --target "$loc_target" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $loc_target — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
        fail=$((fail + 1))
        continue
    fi
    loc_slug="${loc_target##*/}"
    created_files+=("meta/research/$loc_slug.yaml")
    artifact_out="$(python3 scripts/validate-research.py "meta/research/$loc_slug.yaml" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $loc_target — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    # Exercise the renderer pipeline
    artifact_out="$(python3 scripts/build-from-research.py "meta/research/$loc_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("build-from-research $loc_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    artifact_out="$(python3 scripts/review-coverage.py "meta/research/$loc_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("review-coverage $loc_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# --- research artifact: organization-kind dispatch ---
# Scaffolder emits key_personnel: [] and org_relationships: [] on
# every organization artifact, and contracts: [] only when
# kind == gov-contractor. Validator enforces the kind-conditional
# contracts presence (missing on gov-contractor errors;
# present-on-other-kind errors). Renderer pipeline is exercised
# per-kind: Primary Contracts emits on gov-contractor only; all three
# kinds emit Overview / Key Personnel (with leadership_class
# sub-grouping) / Key Passages / Relationships.
for ok_target in "organizations/__smoke-org-gov" "organizations/__smoke-org-contractor" "organizations/__smoke-org-private"; do
    artifact_out="$(python3 scripts/research-scaffold.py --target "$ok_target" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $ok_target — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
        fail=$((fail + 1))
        continue
    fi
    ok_slug="${ok_target##*/}"
    created_files+=("meta/research/$ok_slug.yaml")
    artifact_out="$(python3 scripts/validate-research.py "meta/research/$ok_slug.yaml" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $ok_target — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    # Exercise the renderer pipeline
    artifact_out="$(python3 scripts/build-from-research.py "meta/research/$ok_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("build-from-research $ok_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    artifact_out="$(python3 scripts/review-coverage.py "meta/research/$ok_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("review-coverage $ok_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# --- research artifact: finding + investigation dispatch ---
# Scaffolder emits pattern_statement: "" and establishes / does_not_establish
# / contradictions / timeline / quotes empty lists on finding artifacts;
# hypotheses / cited_findings / hypothesis_evaluation / open_questions
# / counter_evidence / closure_path / resolution_history empty lists +
# best_current_answer: {} on investigation artifacts. Validator
# enforces type-conditional presence; renderer pipeline exercises the
# F.7 finding + investigation body composition.
for syn_target in "findings/__smoke-finding" "investigations/__smoke-investigation"; do
    artifact_out="$(python3 scripts/research-scaffold.py --target "$syn_target" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $syn_target — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
        fail=$((fail + 1))
        continue
    fi
    syn_slug="${syn_target##*/}"
    created_files+=("meta/research/$syn_slug.yaml")
    artifact_out="$(python3 scripts/validate-research.py "meta/research/$syn_slug.yaml" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $syn_target — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
    # Exercise the renderer pipeline
    artifact_out="$(python3 scripts/build-from-research.py "meta/research/$syn_slug.yaml" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("build-from-research $syn_target — failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

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
