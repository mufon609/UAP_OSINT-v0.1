#!/usr/bin/env python3
"""Verify section-name parity between schema.yaml and prompts/build.md.

Walks schema.yaml's required_sections (and conditionally_required) for
every type x archetype/kind, applies topic_substitute(), and checks
each section name appears as a backticked `## SectionName` reference in
prompts/build.md.

Catches two drift cases:
  1. Schema adds / renames a section, prompts/build.md not updated.
  2. Fork swaps topic display_name; prompts/build.md still carries
     literal "UAP Relevance" / "UAP-Scope Activity" instead of the
     templated equivalent.

Usage:
  build-md-spec.py            # report diffs (exit 1 if any)
  build-md-spec.py --quiet    # exit code only; suppress detail

Pre-commit gate (scripts/tests/pre-commit.sh step 8). Blocks commit on
schema/build.md section drift.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT, strict_yaml_load, topic_substitute


SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
BUILD_MD_PATH = REPO_ROOT / "prompts" / "build.md"


def collect_schema_sections():
    """Walk schema.yaml; return set of all section names (topic-substituted)
    declared as required_sections or conditionally_required, across every
    type x archetype/kind.

    The conditionally_required key is overloaded in schema.yaml — media's
    use carries section names, document's carries frontmatter field names.
    Filter to TitleCase-style entries (section names) and drop snake_case
    entries (field names).
    """
    with SCHEMA_PATH.open() as f:
        schema = strict_yaml_load(f)
    types = schema.get("types") or {}
    out = set()

    def _is_section_name(name):
        # Section names begin with an uppercase letter and don't contain
        # lowercase-only-with-underscores patterns; frontmatter field names
        # are snake_case.
        return bool(name) and name[0].isupper() and "_" not in name

    def _add(seq):
        for s in seq or []:
            out.add(topic_substitute(s))

    def _add_cond(cr):
        if not isinstance(cr, dict):
            return
        for name in cr.keys():
            if _is_section_name(name):
                out.add(topic_substitute(name))

    for tname, tdata in types.items():
        if tname == "meta" or not isinstance(tdata, dict):
            continue
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

    # Universal conditional sections — rendered by scripts/build/renderers/
    # _universal.py for any artifact whose schema permits the underlying
    # entry list (rumors / naming_quirks). Not declared per-type in
    # schema; included here so the check doesn't flag them as build.md-
    # only. Mirrors _universal.py's four conditional emitters:
    #   - render_source_form_notes              naming_quirks resolution=preserve-as-sic-in-quotes
    #   - render_preserved_disagreements        naming_quirks resolution=disputed
    #   - render_primary_source_contradictions  rumors status=primary-source-disputed
    #   - render_public_record_claims           rumors status=not-primary-source-established
    out.add("Source-Form Notes")
    out.add("Preserved Disagreements")
    out.add("Primary-Source Contradictions")
    out.add("Public-Record Claims Without Primary Source")
    return out


# `## SectionName` references within backticks; restrict the inner match
# to a single line so layout artifacts don't pollute the section set.
_REF_PATTERN = re.compile(r"`## ([^`\n]+)`")


def collect_build_md_sections():
    """Walk prompts/build.md; return set of every backticked `## SectionName`
    reference."""
    text = BUILD_MD_PATH.read_text()
    return set(_REF_PATTERN.findall(text))


def main():
    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--quiet", action="store_true",
                   help="Exit code only; suppress detail output.")
    args = p.parse_args()

    schema_sections = collect_schema_sections()
    build_md_sections = collect_build_md_sections()

    missing_from_build = schema_sections - build_md_sections
    extra_in_build = build_md_sections - schema_sections

    if not missing_from_build and not extra_in_build:
        if not args.quiet:
            print(f"prompts/build.md section parity OK "
                  f"({len(schema_sections)} sections checked).")
        return 0

    if args.quiet:
        return 1

    if missing_from_build:
        print("Schema sections not referenced in prompts/build.md:")
        for s in sorted(missing_from_build):
            print(f"  - {s}")
        print()
    if extra_in_build:
        print("prompts/build.md sections not in schema:")
        for s in sorted(extra_in_build):
            print(f"  - {s}")
        print()
    print(f"Schema sections: {len(schema_sections)} | "
          f"build.md sections: {len(build_md_sections)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
