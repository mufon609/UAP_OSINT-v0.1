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

Type-conditional sections / fields (background, top_relevance,
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

Origin: foundational from the initial commit (``af5f789``) with
17 required top-level keys. The check has the most-reductive
multi-stage evolution in the codebase — current
``REQUIRED_TOP_LEVEL_KEYS`` is 12 keys; 5 have been removed as
surrounding-system simplifications landed:

  - ``description`` made type-conditional at ``efd4588`` ("Fix
    three pilot findings surfaced during the Graves person pilot").
    Person body renderer doesn't emit ## Description (it emits
    Background / {display_name} Relevance / Credibility Notes from
    dedicated fields ``background`` / ``top_relevance`` /
    ``credibility_notes``), so description is required on non-person
    target types only — kept here as the inline
    ``DESCRIPTION_REQUIRED_TYPES`` set.
  - ``claims`` removed at ``cde69cf`` (2026-04-21 — claims[] layer
    elimination): ``quotes[]`` became the universal evidentiary
    primitive; the claims data-shape layer no longer existed for
    artifacts to carry.
  - ``iterations`` + ``last_iteration`` removed at ``1a8ddbb``
    ("Remove iteration log: git is the audit trail"): the in-
    artifact iteration log was ceremony duplicating git; 794 per-
    entry refs across 15 artifacts cleared in the same wave (per
    ``meta/roadmap.md`` "Iteration log eliminated (2026-04-21)").
  - ``research_gaps`` removed at ``7ec1d61`` ("Remove Open Questions
    / Research Gaps — will be absorbed by investigation redesign"):
    the Open Questions surface is being re-thought as part of
    BACKLOG A4 (rename finding → investigation).

Each removal pruned redundant validator state without adding
mechanical complexity. The "this top-level shape" enforcement role
remains; the shape itself simplified.

Anchor pattern: reductive multi-stage. Distinct from the additive
multi-stage of ``quotes`` (rules accumulated as schema tightened)
and the dual-evolution of ``entities`` (vocabulary expanded + cross-
ref simplified). artifact_top_level mostly LOST keys as the
surrounding system shed complexity — a distinct sub-shape of
multi-stage worth recognizing.

Schema-driven-dispatcher gap (recorded in the code as a comment):
the ``description``-required-on-non-person rule isn't expressed in
``schema.yaml::conditional_keys`` today. The conditional_keys
grammar (``required_when_any_of: [list of AND-rules]``) can't
express the negation case (NOT-IN [person]); the rule lives inline
here as ``DESCRIPTION_REQUIRED_TYPES`` set. Worth a schema-grammar
extension if a second negation case surfaces; at n=1 the inline
rule is the right call.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
Uses ``lib._common.schema_version_compat_messages`` (BACKLOG #8
dedup helper) for the schema-version compat check, shared with
governance_files + frontmatter / type_spec checks. C18 confirmed
byte-identity through the migration despite the heavy reduction
in REQUIRED_TOP_LEVEL_KEYS over time.
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

    # schema_version compatibility (via shared lib helper — BACKLOG #8 dedup).
    # Direct schema-config access; KeyError surfaces if the schema's
    # `schema:` block or its required nested keys are missing (schema
    # is foundational toolkit contract; silent fallbacks would mask
    # schema drift).
    schema_block = ctx.schema["schema"]
    compatible_with = schema_block["compatible_with"]
    current = schema_block["version"]
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
