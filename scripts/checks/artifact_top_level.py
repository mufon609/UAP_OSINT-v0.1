"""artifact-top-level check — research-artifact ResearchContext check.

Bundles the universal-required top-level metadata checks for every
research artifact:

  - top-level required keys: id, type, schema_version, target_node,
    status, created, primary_sources, document_intrinsic,
    context_extrinsic, quotes, entities_referenced, naming_quirks
  - id matches the file path (``meta/research/{slug}``)
  - type literal equals ``research-artifact``
  - schema_version is integer in ``schema.compatible_with``
  - status enum: active | archived
  - target_node points to an existing content-node .md file
  - description required on non-person target types (the person body
    renderer doesn't emit ``## Description``; other types do)

Type-conditional sections / fields (background, uap_relevance,
credibility_notes, event_intrinsic, participants, etc.) are gated by
``iff_section`` (schema-driven dispatch over
``schema.yaml::conditional_keys``); the per-section checks rely on
``section_in_scope``. artifact_top_level keeps only the universal
metadata + the description-required-on-non-person rule that isn't
expressed in conditional_keys today.

Shape: bundles small heterogeneous metadata checks into one module
because the per-check granularity isn't useful — these checks are
all "this top-level shape" enforcement, share the artifact's
top-level dict access, and don't benefit from individual isolation.
"""

from pathlib import Path

from checks import Issue
from lib._common import schema_version_compat_messages


CHECK_NAME = "artifact_top_level"


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


REQUIRED_TOP_LEVEL_KEYS = [
    "id", "type", "schema_version", "target_node", "status", "created",
    "primary_sources", "document_intrinsic",
    "context_extrinsic", "quotes", "entities_referenced",
    "naming_quirks",
]

# description required on all artifact types EXCEPT person.
DESCRIPTION_REQUIRED_TYPES = {
    "document", "transcript", "media", "event",
    "organization", "finding", "location",
}

VALID_STATUS = {"active", "archived"}


def check(ctx):
    data = ctx.data

    # Top-level required keys
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            yield Issue(
                ctx.rel, "error",
                f"Missing required top-level key: {key!r}",
                check_name=CHECK_NAME,
            )

    # id matches file path
    expected_id = f"meta/research/{ctx.path.stem}"
    if data.get("id") and data.get("id") != expected_id:
        yield Issue(
            ctx.rel, "error",
            f"id {data.get('id')!r} does not match file path ({expected_id!r})",
            check_name=CHECK_NAME,
        )

    # type literal
    if "type" in data and data.get("type") != "research-artifact":
        yield Issue(
            ctx.rel, "error",
            f"type must be 'research-artifact'; got {data.get('type')!r}",
            check_name=CHECK_NAME,
        )

    # schema_version compatibility (via shared lib helper — Issue #8 dedup)
    schema_block = ctx.schema.get("schema", {}) or {}
    compatible_with = schema_block.get("compatible_with", [1])
    current = schema_block.get("version", "?")
    for level, msg in schema_version_compat_messages(
        data.get("schema_version"), compatible_with, current,
    ):
        yield Issue(ctx.rel, level, msg, check_name=CHECK_NAME)

    # status enum
    if data.get("status") and data.get("status") not in VALID_STATUS:
        yield Issue(
            ctx.rel, "error",
            f"status must be one of {sorted(VALID_STATUS)}; "
            f"got {data.get('status')!r}",
            check_name=CHECK_NAME,
        )

    # target_node existence
    target_node = data.get("target_node")
    if target_node:
        target_path = _REPO_ROOT / f"{target_node}.md"
        if not target_path.exists():
            yield Issue(
                ctx.rel, "error",
                f"target_node {target_node!r} does not point to an "
                f"existing file ({target_path.relative_to(_REPO_ROOT)})",
                check_name=CHECK_NAME,
            )

    # description required on non-person target types. Not expressed in
    # conditional_keys today (would need a schema extension to declare
    # "required when target_type NOT in [person]"); kept as a small inline
    # rule until that extension lands.
    if (ctx.target_type in DESCRIPTION_REQUIRED_TYPES
            and "description" not in data):
        yield Issue(
            ctx.rel, "error",
            f"Missing required top-level key: 'description' "
            f"(target_node type {ctx.target_type!r} renders "
            f"## Description from this field)",
            check_name=CHECK_NAME,
        )
