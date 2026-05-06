#!/usr/bin/env python3
"""Regression guard for the prose-drift STOPWORDS set in lib/_common.py.

The prose-drift check filters STOPWORDS before comparing prose tokens
to source tokens. STOPWORDS should contain function words (articles,
prepositions, auxiliaries, conjunctions, etc.) that carry no evidentiary
signal. Content words — even common ones — must NEVER be in STOPWORDS,
or they get filtered out of drift detection silently. A future
contributor adding "investigate" or "confirmed" thinking it's a function
word would weaken drift detection corpus-wide without surfacing a
warning anywhere.

This test guards against that class of regression by asserting:
  1. Structural shape: STOPWORDS is a set of lowercase non-empty strings.
  2. Content-word safety: no entry in the curated CONTENT_WORDS set
     (load-bearing English content words) appears in STOPWORDS.

Wired into the pre-commit gate so every commit verifies the constraint.
Cheap to run; no fixtures; no external dependencies.

If a deliberate addition to STOPWORDS happens to overlap with a current
CONTENT_WORDS entry, the resolution is one of:
  - The addition is wrong (the word IS content; pick a different fix).
  - CONTENT_WORDS itself needs updating with explicit justification
    (commit message + rationale comment in this file).
The default is "the addition is wrong" — burden of proof is on the
addition.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lib._common import STOPWORDS


# ---------------------------------------------------------------------------
# Curated content-word fixture.
#
# Each entry is a content-bearing word whose presence/absence in prose is
# evidentially meaningful — fabricating, dropping, or substituting any of
# these in synthesis prose vs. source is exactly the class of drift the
# prose-drift check exists to surface. Spans multiple semantic categories
# so any single accidental STOPWORDS addition trips at least one entry.
#
# Topic-neutral — corpus-specific terminology stays out so the test
# continues to hold across topic forks. The entries below are
# load-bearing for any primary-source investigation.
# ---------------------------------------------------------------------------

CONTENT_WORDS = {
    # Investigation / verification verbs — meaning is precisely what's
    # at stake in evidentiary contexts.
    "investigate", "investigated", "investigation",
    "confirm", "confirmed",
    "attest", "attested",
    "verify", "verified",
    "establish", "established",
    "corroborate", "corroborated",
    "cite", "cited",
    # Reporting / publication / declaration verbs.
    "report", "reported",
    "submit", "submitted",
    "publish", "published",
    "issue", "issued",
    "sign", "signed",
    "announce", "announced",
    "declare", "declared",
    "state", "stated",
    "describe", "described",
    # Institutional / role vocabulary (general; not corpus-specific).
    "agency", "office", "department",
    "director", "secretary", "official", "civilian",
    "intelligence",
    # Testimony / hearing / evidentiary language.
    "testify", "testified", "testimony",
    "hearing", "witness", "sworn", "oath",
    "evidence", "claim", "fact",
    # Provenance / archival vocabulary.
    "document", "documented",
    "archive", "archived",
    "primary", "source", "sources",
    # Common action verbs heavily used in evidentiary prose.
    "lead", "led", "leading",
    "direct", "directed",
    "approve", "approved",
    "create", "created",
    # Generic verbs — content, not function words. Filtering them
    # would mask paraphrase / word-form drift (took/take, took/taken,
    # said/stated reporting-verb substitutions).
    "said", "says", "say", "saying",
    "took", "take", "taking", "taken",
    "made", "make", "making",
    "got", "get", "getting",
    "went", "goes", "gone",
    "came", "come", "coming",
    # Cardinal numbers — counting drift ("one case" vs "three cases")
    # is evidentiary drift even when grammatically a determiner.
    "one", "two", "three",
    # Month name "May" lowercases to "may" and collides with the modal.
    # Filtering would mask month-attestation drift; the cost is rare
    # modal-may false positives on prose.
    "may",
}


def check_shape():
    """STOPWORDS must be a set of lowercase non-empty strings."""
    failures = []
    if not isinstance(STOPWORDS, set):
        failures.append(
            f"STOPWORDS must be a set (for O(1) membership); got {type(STOPWORDS).__name__}"
        )
        return failures
    for w in STOPWORDS:
        if not isinstance(w, str):
            failures.append(f"STOPWORDS entry not a string: {w!r}")
            continue
        if not w:
            failures.append("STOPWORDS contains empty string")
            continue
        if w != w.lower():
            failures.append(
                f"STOPWORDS entry has uppercase: {w!r} "
                "(prose-drift tokenizer lowercases before checking; "
                "uppercase entries silently never match)"
            )
    return failures


def check_no_content_word_filtered():
    """No CONTENT_WORDS entry may appear in STOPWORDS."""
    contaminated = sorted(CONTENT_WORDS & STOPWORDS)
    if not contaminated:
        return []
    return [
        "REGRESSION: content words found in STOPWORDS — drift detection "
        f"silently weakened for: {contaminated}. Either revert the "
        "addition (the word IS content; rewrite prose to use source "
        "vocabulary instead), or update CONTENT_WORDS in "
        "scripts/tests/test_stopwords.py with explicit justification "
        "for treating these as function words."
    ]


def main():
    print("=" * 70)
    print(" STOPWORDS regression test (lib/_common.py)")
    print("=" * 70)
    print()
    failures = check_shape() + check_no_content_word_filtered()
    if failures:
        print(f"  FAILED — {len(failures)} issue(s):")
        print()
        for f in failures:
            print(f"  - {f}")
        print()
        return 1
    print(
        f"  PASSED — STOPWORDS shape valid ({len(STOPWORDS)} entries); "
        f"{len(CONTENT_WORDS)} content words confirmed not filtered."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
