#!/usr/bin/env python3
"""Verify every schema-required section is renderer-producible.

For each content type in ``meta/schema.yaml``'s ``types`` (the nine content
types — meta / research-artifact / attestation_tier excluded), gather the
COMPLETE set of sections the schema can require for it: the union, in RAW
``{topic_display_name}`` placeholder form (no topic substitution), of every
``required_sections`` list (across all kinds / archetypes, or the top-level
one), every ``optional_sections`` entry, and every ``conditionally_required``
section-name key. Assert that set is a SUBSET of the type renderer's ``EMITS``
declaration (``scripts/build/renderers/{type}.py``).

Closes the class gap the removed corpus-addendum exposed:
``scripts/checks/required_sections.py`` can demand a section the type's
renderer has no code path to emit, and nothing flags the contradiction — the
validator requires it, the build can't produce it, and the mismatch is
invisible until traced by hand. This is the STATIC guard:
``scripts/tests/smoke.py`` catches the same gap empirically, but only for
dimensions it has a fixture for; this check covers every schema-declared
required section regardless of fixtures.

Comparing RAW placeholder forms on both sides (schema strings and each
renderer's ``EMITS``) means no ``load_topic()`` is needed — the
``{topic_display_name}`` placeholder is matched literally.

Usage:
  renderer-coverage.py            # report gaps (exit 1 if any)
  renderer-coverage.py --quiet    # exit code only; suppress detail

Pre-commit gate. Blocks commit when a schema-required section has no
renderer code path.
"""
import argparse
import sys
from pathlib import Path

# scripts/build/renderer-coverage.py — put scripts/ and scripts/build/ on
# sys.path so `from lib._common` and `from renderers.X` both resolve from
# this nested location (mirrors build-from-research.py's import topology).
_BUILD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BUILD_DIR.parent))   # scripts/
sys.path.insert(0, str(_BUILD_DIR))          # scripts/build/

from lib._common import load_schema  # noqa: E402

from renderers.document import EMITS as DOCUMENT_EMITS  # noqa: E402
from renderers.person import EMITS as PERSON_EMITS  # noqa: E402
from renderers.organization import EMITS as ORGANIZATION_EMITS  # noqa: E402
from renderers.event import EMITS as EVENT_EMITS  # noqa: E402
from renderers.transcript import EMITS as TRANSCRIPT_EMITS  # noqa: E402
from renderers.media import EMITS as MEDIA_EMITS  # noqa: E402
from renderers.location import EMITS as LOCATION_EMITS  # noqa: E402
from renderers.finding import EMITS as FINDING_EMITS  # noqa: E402
from renderers.investigation import EMITS as INVESTIGATION_EMITS  # noqa: E402


# Renderer ``EMITS`` keyed by content-type name. The nine content types;
# meta / research-artifact / attestation_tier are not content types and
# carry no renderer.
RENDERER_EMITS = {
    "document": DOCUMENT_EMITS,
    "person": PERSON_EMITS,
    "organization": ORGANIZATION_EMITS,
    "event": EVENT_EMITS,
    "transcript": TRANSCRIPT_EMITS,
    "media": MEDIA_EMITS,
    "location": LOCATION_EMITS,
    "finding": FINDING_EMITS,
    "investigation": INVESTIGATION_EMITS,
}


def _is_section_name(name):
    """Section names begin with an uppercase letter and aren't snake_case.
    The ``conditionally_required`` key is overloaded in schema.yaml — media's
    use carries section names, document's carries frontmatter field names.
    Filter to TitleCase-style entries (section names) and drop snake_case
    entries (field names). Mirrors build-md-spec.py's filter."""
    return bool(name) and name[0].isupper() and "_" not in name


def collect_schema_sections(tdata):
    """Return the set of every section name the schema can require for a
    type, in RAW ``{topic_display_name}`` placeholder form (no topic
    substitution). Union of required_sections / optional_sections /
    conditionally_required section-name keys across the top-level entry
    and every archetype / kind sub-entry."""
    out = set()

    def _add(seq):
        for s in seq or []:
            out.add(s)

    def _add_cond(cr):
        if not isinstance(cr, dict):
            return
        for name in cr.keys():
            if _is_section_name(name):
                out.add(name)

    _add(tdata.get("required_sections"))
    _add(tdata.get("optional_sections"))
    _add_cond(tdata.get("conditionally_required"))
    for adata in (tdata.get("archetypes") or {}).values():
        if isinstance(adata, dict):
            _add(adata.get("required_sections"))
            _add(adata.get("optional_sections"))
            _add_cond(adata.get("conditionally_required"))
    for kdata in (tdata.get("kinds") or {}).values():
        if isinstance(kdata, dict):
            _add(kdata.get("required_sections"))
            _add(kdata.get("optional_sections"))
            _add_cond(kdata.get("conditionally_required"))
    return out


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--quiet", action="store_true",
                   help="Exit code only; suppress detail output.")
    args = p.parse_args()

    schema = load_schema()
    types = schema.get("types") or {}

    gaps = []          # (type, section) pairs the renderer can't emit
    types_checked = 0
    sections_checked = 0

    for tname, emits in RENDERER_EMITS.items():
        tdata = types.get(tname)
        if not isinstance(tdata, dict):
            gaps.append((tname, "<type missing from schema.yaml>"))
            continue
        types_checked += 1
        schema_sections = collect_schema_sections(tdata)
        sections_checked += len(schema_sections)
        for section in sorted(schema_sections):
            if section not in emits:
                gaps.append((tname, section))

    if not gaps:
        if not args.quiet:
            print(f"renderer-coverage OK — {types_checked} types, "
                  f"{sections_checked} schema-required sections all "
                  f"renderer-producible.")
        return 0

    if args.quiet:
        return 1

    print("Schema-required sections with no renderer code path:")
    for tname, section in gaps:
        print(f"  - {tname}: '{section}' is schema-required but "
              f"renderers/{tname}.py EMITS has no code path to emit it.")
    print()
    print(f"{len(gaps)} gap(s) across {types_checked} types checked.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
