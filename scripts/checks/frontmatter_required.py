"""frontmatter-required check — per-node NodeContext check.

Verifies every frontmatter field listed in ``type_spec.frontmatter.required``
is present on the node's frontmatter. Per-type required-field lists are
declared in ``meta/schema.yaml::types.{T}.frontmatter.required``.

Assumes the orchestrator has already parsed frontmatter cleanly and
populated ``ctx.type_spec`` — fatal cases (parse failure, unknown type)
are handled upstream, so this check stays minimal and assumes both
fields are non-None.

Origin: foundational schema discipline; present in the initial commit
``af5f789`` alongside schema_version compat and id-path match. No
specific incident drove its creation — required-frontmatter
enforcement is part of the toolkit's basic invariant. Without it, a
contributor could submit a node missing ``archetype`` / ``kind`` /
``status`` / ``type`` / ``created`` and downstream archetype-
conditional or kind-conditional dispatch (in iff_section, the
per-section research-artifact checks, and the renderer) silently
mis-routes or skips entirely. The class of failure this check
protects against is dispatcher-correctness; this is the prerequisite
for every other check that gates on type_spec / archetype / kind.

Presence-only by design: ``field not in ctx.fm`` rather than truthy.
A nullified required field (``archetype:`` with no value → ``None``)
passes this check; the downstream value-validation
(``status_archetype_kind``) is presence-guarded too, so it fires on
the null value as an enum violation (None ∉ valid). Layering by
role — presence here (catches missing key), value semantics
downstream (catches present-with-bad-value, including null) — keeps
each check focused and avoids double-firing on the same defect.

The layering invariant relies on ``status_archetype_kind`` using
presence-guard semantics, not truthy. Don't tighten THIS check to
truthy without coordinating with status_archetype_kind, and don't
loosen status_archetype_kind to truthy without expanding this
check's coverage — both checks must use presence to keep the gap
between them closed. The C17 audit caught and corrected a prior
truthy-guard implementation in status_archetype_kind that opened
the gap.

Migration to per-module shape happened at commit ``60bb88d`` (C11
session 3); C18 confirmed byte-identity through that move.
"""

from checks import Issue


CHECK_NAME = "frontmatter_required"


def check(ctx):
    # Direct subscript on the schema-required path. Every node type's
    # spec carries a ``frontmatter.required`` list per schema.yaml; a
    # silent ``.get(..., {})`` fallback would mask schema drift (a type
    # missing the ``frontmatter:`` block would silently skip required-
    # field validation). Loud KeyError is the right failure mode per
    # the C21 no-silent-fallbacks principle.
    required = ctx.type_spec["frontmatter"]["required"]
    for field in required:
        if field not in ctx.fm:
            yield Issue(
                ctx.rel, "error",
                f"Missing required frontmatter field '{field}'",
                check_name=CHECK_NAME,
            )
