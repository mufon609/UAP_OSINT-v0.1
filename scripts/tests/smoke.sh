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

# --- document: both kinds + article + book doc_form (covers the post-news/book
#     collapse paths: article is the former `news` case, book is the former
#     `book` case with archival_status required) ---
test_scaffold "document gov-doc"         document --kind gov-doc     --form testimony --slug __smoke-doc-gov
test_scaffold "document non-gov-doc"     document --kind non-gov-doc --form article   --slug __smoke-doc-non-gov
test_scaffold "document book"            document --kind non-gov-doc --form book      --archival-status excerpts-only --slug __smoke-doc-book
test_scaffold "document social-post"     document --kind non-gov-doc --form social-post --slug __smoke-doc-social

# --- event: both kinds ---
test_scaffold "event hearing"   event --kind hearing   --slug __smoke-event-hearing
test_scaffold "event encounter" event --kind encounter --slug __smoke-event-encounter

# --- transcript: both kinds (hearing + other, where `other` covers the former
#     `interview` case and broader speech sources). The `other` fixture
#     exercises --derived-from pointing to the already-scaffolded doc-gov
#     fixture so the frontmatter-pointer existence check has a resolves-clean
#     case in the regression set. ---
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
test_scaffold "location" location --slug __smoke-location
test_scaffold "finding"  finding  --slug __smoke-finding --entities "/people/a,/organizations/b,/events/c"

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
# regardless of kind (photo / video / audio / imagery-other). The
# validator's media-type conditional requires the key present; a clean
# validate pass on an empty scaffold confirms (a) the scaffolder adds
# the section and (b) the validator's conditional block fires correctly.
# Exercises both canonical and derivative node scaffolds — the
# conditional-present rule doesn't gate on derivation_of, only on
# target_node type. The F.4b renderer path is then exercised for each
# artifact: build-from-research regenerates the node body, post-build
# validate.py confirms structural integrity, review-coverage runs the
# four checks (Coverage / Boundary / Stub-linking / Description-drift).
# Derivative artifact surfaces the validate-research warn for empty
# media_versioning + derivation_of set (non-blocking — contributor
# review signal).
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
    # Exercise F.4b renderer path
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
# Both transcript kinds (hearing, other) scaffold the same sections
# post-Material-Differences elimination: description / primary_sources /
# document_intrinsic / context_extrinsic / quotes / claims / speakers /
# entities_referenced / naming_quirks. A clean validate
# pass on an empty scaffold is the pass criterion.
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

# --- research artifact: location dispatch (F.6a + F.6b) ---
# Scaffolder must emit ownership_timeline: [], uap_scope_activity: [],
# and location_relationships: [] on every location artifact. Validator
# enforces the type-conditional presence: missing-required fires on
# location artifacts if absent; absent-on-other-type fires on non-
# location artifacts if present. No kind-conditional extensions (location
# has no kinds).
#
# F.6b extends the fixture to exercise the full renderer pipeline:
# build-from-research regenerates the node body (Overview fact-table
# from document_intrinsic location keys + Description + Ownership
# Timeline + UAP-Scope Activity + Relationships with Confirmed/Flagged
# split). Post-build validate.py confirms structural integrity;
# review-coverage runs the four checks (Coverage / Boundary /
# Stub-linking / Description-drift).
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
    # Exercise F.6b renderer path
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

# --- research artifact: organization-kind dispatch (F.5a + F.5b) ---
# Scaffolder must emit key_personnel: [] and org_relationships: [] on
# every organization artifact regardless of kind, and emit contracts: []
# only when kind == gov-contractor. Validator enforces the kind-
# conditional contracts presence: missing-required fires on gov-
# contractor if absent; absent-on-other-kind fires on gov or private if
# present.
#
# F.5b extends this to the full renderer pipeline: build-from-research
# regenerates the node body per-kind (Primary Contracts section emits
# on gov-contractor only; all three kinds emit the Overview fact-table,
# Key Personnel with leadership_class sub-grouping, Key Passages, and
# org_relationships-sourced Relationships). Post-build validate.py
# confirms structural integrity; review-coverage runs the four checks
# (Coverage / Boundary / Stub-linking / Description-drift).
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
    # Exercise F.5b renderer path
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
