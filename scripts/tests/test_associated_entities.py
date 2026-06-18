#!/usr/bin/env python3
"""Regression guard for the associated-entities check
(`scripts/checks/associated_entities.py`).

The ``associated_entities`` field is the complete, deduped list of every
entity a source names, unioned into ``## Associated Nodes`` by associate.py —
the mechanism that carries an entity named only inside a verbatim quote
(un-wrappable) without depending on the ``description`` prose. The field is
required on the source-backed types and forbidden elsewhere (enforced by
iff_section from the schema conditional_keys rule); THIS check is the content
validator — silent when the field is absent (iff_section owns presence), and
when present it enforces shape (well-formed ``/type/slug``, no dupes, list
type) and the completeness superset (every inline prose-wrap is a member). See
the build-protocol "Linking — ingest is the relevance decision" contract.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import associated_entities


class _Ctx:
    def __init__(self, data):
        self.rel = "test"
        self.data = data


def _msgs(data):
    return [i.message for i in associated_entities.check(_Ctx(data))]


def _has(msgs, needle):
    return any(needle in m for m in msgs)


CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def run():
    # absent field — optional during rollout, check is silent
    record("silent when field absent", not _msgs({"description": "no field here"}))

    # well-formed complete field, description wraps a member → clean
    good = {
        "target_node": "documents/x",
        "associated_entities": ["/organizations/dia", "/people/john-greenewald"],
        "description": "A doc by John Greenewald ([`/people/john-greenewald`]).",
    }
    record("clean on well-formed + superset", not _msgs(good), repr(_msgs(good)))

    # description wraps an entity NOT in the field → superset ERROR
    m = _msgs({
        "target_node": "documents/x",
        "associated_entities": ["/organizations/dia"],
        "description": "Names Princeton ([`/organizations/princeton-university`]).",
    })
    record("fires on prose-wrap missing from field",
           _has(m, "princeton-university") and _has(m, "absent from"))

    # malformed path (unknown type dir) → shape ERROR
    m = _msgs({"target_node": "documents/x",
               "associated_entities": ["/widgets/foo"]})
    record("fires on unknown type dir", _has(m, "well-formed"))

    # malformed path (missing slug) → shape ERROR
    m = _msgs({"target_node": "documents/x",
               "associated_entities": ["/people/"]})
    record("fires on missing slug", _has(m, "well-formed"))

    # duplicate entry → ERROR
    m = _msgs({"target_node": "documents/x",
               "associated_entities": ["/people/x-y", "/people/x-y"]})
    record("fires on duplicate", _has(m, "duplicate"))

    # non-list value → ERROR
    m = _msgs({"target_node": "documents/x", "associated_entities": "NONE"})
    record("fires on non-list value", _has(m, "must be a list"))

    # self-reference wrap is excluded from the superset requirement
    m = _msgs({
        "target_node": "documents/self-doc",
        "associated_entities": ["/people/john-greenewald"],
        "description": "This doc ([`/documents/self-doc`]) by Greenewald "
                       "([`/people/john-greenewald`]).",
    })
    record("excludes self-reference from superset", not m, repr(m))

    # extrinsic_authorship is METADATA-ONLY and lives nested under
    # context_extrinsic — it is NOT one of the scanned prose fields, so a wrap
    # there is the extrinsic_authorship check's concern, not the superset's.
    # The superset must NOT fire on it (the historical bug read it at top level
    # and so never matched a real artifact; that path is gone). The externally-
    # attested author IS still listed in the field directly, as prose without a
    # wrap.
    m = _msgs({
        "target_node": "documents/x",
        "associated_entities": ["/people/vincent-teofilo"],
        "context_extrinsic": {
            "extrinsic_authorship": "Attributed to Dr. V. Teofilo of "
                                    "Lockheed Martin per the products list.",
        },
    })
    record("superset ignores extrinsic_authorship (metadata-only)", not m, repr(m))


def main():
    print("=" * 70)
    print(" associated-entities regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (silent-absent; shape + superset fire)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
