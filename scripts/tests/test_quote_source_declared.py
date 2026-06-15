#!/usr/bin/env python3
"""Regression guard for the quote-source-declared invariant in the
``quotes`` check (scripts/checks/quotes.py):

  Every ``quotes[].source.path`` must appear in the artifact's own
  ``primary_sources[]`` — a quote IS the artifact drawing on a source, so a
  quoted path that isn't a declared primary source is an undeclared source.
  It is also a faithfulness hole: the sibling gates (ocr_sibling_presence /
  transcript_sibling_presence) iterate ``primary_sources[]``, not
  ``quotes[]``, so a degraded source quoted-but-not-declared escapes the
  mandatory sibling and verbatim_quotes silently falls back to the corrupt
  text layer.

Pins three behaviors that are easy to regress:
  1. The membership error FIRES when a manifest-registered path is absent
     from primary_sources[].
  2. It does NOT fire when the path is declared (no false positive).
  3. NO double-fire with the manifest check: a path absent from the
     manifest yields the manifest error ONLY (if/elif, manifest wins), and
     an empty/malformed primary_sources defers to primary_sources.py
     (no per-quote pile-on).

Pure unit test — mocks the ResearchContext fields the check reads
(rel/data/manifest_paths/target_type/schema). Uses a non-person,
non-transcript target_type so the source-membership logic is exercised
without tripping the observation_type / speaker_id branches; the invariant
is universal across types.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import quotes

# Minimal schema carrying only what quotes.check() reads at entry.
_SCHEMA = {
    "types": {
        "research-artifact": {
            "quote_entry": {
                "observation_type_values": ["direct", "relayed"],
                "attestation_tier_values": ["primary", "secondary"],
            }
        }
    }
}

DECLARED = "government/foo.pdf"      # in manifest AND in primary_sources[]
UNDECLARED = "government/bar.pdf"    # in manifest, NOT in primary_sources[]
UNREGISTERED = "government/baz.pdf"  # NOT in manifest at all
MANIFEST = {DECLARED, UNDECLARED}

_NEEDLE = "not in this artifact's primary_sources[]"
_MANIFEST_NEEDLE = "not in sources/manifest.yaml"


class _Ctx:
    def __init__(self, data, target_type="organization"):
        self.rel = "test"
        self.data = data
        self.manifest_paths = MANIFEST
        self.target_type = target_type
        self.schema = _SCHEMA


def _msgs(data, target_type="organization"):
    return [i.message for i in quotes.check(_Ctx(data, target_type))]


def _has(msgs, needle):
    return any(needle in m for m in msgs)


def _artifact(quote_path, primary_paths):
    return {
        "primary_sources": [{"path": p, "format": "pdf"} for p in primary_paths],
        "quotes": [{"id": "q1", "text": "x",
                    "source": {"path": quote_path, "location": "p. 1, ¶2"}}],
    }


CASES = []  # (label, ok)


def record(label, ok):
    CASES.append((label, ok))


def run():
    # 1. fires when a registered path is absent from primary_sources[]
    m = _msgs(_artifact(UNDECLARED, [DECLARED]))
    record("fires on undeclared (registered) quote source", _has(m, _NEEDLE))

    # 2. no false positive when the quoted path IS declared
    m = _msgs(_artifact(DECLARED, [DECLARED]))
    record("no false-positive when source is declared", not _has(m, _NEEDLE))

    # 2b. declared among MANY primary_sources (membership, not equality)
    m = _msgs(_artifact(UNDECLARED, [DECLARED, UNDECLARED]))
    record("no false-positive when declared as a non-first primary_source",
           not _has(m, _NEEDLE))

    # 3a. unregistered path -> manifest error ONLY, no double-fire
    m = _msgs(_artifact(UNREGISTERED, [DECLARED]))
    record("unregistered path fires manifest error", _has(m, _MANIFEST_NEEDLE))
    record("unregistered path does NOT also fire primary_sources error",
           not _has(m, _NEEDLE))

    # 3b. empty primary_sources -> defer to primary_sources.py, no pile-on
    m = _msgs({"primary_sources": [],
               "quotes": [{"id": "q1", "text": "x",
                           "source": {"path": DECLARED, "location": "p. 1, ¶2"}}]})
    record("empty primary_sources does NOT fire (deferred)", not _has(m, _NEEDLE))

    # universal: same invariant fires on a different target_type
    m = _msgs(_artifact(UNDECLARED, [DECLARED]), target_type="event")
    record("fires universally (event target_type)", _has(m, _NEEDLE))


def main():
    print("=" * 70)
    print(" quote-source-declared invariant regression test")
    print("=" * 70)
    print()
    run()
    failures = [label for label, ok in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label in failures:
            print(f"    - {label}")
        return 1
    print(f"  PASSED — {len(CASES)} cases "
          f"(invariant fires; no false positives; no double-fire)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
