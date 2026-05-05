"""governance-frontmatter check — global BaseContext check.

Validates every ``.md`` file under ``meta/`` carries the required
frontmatter discipline: id / type / schema_version / created;
schema_version in ``schema.compatible_with``; id matches file path.

Routes templates (under ``meta/templates/``) through a placeholder-
aware regex path because their ``{{slug}}`` / ``{{today}}`` values
can't be YAML-parsed cleanly. Governance docs (everything else under
``meta/``) use standard YAML frontmatter parsing.

Closes the BACKLOG gap that motivated this check: meta files carried
schema_version but had no validation pass. Template drift is the
highest-blast-radius scenario — a drifted schema_version in a
template propagates to every node scaffolded afterward, and was
previously undetectable until someone tried to validate one of those
downstream nodes.

Skips ``meta/topic/working-notes/`` per the working-notes README:
those files sit outside the validated content layer (transient
contributor scratch, deleted on integration).

Consumes ``BaseContext.schema``; performs its own filesystem walk
(governance walk is global, not driven by content-node iteration).
"""

import re
from pathlib import Path

from checks import Issue
from lib._common import parse_frontmatter


CHECK_NAME = "governance_files"


# Type → content-directory mapping used to derive a template's expected
# placeholder id (person.md → id: people/{{slug}}). Same small static map
# appears in new.py and validate-research.py; centralization deferred —
# the map is short, stable, and rarely changes (one entry added when a
# new node type ships). If drift surfaces or the map grows, promote to
# scripts/lib/_common.py alongside the source-extraction helpers.
_TEMPLATE_TYPE_DIRS = {
    "person": "people", "organization": "organizations",
    "document": "documents", "event": "events",
    "transcript": "transcripts", "media": "media",
    "location": "locations", "finding": "findings",
}

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
        expected_dir = _TEMPLATE_TYPE_DIRS.get(stem, stem)
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
    # inherit the value verbatim.
    sv_match = re.search(r"^schema_version:\s*(\d+)\s*$", block, re.MULTILINE)
    if not sv_match:
        yield Issue(rel, "error",
            "Template missing required 'schema_version:' line "
            "(must be an integer, not a placeholder)",
            check_name=CHECK_NAME)
    else:
        sv = int(sv_match.group(1))
        if sv not in compatible_with:
            current = schema_block.get("version", "?")
            yield Issue(rel, "error",
                f"Template schema_version {sv} not in compatible_with "
                f"{compatible_with} (current schema version is {current})",
                check_name=CHECK_NAME)

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

    # schema_version value check
    sv = fm.get("schema_version")
    if sv is not None:
        if not isinstance(sv, int) or isinstance(sv, bool):
            yield Issue(rel, "error",
                f"schema_version must be an integer; got {sv!r} "
                f"({type(sv).__name__})",
                check_name=CHECK_NAME)
        elif sv not in compatible_with:
            current = schema_block.get("version", "?")
            yield Issue(rel, "error",
                f"schema_version {sv} not in compatible_with "
                f"{compatible_with} (current schema version is "
                f"{current}). Migrate per "
                f"meta/toolkit-notes/schema-migrations/.",
                check_name=CHECK_NAME)

    # id matches path
    if "id" in fm:
        expected_id = str(rel).removesuffix(".md")
        if fm["id"] != expected_id:
            yield Issue(rel, "error",
                f"Frontmatter id {fm['id']!r} does not match path "
                f"{expected_id!r}",
                check_name=CHECK_NAME)


def check(ctx):
    """Yield Issues for any governance file under meta/ that violates
    the frontmatter discipline. Templates routed through a placeholder-
    aware regex path; everything else uses standard YAML parsing."""
    schema_block = ctx.schema.get("schema", {}) or {}
    compatible_with = schema_block.get("compatible_with", [1])

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
