"""frontmatter-required check — per-node NodeContext check.

Verifies every frontmatter field listed in ``type_spec.frontmatter.required``
is present on the node's frontmatter. Per-type required-field lists are
declared in ``meta/schema.yaml::types.{T}.frontmatter.required``.

Assumes the orchestrator has already parsed frontmatter cleanly and
populated ``ctx.type_spec`` — fatal cases (parse failure, unknown type)
are handled upstream, so this check stays minimal and assumes both
fields are non-None.
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
