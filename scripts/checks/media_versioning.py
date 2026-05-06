"""media-versioning check — type-conditional research-artifact check.

Present on every media artifact. Empty list permitted for canonical /
original media; populated when the node's frontmatter has
``derivation_of`` set and the derivative differs from its parent.

Each entry: required {id, aspect, parent_form, this_form, source},
optional {note}. ``aspect`` enum {duration, encoding, metadata,
content, provenance, other} — ``other`` is the extensibility escape;
unknown values warn (don't error) inviting schema discussion. The
extensible-enum warn-on-unknown pattern fits because aspect doesn't
drive renderer routing.

Cross-frontmatter awareness: when the target media node's
frontmatter has ``derivation_of`` set (signalling a derivative
media node — e.g., DoD's official Gimbal cut vs. a leaked longer
version), an empty media_versioning warns. The orchestrator
pre-populates ``ctx.target_derivation_of`` from the target node's
frontmatter.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "media_versioning"


def check(ctx):
    if not section_in_scope(ctx, "media_versioning"):
        return
    if "media_versioning" not in ctx.data:
        return

    valid_aspect = ctx.schema["types"]["research-artifact"][
        "media_versioning_entry"]["aspect_values"]

    items = entries(ctx.data, "media_versioning")
    if ctx.target_derivation_of and not items:
        yield Issue(
            ctx.rel, "warn",
            f"media_versioning is empty but target node has "
            f"derivation_of={ctx.target_derivation_of!r} set — "
            f"derivative media nodes typically document at least one "
            f"parent/derivative difference (duration, encoding, "
            f"metadata, content, provenance). Populate media_versioning "
            f"or confirm the derivative is byte-identical to the parent "
            f"(in which case derivation_of itself may not be warranted).",
            check_name=CHECK_NAME,
        )

    yield from check_unique_ids(ctx.rel, items, "media_versioning", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "media_versioning", i, CHECK_NAME)
        for field in ("aspect", "parent_form", "this_form"):
            if field not in e or not str(e.get(field) or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"media_versioning[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        aspect = e.get("aspect")
        if aspect is not None and aspect not in valid_aspect:
            yield Issue(
                ctx.rel, "warn",
                f"media_versioning[{i}] ({e.get('id')!r}): "
                f"aspect {aspect!r} not in {sorted(valid_aspect)} — "
                f"extensible vocabulary, but unexpected values may "
                f"indicate a missing enum entry worth schema discussion.",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "media_versioning", i, ctx.manifest_paths, CHECK_NAME,
        )
