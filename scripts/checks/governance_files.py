"""governance-frontmatter check — global BaseContext check.

Validates every ``.md`` file under ``meta/`` carries the required
frontmatter discipline: id / type / schema_version / created;
schema_version in ``schema.compatible_with``; id matches file path.

Routes templates (under ``meta/templates/``) through a placeholder-
aware regex path because their ``{{slug}}`` / ``{{today}}`` values
can't be YAML-parsed cleanly (``{...}`` conflicts with YAML's flow-
mapping syntax). Governance docs (everything else under ``meta/``)
use standard YAML frontmatter parsing.

Skips ``meta/topic/working-notes/`` per the working-notes README:
those files sit outside the validated content layer (transient
contributor scratch, deleted on integration).

Consumes ``BaseContext.schema``; performs its own filesystem walk
(governance walk is global, not driven by content-node iteration).

Origin: introduced at commit ``30b7fc3`` ("Add check #13 —
governance-file frontmatter validation"). Closes BACKLOG #3.
Pre-30b7fc3, every .md file under meta/ carried schema_version
frontmatter but no validation pass enforced the discipline.
Template drift was the highest-blast-radius scenario: a drifted
schema_version in ``meta/templates/{type}.md`` propagates to every
node scaffolded afterward via ``new.py``, and was previously
undetectable until someone tried to validate one of those
downstream nodes. Defensive design — the check guards an invariant
to prevent a known failure class rather than responding to a
specific incident.

Migration trail:

  - ``30b7fc3`` (introduction; inline in validate.py)
  - ``7f5f86f`` (C11 session 2 — "checks: migrate governance_files;
    lift parse_frontmatter to lib/_common"): moved
    ``parse_frontmatter`` into ``lib/_common.py`` alongside the
    governance check lift, so both this check and the node
    frontmatter checks share one parse implementation
  - ``2f3effb`` (BACKLOG #8 close): consolidated the schema_version
    compat-check messaging into ``schema_version_compat_messages``,
    a shared helper used here on both routes (template + governance-
    doc) plus the node frontmatter check and the research-artifact
    top-level check — single point of truth for the version-compat
    error / migration-pointer wording

C18 confirmed byte-identity through both the per-module migration
and the helper consolidation.

Type → content-directory mapping comes from ``lib._common
.content_type_dirs()`` — single source of truth shared with
``new.py``, ``research-scaffold.py``, ``build-from-research.py``,
the validator orchestrators, and every other script that walks the
content layer.
"""

import re
from pathlib import Path

from checks import Issue
from lib._common import (
    content_type_dirs,
    parse_frontmatter,
    schema_version_compat_messages,
)


CHECK_NAME = "governance_files"

_REQUIRED_META_FIELDS = ("id", "type", "schema_version", "created")

# meta/topic/working-notes/ is the holding pen for in-progress contributor
# synthesis (handoff drafts, audit scratch, investigation notes). Per
# meta/topic/working-notes/README.md, files there sit outside the validated
# content layer and the schema-frontmatter contract — they're transient
# scratch material, deleted on integration.
_WORKING_NOTES_PREFIX = "meta/topic/working-notes/"


# Repo paths derived from this module's location so the check works
# regardless of which orchestrator invoked it.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_META_DIR = _REPO_ROOT / "meta"


def _iter_governance_files():
    """Yield every .md file under meta/ except working-notes drafts,
    ordered by path for stable reports."""
    if not _META_DIR.is_dir():
        return
    for p in sorted(_META_DIR.rglob("*.md")):
        rel = p.relative_to(_REPO_ROOT).as_posix()
        if rel.startswith(_WORKING_NOTES_PREFIX):
            continue
        yield p


