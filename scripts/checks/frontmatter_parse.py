"""frontmatter-parse check — preflight for the per-node check chain.

Validates that a content node's frontmatter parses cleanly and declares
a known node type. Three fatal cases:

  - Frontmatter missing or malformed (yaml.safe_load fails or no
    frontmatter delimiters).
  - 'type' field absent or empty.
  - 'type' value not a key in ``schema.types``.

Runs as a preflight in ``validate.py``'s per-node iteration: orchestrator
constructs a minimal NodeContext (text + base context only), dispatches
this check, and short-circuits the main ``_NODE_CHECKS`` chain on any
fatal Issue. Downstream checks rely on ``ctx.fm`` / ``ctx.node_type`` /
``ctx.type_spec`` being populated, so a clean parse + valid type is a
precondition for the chain.

Origin: lifted from inline ``validate.py`` parse/type-lookup logic. The
orchestrator was hand-emitting Issues with ``check_name='frontmatter_parse'``
that pointed to no module, breaking the "every named check lives at
``scripts/checks/{name}.py``" rule. This module makes the contract honest.
"""

from checks import Issue
from lib._common import parse_frontmatter


CHECK_NAME = "frontmatter_parse"


def check(ctx):
    """Yield fatal Issues for any frontmatter / type-spec failure that
    would prevent downstream NodeContext construction. Consumes only
    ``ctx.text`` and ``ctx.schema``; ``ctx.fm`` / ``ctx.node_type`` /
    ``ctx.type_spec`` are populated by the orchestrator AFTER this check
    passes."""
    fm, _ = parse_frontmatter(ctx.text)
    if fm is None:
        yield Issue(
            ctx.rel, "error",
            "Missing or malformed YAML frontmatter",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    node_type = fm.get("type")
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
