#!/usr/bin/env python3
"""finalize-attribution.py — strip verification scaffolding from a speaker-
attribution sibling, leaving a structured-only verified artifact.

`rationale` and `verifier_notes` are DRAFT-PHASE scaffolding: the producer
emits the cue for each contested boundary, the independent verifier checks it
against the source. Once the sibling is verified that prose has served its
purpose — it isn't load-bearing on the committed artifact, it eats tokens, and
it renders into the `-attributed.md`. This tool removes it deterministically
(agents emit/judge; scripts mutate), so a verified sibling carries only its
structured fields. `confidence: low|medium` remains as the durable uncertainty
marker; an investigator reads the source lines to judge any boundary.

Stripped: every turn's `rationale` + `verifier_notes`, the top-level
`verifier_notes`, and any `contributor_notes` on an image_verification entry.
Kept: all structured fields, `confidence`, `referenced_source`, speaker
`notes`, `image_verification` (turn_line_range / resolution /
resolved_speaker_id / resolved_by).

Run after the independent verifier returns PASS:

  ./finalize-attribution.py SIBLING.yaml --verifier-session SESSION_ID

On an already-verified sibling (re-finalize), --verifier-session may be
omitted — the existing one is kept. Run `validate-speaker-attribution.py`
afterwards; a verified sibling that still carries scaffolding is a FATAL there
(this tool is what clears it).
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT, strict_yaml_load  # noqa: E402

HEADER = (
    "# Speaker-attribution sibling — verified, structured-only. Verification\n"
    "# scaffolding (rationale / verifier_notes) was stripped by\n"
    "# scripts/build/finalize-attribution.py once the independent verifier\n"
    "# passed. Indexes into the source transcript by 1-indexed line range;\n"
    "# references only, no transcript text. Conforms to\n"
    "# meta/schema-speaker-attribution.yaml.\n"
)


def finalize(data: dict, verifier_session: str | None) -> dict:
    """Set verified status + session and strip scaffolding. Returns counts."""
    if verifier_session:
        data["verification_status"] = "verified"
        data["verifier_session"] = verifier_session
    else:
        if data.get("verification_status") != "verified" or not data.get("verifier_session"):
            sys.exit(
                "error: sibling is not verified and no --verifier-session given. "
                "Finalize only an independent-verifier-approved sibling."
            )

    counts = {"rationale": 0, "turn_verifier_notes": 0,
              "top_verifier_notes": 0, "contributor_notes": 0}

    if data.pop("verifier_notes", None) is not None:
        counts["top_verifier_notes"] = 1
    for t in data.get("turns") or []:
        if isinstance(t, dict):
            if t.pop("rationale", None) is not None:
                counts["rationale"] += 1
            if t.pop("verifier_notes", None) is not None:
                counts["turn_verifier_notes"] += 1
    for e in data.get("image_verification") or []:
        if isinstance(e, dict) and e.pop("contributor_notes", None) is not None:
            counts["contributor_notes"] += 1
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="path to {slug}-attribution.yaml")
    ap.add_argument("--verifier-session",
                    help="verifier agent session id (sets status=verified). "
                         "Optional when the sibling is already verified.")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"error: not found: {path}")

    with path.open() as f:
        data = strict_yaml_load(f)
    if not isinstance(data, dict):
        sys.exit("error: sibling is not a YAML mapping")

    counts = finalize(data, args.verifier_session)

    # sort_keys=False preserves the producer's key order; width avoids wrapping
    # long scalars (source_path). After stripping, every value is a short
    # scalar or list, so the dump is clean and stable across re-runs.
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=4096)
    with path.open("w") as f:
        f.write(HEADER + "\n" + body)

    total = sum(counts.values())
    print(f"Finalized {path}")
    print(f"  verification_status: {data['verification_status']}   "
          f"verifier_session: {data.get('verifier_session')}")
    print(f"  stripped: {counts['rationale']} rationale, "
          f"{counts['turn_verifier_notes']} turn verifier_notes, "
          f"{counts['top_verifier_notes']} top verifier_notes, "
          f"{counts['contributor_notes']} contributor_notes "
          f"({total} prose field(s) total)")


if __name__ == "__main__":
    main()
