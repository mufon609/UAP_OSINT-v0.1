"""frontmatter-parse check — preflight for the per-node check chain.

Validates that a content node's frontmatter parsed cleanly and declares
a known node type. Three fatal cases:

  - Frontmatter missing or malformed (``ctx.fm`` is None — the
    orchestrator's ``parse_frontmatter`` call returned None on absent
    delimiters or YAMLError).
  - 'type' field absent or empty.
  - 'type' value not a key in ``schema.types``.

Pure inspection — does NOT read or parse the file. The orchestrator
owns the frontmatter parse and populates ``ctx.fm`` on success or
leaves it None on failure. This check reads that state and yields
fatal Issues; downstream Context construction reuses ``ctx.fm`` so no
second parse runs.

Runs as a preflight in ``validate.py``'s per-node iteration: the
orchestrator constructs a minimal NodeContext (text + base + fm
populated by the single parse), dispatches this check, and short-
circuits the main ``_NODE_CHECKS`` chain on any fatal Issue.
Downstream checks rely on ``ctx.fm`` / ``ctx.node_type`` /
``ctx.type_spec`` being populated.
"""

from checks import Issue


CHECK_NAME = "frontmatter_parse"


def check(ctx):
    """Yield fatal Issues for any frontmatter / type-spec failure that
    would prevent downstream NodeContext construction. Reads only
    ``ctx.fm`` (populated by orchestrator) and ``ctx.schema``;
    ``ctx.node_type`` / ``ctx.type_spec`` are populated by the
    orchestrator AFTER this check passes."""
    if ctx.fm is None:
        yield Issue(
            ctx.rel, "error",
            "Missing or malformed YAML frontmatter",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    node_type = ctx.fm.get("type")
    if not node_type:
        yield Issue(
            ctx.rel, "error",
            "Missing 'type' in frontmatter",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    if node_type not in ctx.schema["types"]:
        yield Issue(
            ctx.rel, "error",
            f"Unknown type '{node_type}'",
            check_name=CHECK_NAME, fatal=True,
        )
