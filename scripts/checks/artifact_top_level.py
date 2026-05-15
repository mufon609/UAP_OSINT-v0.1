"""artifact-top-level check — research-artifact ResearchContext check.

Bundles the universal top-level metadata checks for every research
artifact:

  - top-level required keys: id, type, schema_version, target_node,
    status, created, primary_sources, document_intrinsic,
    context_extrinsic, quotes, entities_referenced, naming_quirks
  - id matches the file path (``meta/research/{slug}``)
  - type literal equals ``research-artifact``
  - schema_version is integer in ``schema.compatible_with``
  - status enum: active | archived
  - target_node points to an existing content-node .md file
  - description required on document / transcript / media / event /
    organization / finding / location target types (the renderers for
    those types emit ``## Description``); not required on person
    (renderer never calls render_description) or investigation
    (renderer wires it up but a missing key is permitted)

Type-conditional sections / fields (background, top_relevance,
credibility_notes, event_intrinsic, participants, etc.) are gated by
``iff_section`` via ``schema.yaml::conditional_keys``; the per-section
checks rely on ``section_in_scope``. This check keeps only the
universal metadata plus the type-conditional description-required
rule.

The description rule isn't expressed in ``conditional_keys`` because
the grammar (``required_when_any_of: [list of AND-rules]``) only
supports type-IN matches — the rule's allowlist is the seven types
that DO require description, expressed inline here as
``DESCRIPTION_REQUIRED_TYPES``. Investigation's NOT-required state
falls out of the allowlist by exclusion alongside person.

Bundled into one module because the sub-checks are all "this top-level
shape" enforcement, share the artifact's top-level dict access, and
don't benefit from individual isolation.
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

# description required on the seven content-bearing renderer-supported
# types. Excluded: person (renderer never calls render_description) and
# investigation (renderer wires it up but treats it as optional).
DESCRIPTION_REQUIRED_TYPES = {
    "document", "transcript", "media", "event",
    "organization", "finding", "location",
}


def check(ctx):
    # Research-artifact's own ``status`` enum is declared in
    # ``schema.yaml::types.research-artifact.status_values``. Direct
    # subscript: schema malformation surfaces loudly.
    valid_status = ctx.schema["types"]["research-artifact"]["status_values"]
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

    # schema_version compatibility check via the shared lib helper.
    # Direct subscript on ``schema:`` so a malformed schema file
    # surfaces loudly rather than masking drift.
    schema_block = ctx.schema["schema"]
    compatible_with = schema_block["compatible_with"]
    current = schema_block["version"]
    for level, msg in schema_version_compat_messages(
        data.get("schema_version"), compatible_with, current,
    ):
        yield Issue(ctx.rel, level, msg, check_name=CHECK_NAME)

    # status enum
    if data.get("status") and data.get("status") not in valid_status:
        yield Issue(
            ctx.rel, "error",
            f"status must be one of {sorted(valid_status)}; "
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

    # description required on the seven types in DESCRIPTION_REQUIRED_TYPES
    # (above). Person and investigation are excluded — see the module
    # docstring for rationale. Kept as a small inline allowlist rather
    # than a conditional_keys grammar entry because the rule is
    # type-IN-allowlist, simple enough to live here.
    if (ctx.target_type in DESCRIPTION_REQUIRED_TYPES
            and "description" not in data):
        yield Issue(
            ctx.rel, "error",
            f"Missing required top-level key: 'description' "
            f"(target_node type {ctx.target_type!r} renders "
            f"## Description from this field)",
            check_name=CHECK_NAME,
        )