def _check_template_frontmatter(path, rel, text, compatible_with, schema_block):
    """Template-specific frontmatter check. YAML can't cleanly parse
    template placeholders like ``{{slug}}`` and ``{{today}}`` — they
    conflict with YAML's flow-mapping syntax (``{...}``). Use line-based
    regex checks against the raw frontmatter block instead."""
    if not text.startswith("---"):
        yield Issue(rel, "error",
            "Template missing frontmatter opener '---'",
            check_name=CHECK_NAME)
        return
    end = text.find("\n---", 3)
    if end < 0:
        yield Issue(rel, "error",
            "Template frontmatter not closed with '---'",
            check_name=CHECK_NAME)
        return
    block = text[3:end]
    stem = path.stem

    # id: must match the placeholder pattern "{content-dir}/{{slug}}"
    id_match = re.search(r"^id:\s*(\S.*?)\s*$", block, re.MULTILINE)
    if not id_match:
        yield Issue(rel, "error",
            "Template missing required 'id:' line in frontmatter",
            check_name=CHECK_NAME)
    else:
        # Schema-derived type→dir map; ``.get(stem, stem)`` falls back
        # to using the stem as dirname for forward compatibility (a new
        # node type whose template ships before its schema entry).
        expected_dir = content_type_dirs().get(stem, stem)
        expected_id = f"{expected_dir}/{{{{slug}}}}"
        if id_match.group(1) != expected_id:
            yield Issue(rel, "error",
                f"Template id {id_match.group(1)!r} does not match "
                f"expected placeholder pattern {expected_id!r} "
                f"(derived from filename stem {stem!r})",
                check_name=CHECK_NAME)

    # type: must match the filename stem
    type_match = re.search(r"^type:\s*(\S.*?)\s*$", block, re.MULTILINE)
    if not type_match:
        yield Issue(rel, "error",
            "Template missing required 'type:' line in frontmatter",
            check_name=CHECK_NAME)
    elif type_match.group(1) != stem:
        yield Issue(rel, "error",
            f"Template type {type_match.group(1)!r} does not match "
            f"filename stem {stem!r}",
            check_name=CHECK_NAME)

    # schema_version: must be integer in compatible_with. Templates
    # hard-code a version (not a placeholder) because scaffolded nodes
    # inherit the value verbatim. Shared lib helper drives the
    # compat-check messaging (Issue #8 dedup).
    sv_match = re.search(r"^schema_version:\s*(\d+)\s*$", block, re.MULTILINE)
    if not sv_match:
        yield Issue(rel, "error",
            "Template missing required 'schema_version:' line "
            "(must be an integer, not a placeholder)",
            check_name=CHECK_NAME)
    else:
        sv = int(sv_match.group(1))
        current = schema_block.get("version", "?")
        for level, msg in schema_version_compat_messages(
            sv, compatible_with, current, prefix="Template ",
        ):
            yield Issue(rel, level, msg, check_name=CHECK_NAME)

    # created: required; value is always `{{today}}` placeholder, not
    # validated as a date (the scaffolder substitutes).
    if not re.search(r"^created:\s*\S", block, re.MULTILINE):
        yield Issue(rel, "error",
            "Template missing required 'created:' line in frontmatter",
            check_name=CHECK_NAME)


def _check_governance_doc_frontmatter(path, rel, text, compatible_with, schema_block):
    """Standard governance-doc frontmatter check via YAML parse."""
    fm, _ = parse_frontmatter(text)

    if fm is None:
        yield Issue(rel, "error",
            "Missing or malformed YAML frontmatter (meta/ files require "
            "id / type / schema_version / created)",
            check_name=CHECK_NAME)
        return

    # Required fields
    for field in _REQUIRED_META_FIELDS:
        if field not in fm:
            yield Issue(rel, "error",
                f"Missing required frontmatter field {field!r} "
                f"(meta/ files require "
                f"{' / '.join(_REQUIRED_META_FIELDS)})",
                check_name=CHECK_NAME)

    # schema_version value check (shared lib helper — Issue #8 dedup)
    current = schema_block.get("version", "?")
    for level, msg in schema_version_compat_messages(
        fm.get("schema_version"), compatible_with, current,
    ):
        yield Issue(rel, level, msg, check_name=CHECK_NAME)

    # id matches path
    if "id" in fm:
        expected_id = str(rel).removesuffix(".md")
        if fm["id"] != expected_id:
            yield Issue(rel, "error",
                f"Frontmatter id {fm['id']!r} does not match path "
                f"{expected_id!r}",
                check_name=CHECK_NAME)

    # Per BACKLOG C22: meta/topic/overview.md is the canonical topic-
    # config record; frontmatter must carry topic + display_name so
    # lib._common.load_topic() and the renderer can substitute the
    # display name into section headers. Other governance docs
    # don't need these fields.
    if str(rel) == "meta/topic/overview.md":
        for field in ("topic", "display_name"):
            if field not in fm:
                yield Issue(rel, "error",
                    f"meta/topic/overview.md frontmatter missing "
                    f"required topic-config field {field!r} (topic + "
                    f"display_name drive schema-field-rename + renderer "
                    f"section-header substitution; see BACKLOG C22 + "
                    f"prompts/fork-init.md)",
                    check_name=CHECK_NAME)


def check(ctx):
    """Yield Issues for any governance file under meta/ that violates
    the frontmatter discipline. Templates routed through a placeholder-
    aware regex path; everything else uses standard YAML parsing.
    Also verifies meta/topic/overview.md exists — every toolkit
    instance must declare its topic scope there (see BACKLOG C22 +
    prompts/fork-init.md)."""
    # Direct schema-config access; KeyError surfaces if the schema's
    # `schema:` block or its required nested keys are missing. Schema
    # is foundational toolkit contract — silent fallbacks would mask
    # schema drift, not a degrade-gracefully case.
    schema_block = ctx.schema["schema"]
    compatible_with = schema_block["compatible_with"]

    overview_path = _META_DIR / "topic" / "overview.md"
    if not overview_path.exists():
        yield Issue(
            "meta/topic/overview.md", "error",
            "Required file missing — every toolkit instance must declare "
            "its topic scope in meta/topic/overview.md. See README.md for "
            "fork procedure.",
            check_name=CHECK_NAME,
        )

    for path in _iter_governance_files():
        rel = path.relative_to(_REPO_ROOT)
        rel_str = str(rel)
        is_template = rel_str.startswith("meta/templates/")

        text = path.read_text(encoding="utf-8", errors="replace")

        if is_template:
            yield from _check_template_frontmatter(
                path, rel, text, compatible_with, schema_block)
        else:
            yield from _check_governance_doc_frontmatter(
                path, rel, text, compatible_with, schema_block)
