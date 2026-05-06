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
passes this check, but downstream value-validation checks
(``status_archetype_kind`` for the archetype / kind / status enums)
catch the null. Layering by role — presence here, value semantics
downstream — keeps each check focused and avoids double-firing on
the same defect. Don't tighten to truthy without coordinating with
the downstream enum checks.

Migration to per-module shape happened at commit ``60bb88d`` (C11
session 3); C18 confirmed byte-identity through that move.
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
