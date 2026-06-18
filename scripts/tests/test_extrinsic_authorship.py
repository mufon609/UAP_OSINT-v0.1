#!/usr/bin/env python3
"""Regression guard for the extrinsic-authorship check
(`scripts/checks/extrinsic_authorship.py`).

``context_extrinsic.extrinsic_authorship`` is structured metadata that the
document renderer never displays. A ``[`/type/slug`]`` link wrap placed there
renders nowhere and duplicates the ``associated_entities`` entry, so the check
ERRORS on any wrap. The field is nested under ``context_extrinsic`` (the
historical associated_entities superset bug read it at top level and so never
fired on a real artifact — this check reads the correct nested path).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import extrinsic_authorship


class _Ctx:
    def __init__(self, data):
        self.rel = "test"
        self.data = data


def _msgs(data):
    return [i.message for i in extrinsic_authorship.check(_Ctx(data))]


def _has(msgs, needle):
    return any(needle in m for m in msgs)


CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def run():
    # no context_extrinsic → silent
    record("silent when context_extrinsic absent", not _msgs({}))

    # extrinsic_authorship absent → silent
    record("silent when extrinsic_authorship absent",
           not _msgs({"context_extrinsic": {"display_title": "X"}}))

    # clean metadata prose, no wrap → silent
    record("clean when no link wrap", not _msgs({
        "context_extrinsic": {
            "extrinsic_authorship": "Attributed to Dr. V. Teofilo of "
                                    "Lockheed Martin per the products list.",
        }
    }))

    # a person wrap nested under context_extrinsic → ERROR (the real shape;
    # the historical top-level read would have missed this)
    m = _msgs({
        "context_extrinsic": {
            "extrinsic_authorship": "Attributed to Dr. V. Teofilo "
                                    "([`/people/v-teofilo`]) of Lockheed "
                                    "Martin ([`/organizations/lockheed-martin`]).",
        }
    })
    record("fires on each nested link wrap",
           _has(m, "v-teofilo") and _has(m, "lockheed-martin")
           and len(m) == 2)

    # a top-level extrinsic_authorship (not the real shape) is NOT scanned —
    # the field is read only at its nested home, never the artifact root
    record("ignores a top-level extrinsic_authorship key", not _msgs({
        "extrinsic_authorship": "Names ([`/people/v-teofilo`]).",
    }))


def main():
    print("=" * 70)
    print(" extrinsic-authorship regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (silent-absent; nested wrap fires)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
