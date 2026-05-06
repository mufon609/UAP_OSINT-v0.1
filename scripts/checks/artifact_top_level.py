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
  - person artifacts require ``background`` / ``uap_relevance`` /
    ``credibility_notes`` prose fields (renderer reads them; absent
    → renderer emits TODO stubs)
  - event artifacts require ``event_intrinsic`` dict + ``participants``
    list

Shape: bundles small heterogeneous metadata checks into one module
because the per-check granularity isn't useful — these checks are
all "this top-level shape" enforcement, share the artifact's
top-level dict access, and don't benefit from individual isolation.
Per-section entry checks (quotes, rumors, timeline, etc.) live in
their own modules and gate themselves by target type.
"""

from pathlib import Path

from checks import Issue


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

# Person-artifact prose fields the renderer reads to populate
# Background / UAP Relevance / Credibility Notes sections.
PERSON_PROSE_KEYS = ("background", "uap_relevance", "credibility_notes")

# Event-artifact universal keys.
EVENT_REQUIRED_KEYS = ("event_intrinsic", "participants")

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

    # schema_version compatibility
    sv = data.get("schema_version")
    compatible_with = ctx.schema.get("schema", {}).get("compatible_with", [1])
    if sv is not None:
        if not isinstance(sv, int) or isinstance(sv, bool):
            yield Issue(
                ctx.rel, "error",
                f"schema_version must be an integer; got {sv!r}",
                check_name=CHECK_NAME,
            )
        elif sv not in compatible_with:
            current = ctx.schema.get("schema", {}).get("version", "?")
            yield Issue(
                ctx.rel, "error",
                f"schema_version {sv} not in compatible_with {compatible_with} "
                f"(current schema version is {current}). "
                f"Migrate per meta/toolkit-notes/schema-migrations/.",
                check_name=CHECK_NAME,
            )

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

    # description required on non-person target types
    if (ctx.target_type in DESCRIPTION_REQUIRED_TYPES
            and "description" not in data):
        yield Issue(
            ctx.rel, "error",
            f"Missing required top-level key: 'description' "
            f"(target_node type {ctx.target_type!r} renders "
            f"## Description from this field)",
            check_name=CHECK_NAME,
        )

    # Person-artifact prose keys
    if ctx.target_type == "person":
        for key in PERSON_PROSE_KEYS:
            if key not in data:
                yield Issue(
                    ctx.rel, "error",
                    f"Required {key!r} key missing "
                    f"(person artifacts require "
                    f"{', '.join(PERSON_PROSE_KEYS)})",
                    check_name=CHECK_NAME,
                )
    elif ctx.target_type is not None:
        for key in PERSON_PROSE_KEYS:
            if key in data:
                yield Issue(
                    ctx.rel, "error",
                    f"{key!r} key should not be present "
                    f"(target_node type {ctx.target_type!r} is not person)",
                    check_name=CHECK_NAME,
                )

    # Event-artifact universal keys
    if ctx.target_type == "event":
        for key in EVENT_REQUIRED_KEYS:
            if key not in data:
                yield Issue(
                    ctx.rel, "error",
                    f"Required {key!r} key missing "
                    f"(event artifacts require "
                    f"{', '.join(EVENT_REQUIRED_KEYS)})",
                    check_name=CHECK_NAME,
                )
    elif ctx.target_type is not None:
        for key in EVENT_REQUIRED_KEYS:
            if key in data:
                yield Issue(
                    ctx.rel, "error",
                    f"{key!r} key should not be present "
                    f"(target_node type {ctx.target_type!r} is not event)",
                    check_name=CHECK_NAME,
                )
