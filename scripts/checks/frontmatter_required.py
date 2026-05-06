"""frontmatter-required check — per-node NodeContext check.

Verifies every frontmatter field listed in ``type_spec.frontmatter.required``
is present on the node's frontmatter. Per-type required field lists are
declared in ``meta/schema.yaml``.

Lift from validate.py validate_node (C11 session-3 migration). Assumes
the orchestrator has already validated frontmatter parsed cleanly and
type_spec is non-None (fatal cases handled upstream so per-check
defensive coding stays minimal).
"""

from checks import Issue


CHECK_NAME = "frontmatter_required"


def check(ctx):
    required = ctx.type_spec.get("frontmatter", {}).get("required", [])
    for field in required:
        if field not in ctx.fm:
            yield Issue(
                ctx.rel, "error",
                f"Missing required frontmatter field '{field}'",
                check_name=CHECK_NAME,
            )
