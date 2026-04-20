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

# Smoke-fixture state that outlives a single file — manifest backup path
# and fixture source-file path. Restored/removed in cleanup. Initialized
# empty so `set -u` is satisfied if cleanup fires before these are set.
MANIFEST_BACKUP=""
FIXTURE_SRC_PATH=""

cleanup() {
    # Restore manifest if we staged a backup
    if [ -n "$MANIFEST_BACKUP" ] && [ -f "$MANIFEST_BACKUP" ]; then
        mv "$MANIFEST_BACKUP" sources/manifest.yaml
    fi
    # Remove the fixture source file if we placed one
    if [ -n "$FIXTURE_SRC_PATH" ] && [ -f "$FIXTURE_SRC_PATH" ]; then
        rm -f "$FIXTURE_SRC_PATH"
    fi
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

# --- research artifact: transcript-kind dispatch ---
# Scaffolder must emit material_differences: [] for transcript.hearing
# and NOT emit it for transcript.other. Enforced implicitly by validate-
# research.py's kind-conditional rule: missing-required fires on hearing
# if absent; absent-on-other-kind fires on other if present. So a clean
# validate pass on an empty scaffold is a pass for the kind dispatch.
for tk_target in "transcripts/__smoke-trans-hearing" "transcripts/__smoke-trans-other"; do
    artifact_out="$(python3 scripts/research-scaffold.py --target "$tk_target" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $tk_target — failed (rc=$rc): $(echo "$artifact_out" | head -1)")
        fail=$((fail + 1))
        continue
    fi
    tk_slug="${tk_target##*/}"
    created_files+=("research/$tk_slug.yaml")
    artifact_out="$(python3 scripts/validate-research.py "research/$tk_slug.yaml" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("research-scaffold $tk_target — validate-research.py failed: $(echo "$artifact_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# --- cross-artifact material_differences fixture ---
# Exercises the F.3a cross-artifact quote_ref resolver end-to-end:
#   - check_material_differences (structural + divergence_class enum)
#   - resolve_cross_artifact_quote_ref (written_ref → documents/__smoke-xdoc:q1)
#   - intra-artifact oral_ref resolution (within transcript artifact)
#   - check #16 pooled-source drift scan on material_differences[].note
#
# Stands up temporary state:
#   - sources/government/__smoke-xfixture.txt (fixture primary source)
#   - matching archived manifest entry with real sha256
#   - __smoke-xdoc document node (new.py scaffold)
#   - __smoke-xtrans-hearing transcript node (new.py scaffold)
#   - research/__smoke-xdoc.yaml (cp from tests/smoke-fixtures/)
#   - research/__smoke-xtrans-hearing.yaml (cp from tests/smoke-fixtures/)
# All state is restored/removed on trap cleanup.

MANIFEST_BACKUP="/tmp/__smoke-manifest-backup-$$.yaml"
FIXTURE_SRC_PATH="sources/government/__smoke-xfixture.txt"

cp sources/manifest.yaml "$MANIFEST_BACKUP"
cp tests/smoke-fixtures/source.txt "$FIXTURE_SRC_PATH"
FIXTURE_SHA=$(sha256sum "$FIXTURE_SRC_PATH" | awk '{print $1}')

cat >> sources/manifest.yaml <<EOF
- url: https://example.invalid/__smoke-xfixture.txt
  format: txt
  status: archived
  path: government/__smoke-xfixture.txt
  sha256: $FIXTURE_SHA
  note: smoke-fixture — auto-created/removed by tests/smoke.sh
EOF

# Scaffold the target nodes the fixture artifacts point at
xdoc_out="$(python3 scripts/new.py document --kind gov-doc --form testimony --slug __smoke-xdoc 2>&1)"
xdoc_rc=$?
xdoc_path=$(printf '%s\n' "$xdoc_out" | awk '/^✓ Created/ {print $3; exit}')
if [ "$xdoc_rc" -ne 0 ] || [ -z "$xdoc_path" ]; then
    failures+=("cross-artifact doc node scaffold — failed: $(echo "$xdoc_out" | head -1)")
    fail=$((fail + 1))
else
    created_files+=("$xdoc_path")
fi

xtrans_out="$(python3 scripts/new.py transcript --kind hearing --slug __smoke-xtrans-hearing 2>&1)"
xtrans_rc=$?
xtrans_path=$(printf '%s\n' "$xtrans_out" | awk '/^✓ Created/ {print $3; exit}')
if [ "$xtrans_rc" -ne 0 ] || [ -z "$xtrans_path" ]; then
    failures+=("cross-artifact trans node scaffold — failed: $(echo "$xtrans_out" | head -1)")
    fail=$((fail + 1))
else
    created_files+=("$xtrans_path")
fi

# Install fixture research artifacts
cp tests/smoke-fixtures/cross-artifact-doc.yaml research/__smoke-xdoc.yaml
cp tests/smoke-fixtures/cross-artifact-trans.yaml research/__smoke-xtrans-hearing.yaml
created_files+=("research/__smoke-xdoc.yaml")
created_files+=("research/__smoke-xtrans-hearing.yaml")

# Validate both — the transcript artifact's clean pass is the end-to-end
# resolver check (written_ref resolves to a real quote in the doc artifact;
# oral_ref resolves within self; note matches pooled source vocabulary).
for xartifact in "research/__smoke-xdoc.yaml" "research/__smoke-xtrans-hearing.yaml"; do
    cross_out="$(python3 scripts/validate-research.py "$xartifact" --quiet 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("cross-artifact $xartifact — validate-research.py failed: $(echo "$cross_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# Render both via build-from-research.py — the transcript pass is the
# F.3b renderer end-to-end check (Publication Record / Summary /
# Speakers / Key Passages / Material Differences with cross-artifact
# excerpt rendering all run; post-build validate.py confirms structural
# + verbatim-quote integrity on the regenerated node).
for xartifact in "research/__smoke-xdoc.yaml" "research/__smoke-xtrans-hearing.yaml"; do
    cross_out="$(python3 scripts/build-from-research.py "$xartifact" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("cross-artifact $xartifact — build-from-research.py failed: $(echo "$cross_out" | grep ERROR | head -2)")
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done

# Review-coverage on both — Coverage / Boundary / Stub-linking / OQ
# dedup. Boundary is the strongest check: re-runs build-from-research
# dry-run and diffs against the just-rendered node; any non-determinism
# in the renderer surfaces here.
for xartifact in "research/__smoke-xdoc.yaml" "research/__smoke-xtrans-hearing.yaml"; do
    cross_out="$(python3 scripts/review-coverage.py "$xartifact" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        failures+=("cross-artifact $xartifact — review-coverage.py failed: $(echo "$cross_out" | grep ERROR | head -2)")
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
