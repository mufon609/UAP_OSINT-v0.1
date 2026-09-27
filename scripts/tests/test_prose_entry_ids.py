#!/usr/bin/env python3
"""Regression guard for the prose-entry-ID checks
(`scripts/checks/quote_prose_entry_ids.py`, `synthesis_prose_entry_ids.py`,
`link_prose_entry_ids.py`; shared scanner `scripts/checks/_entry_id_prose.py`).

Prose names the source, never an internal entry ID. The pre-fix fixtures
below are strings the corpus actually carried before the sweep (a quote
significance citing FOIA rollout emails by testimony-quote IDs, naming-quirk
and timeline locations ending "(q97, q98)", a cross-artifact "vc2 in the
Grusch artifact", a slug-form quote id); each must ERROR, from exactly the
check whose phase owns the field. The clean fixtures pin the false-positive
guards: a source's own uppercase labels (QFR "Q7", Record page "H5120",
hypothesis "H1"), ID-typed pointer fields, verbatim payload, machine-stamped
primary_sources records, and paths / URLs / link wraps are never flagged.
Fixtures only — no corpus artifact is read or written.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import (  # noqa: E402
    link_prose_entry_ids,
    quote_prose_entry_ids,
    synthesis_prose_entry_ids,
)

CHECKS = {
    "quote": quote_prose_entry_ids,
    "synthesis": synthesis_prose_entry_ids,
    "link": link_prose_entry_ids,
}


class _Ctx:
    def __init__(self, data):
        self.rel = "test"
        self.data = data


def _issues(data):
    """{check key: [messages]} across the phase dispatches."""
    return {k: [i.message for i in mod.check(_Ctx(data))]
            for k, mod in CHECKS.items()}


def _only(data, key, *needles):
    """True iff exactly one check (``key``) fires, and every needle appears
    in its messages. All issues must be errors."""
    out = _issues(data)
    levels = {i.level for mod in CHECKS.values() for i in mod.check(_Ctx(data))}
    others = [k for k, v in out.items() if v and k != key]
    joined = " ".join(out[key])
    return (bool(out[key]) and not others and levels == {"error"}
            and all(n in joined for n in needles)), out


def _silent(data):
    out = _issues(data)
    return not any(out.values()), out


CASES = []


def record(label, result):
    ok, detail = result if isinstance(result, tuple) else (result, "")
    CASES.append((label, ok, detail))


def _q(**kw):
    base = {"id": "q1", "added_date": "2026-01-01",
            "text": "verbatim", "source": {"path": "news/x.html",
                                           "location": "¶2"}}
    base.update(kw)
    return base


def run():
    # --- pre-fix fixtures: each errors from the owning phase only ---------
    record("quote significance citing emails by testimony-quote IDs (extract)",
           _only({"quotes": [_q(significance=(
               "The FOIA 24-F-0894 rollout emails (q39, q40) show the "
               "release was coordinated"))]}, "quote", "'q39'", "'q40'"))
    record("slash-joined IDs both flagged", _only(
        {"quotes": [_q(significance="Pairs with q39/q40 on the same page")]},
        "quote", "'q39'", "'q40'"))
    record("quote location parenthetical (extract)", _only(
        {"quotes": [_q(source={"path": "news/x.html",
                               "location": "¶ The Staff Officer V will support (q97, q98)"})]},
        "quote", "'q97'", "'q98'"))
    record("slug-form quote id (extract)", _only(
        {"quotes": [_q(significance=(
            "beyond the provenance (already captured in q-lifting-payloads-task)"))]},
        "quote", "q-lifting-payloads-task"))
    record("naming-quirk location 'quoted in q39' (link)", _only(
        {"naming_quirks": [{"id": "nq4", "observed": "HQ0208",
                            "location": "FPDS entry P00008, quoted in q39; the "
                                        "FPDS record does not expand it"}]},
        "link", "naming_quirks[0 ('nq4')].location", "'q39'"))
    record("timeline location range 'q130–q134' (link)", _only(
        {"timeline": [{"id": "t33", "date": "2026-01-01", "event": "x",
                       "source": {"path": "news/x.html",
                                  "location": "¶ They declined to disclose (q130–q134)"}}]},
        "link", "'q130'", "'q134'"))
    record("hyphen-joined range 'q21-q23' (link)", _only(
        {"timeline": [{"id": "t17", "date": "1973-02-22", "event":
                       "page-1 byline places Targ at SRI (q21-q23)"}]},
        "link", "'q21'", "'q23'"))
    record("timeline event citing a naming quirk (link)", _only(
        {"timeline": [{"id": "t12a", "date": "2004", "event":
                       "Radar track reported (nq4 disputed)."}]},
        "link", "'nq4'"))
    record("cross-artifact 'vc2 in the Grusch artifact' (organize)", _only(
        {"description": "cited as vc2 in the Grusch artifact Vouching Chain"},
        "synthesis", "'vc2'"))
    record("finding establishes bullet 'q1 ($10,160,000)' (organize)", _only(
        {"establishes": ["Fiscal year triangulates across q1 ($10,160,000) "
                         "and q2 (approximately $10 million)."]},
        "synthesis", "establishes[0]", "'q1'", "'q2'"))
    record("investigation text 'per F2's c2 contradiction' (organize)", _only(
        {"hypothesis_evaluation": [{"hypothesis_id": "h3", "status": "open",
                                    "text": "The update (per F2's c2 contradiction) reports",
                                    "sources": []}]},
        "synthesis", "'c2'"))
    record("person significance citing affiliation / program entries", _only(
        {"quotes": [_q(significance="tightens affiliation a1 and program_involvement p1 / p4")]},
        "quote", "'a1'", "'p1'", "'p4'"))
    record("artifact's own novel prefix is picked up", _only(
        {"widgets": [{"id": "zz1"}], "description": "see zz1"},
        "synthesis", "'zz1'"))

    # --- clean fixtures: the same facts named by source ---------------------
    record("fixed prose naming sources is clean", _silent({
        "description": "Named in Grusch's Vouching Chain entry for the 2023 "
                       "ICIG complaint.",
        "quotes": [_q(significance="The FOIA 24-F-0894 rollout emails of "
                                   "2024-03-08 show the release was coordinated")],
        "naming_quirks": [{"id": "nq4", "observed": "HQ0208", "location":
                           "FPDS HQ003424C0046 entry modNumber P00008; the FPDS "
                           "record does not expand it"}],
        "timeline": [{"id": "t33", "date": "2026-01-01", "event": "x",
                      "source": {"path": "news/x.html",
                                 "location": "¶ They declined to disclose"}}],
    }))
    record("source labels and ordinary tokens are not IDs", _silent({
        "description": "QFR Q7 and Q1 responses; Record page H5120; H1 and H2 "
                       "hypotheses; Q4 FY2011; p. 3, ¶1; (b)(6); a 480p mp4; "
                       "SEC. 1746(f)(6); H2O; T1 relaxation; F-35; a "
                       "sec-q3 label and a q3-report file stem.",
    }))
    record("ID-typed pointer fields are exempt", _silent({
        "quotes": [_q(superseded_by="q2", contradicted_by="q3",
                      corroborated_by=["q4"], speaker_id="s1")],
        "contradictions": [{"id": "c1", "question": "How far?",
                            "positions": [{"evidence_id": "q1", "position": "170 m"}]}],
        "hypothesis_evaluation": [{"hypothesis_id": "h1", "status": "open",
                                   "text": "Bears on H1.", "sources": [
                                       {"entity_path": "/people/x", "anchor": "q24",
                                        "description": "The subject's 2023 testimony."}]}],
        "counter_evidence": [{"id": "ce1", "against_hypothesis_id": "h2",
                              "text": "Against H2.", "sources": []}],
    }))
    record("verbatim payload and machine stamps are exempt", _silent({
        "quotes": [_q(text="Exhibit q3 and item t8 as printed")],
        "naming_quirks": [{"id": "nq1", "observed": "q3", "location": "p. 2"}],
        "records_sought": [{"id": "rs1", "identifiers": [{"value": "q7"}]}],
        "cited_works": [{"id": "cw1", "citation_verbatim": "Ref q2"}],
        "primary_sources": [{"path": "government/x.pdf", "quote_corroboration":
                             "2 contested token(s): q14 ‹Thursday› (line 11)"}],
    }))
    record("paths, URLs and link wraps are exempt", _silent({
        "description": "See [`/people/q3-man`] and https://example.org/q3/t8 "
                       "and government/q3-report.pdf and /documents/t8-memo.",
        "timeline": [{"id": "t1", "date": "2020", "event": "x",
                      "node_link": "/documents/q3-memo",
                      "observed_event_ref": "/events/t8"}],
    }))


def main():
    print("=" * 70)
    print(" prose-entry-ID regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (pre-fix prose errors from the owning "
          f"phase; source labels / pointers / verbatim / paths silent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
