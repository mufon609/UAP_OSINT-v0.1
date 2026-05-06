"""frontmatter-required check — per-node NodeContext check.

Verifies every frontmatter field listed in
``type_spec.frontmatter.required`` is present on the node's
frontmatter. Per-type required-field lists are declared in
``meta/schema.yaml::types.{T}.frontmatter.required``.

Assumes the orchestrator has already parsed frontmatter cleanly and
populated ``ctx.type_spec`` — fatal cases (parse failure, unknown
type) are handled upstream by ``frontmatter_parse``.

Presence-only by design: ``field not in ctx.fm`` rather than truthy.
A nullified required field (``archetype:`` with no value → None)
passes this check; the downstream value-validation
(``status_archetype_kind``) is also presence-guarded and fires on
the null value as an enum violation. Layering by role — presence
here (catches missing key), value semantics downstream (catches
present-with-bad-value, including null) — avoids double-firing on
the same defect.

LAYERING INVARIANT: don't tighten THIS check to truthy without
coordinating with ``status_archetype_kind``, and don't loosen
``status_archetype_kind`` to truthy without expanding this check's
coverage. Both must use presence-guard semantics to keep the gap
between them closed.
"""

from checks import Issue


CHECK_NAME = "frontmatter_required"


def check(ctx):
    # Direct subscript on the schema-required path. A silent
    # ``.get(..., {})`` fallback would mask schema drift (a type missing
    # the ``frontmatter:`` block would silently skip required-field
    # validation). Loud KeyError is the right failure mode.
    required = ctx.type_spec["frontmatter"]["required"]
    for field in required:
        if field not in ctx.fm:
            yield Issue(
                ctx.rel, "error",
                f"Missing required frontmatter field '{field}'",
                check_name=CHECK_NAME,
            )
