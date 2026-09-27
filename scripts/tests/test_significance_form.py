#!/usr/bin/env python3
"""Regression guard for the quote-significance-form check
(`scripts/checks/quote_significance_form.py`) and the passage-head renderer
(`scripts/build/renderers/_common.py`, `_render_passage_head`).

A quote's significance is its Key Passage heading: one sentence, at most
`quote_entry.significance_words_max` words; the analysis goes in `analysis`.
The pre-fix fixtures below are significances the corpus actually carried
before the sweep (a five-sentence Defense One panel heading, a two-sentence
DIRD title-page heading, a 41-word single sentence); each must ERROR. The
clean fixtures pin the false-positive guards: abbreviations, initials and
dotted acronyms (`U.S. Navy`, `Dr. Hal Puthoff`, `H. E. Puthoff`,
`et al. (2006)`, `No. 315`, `e.g. Boeing`) are not sentence breaks; exactly
the cap passes; a long multi-sentence `analysis` is never checked. The
renderer case pins the layout: heading, analysis paragraph, then the
blockquote. Fixtures only — no corpus artifact is read or written.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "build"))

from checks import quote_significance_form as ck  # noqa: E402
from renderers._common import _render_passage_head  # noqa: E402

CAP = 40
SCHEMA = {"types": {"research-artifact": {"quote_entry": {
    "significance_words_max": CAP}}}}


class _Ctx:
    def __init__(self, data):
        self.rel = "test"
        self.data = data
        self.schema = SCHEMA


def _q(**kw):
    base = {"id": "q1", "added_date": "2026-01-01", "text": "verbatim",
            "source": {"path": "news/x.html", "location": "¶2"}}
    base.update(kw)
    return base


def _issues(*quotes):
    return list(ck.check(_Ctx({"quotes": list(quotes)})))


def _errors(needle, *quotes):
    out = _issues(*quotes)
    ok = (bool(out) and all(i.level == "error" for i in out)
          and all(i.check_name == ck.CHECK_NAME for i in out)
          and any(needle in i.message for i in out))
    return ok, [i.message for i in out]


def _silent(*quotes):
    out = _issues(*quotes)
    return not out, [i.message for i in out]


CASES = []


def record(label, result):
    ok, detail = result
    CASES.append((label, ok, detail))


def run():
    # --- pre-fix fixtures: each errors -----------------------------------
    record("five-sentence panel heading", _errors("5 sentences", _q(
        significance=(
            "Holly's self-assessment of the U.S. influence-operations "
            "enterprise as \"weak, quite frankly\" — delivered at the SOF "
            "Week 2024 panel held May 9, 2024. The panel paired Holly with "
            "Daniel Kimmage ([`/people/daniel-kimmage`]). Documents IPMO's "
            "interagency reach beyond DoD. Defense One reporting is the only "
            "publicly accessible attestation. Defense One spells the "
            "surname \"Kimmidge\"."))))
    record("two-sentence title-page heading", _errors("2 sentences", _q(
        significance=(
            "Author identity redacted under (b)(6) inside the DIRD itself; "
            "preparing organization redacted under (b)(3):10 USC 424. "
            "Documents that the DIRD-13 attribution to Obousy is extrinsic, "
            "not internal."))))
    record("sentence after a closing quote", _errors("2 sentences", _q(
        significance='He calls it "my disclosure." 99% is "releasable".')))
    record("single sentence over the cap", _errors(
        f"41 words (cap {CAP})",
        _q(significance=" ".join(["word"] * 41))))
    record("person artifacts are checked too", _errors("2 sentences", _q(
        significance="Grusch names the program. He was read on in 2019.",
        observation_type="relayed", context="Hearing")))

    # --- clean fixtures: silent ------------------------------------------
    record("the reader-standard example", _silent(_q(significance=(
        "IPMO PWS §1.2 (April 2022): USD(I&S) is supported by DDI "
        "(Collection and Special Programs), which is supported by the "
        "Director of IPMO."))))
    record("exactly the cap", _silent(
        _q(significance=" ".join(["word"] * CAP))))
    record("abbreviations are not sentence breaks", _silent(
        _q(id="q1", significance="Fravor spent a decade in U.S. Navy "
           "squadrons before the 2004 intercept."),
        _q(id="q2", significance="Memo (2009): names Dr. Hal Puthoff and "
           "Dr. Kit Green as reviewers."),
        _q(id="q3", significance="Report (1976): the protocol was proposed "
           "by H. E. Puthoff and R. Targ at SRI."),
        _q(id="q4", significance="DIRD #20 (2010): cites the Fetz et al. "
           "(2006) implant."),
        _q(id="q5", significance="House amendment (2024): Amendment No. 315 "
           "to H.R. 8800 directs a briefing."),
        _q(id="q6", significance="Filing (2023): names a third party "
           "(e.g. Boeing) as the holder."),
    ))
    record("analysis is never checked", _silent(_q(
        significance="Defense One (May 24, 2024): Holly calls the "
                     "enterprise \"weak, quite frankly.\"",
        analysis=" ".join(["One sentence of analysis."] * 30))))
    record("missing or empty significance is silent", _silent(
        _q(id="q1"), _q(id="q2", significance="")))

    # --- renderer layout ---------------------------------------------------
    head = _render_passage_head(
        {"significance": "Source (2020): statement.", "analysis": "More.\n"},
        "Passage")
    record("analysis renders between heading and blockquote", (
        head == ["### Source (2020): statement.", "", "More.", ""], head))
    head = _render_passage_head({"significance": "Source (2020): x."},
                                "Passage")
    record("no analysis, no paragraph", (
        head == ["### Source (2020): x.", ""], head))
    record("fallback heading", (
        _render_passage_head({}, "Attestation") == ["### Attestation", ""],
        _render_passage_head({}, "Attestation")))


def main():
    print("=" * 70)
    print(" quote-significance-form regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (multi-sentence / over-cap "
          f"significances error; abbreviations, the cap itself and "
          f"analysis stay silent; analysis renders under the heading)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
