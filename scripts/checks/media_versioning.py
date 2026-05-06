"""media-versioning check — type-conditional research-artifact check.

Present on every media artifact. Empty list permitted for canonical /
original media; populated when the node's frontmatter has
``derivation_of`` set and the derivative differs from its parent.

Each entry: required {id, aspect, parent_form, this_form, source},
optional {note}. ``aspect`` enum {duration, encoding, metadata, content,
provenance, other} — ``other`` permitted as extensibility escape;
unknown values warn (don't error).

Empty list with ``derivation_of`` set on the target media node warns
(likely contributor-forgot-to-populate).

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at F.4a (media schema + check + scaffolder ship)
alongside the new media node type per the post-Step-D source-taxonomy
consolidation (commit ``26969ba``). Same renderer-coupled-defensive
shape as the F.1a / F.1b / F.2 / F.5 entry-list family, but with two
distinctive features that set it apart:

  1. CROSS-FRONTMATTER AWARENESS via ``ctx.target_derivation_of``.
     When the target media node's frontmatter has ``derivation_of``
     set (signalling a derivative media node — e.g., DoD's official
     Gimbal cut vs. a leaked longer version), the check warns if
     media_versioning entries are empty: derivative media should
     document at least one parent/derivative difference. This is
     unique among entry-list checks — most don't read target-node
     frontmatter; they validate artifact shape only. The
     orchestrator pre-populates target_derivation_of in
     ResearchContext from the target node's frontmatter, same shape
     as how Phase III checks consume ctx.node_text /
     regenerated_body.

  2. EXTENSIBLE ENUM with WARN-ON-UNKNOWN. The ``aspect`` field
     enum {duration, encoding, metadata, content, provenance,
     other} is intentionally open — ``other`` is the documented
     escape hatch, and unknown values produce a warning (not an
     error) inviting "schema discussion" per the warn message.
     This is the CANONICAL implementation of the extensible-enum
     warn-on-unknown pattern. By contrast, ``timeline``'s category
     enum (BACKLOG C20) declares the same "extensible; warns on
     unknown values" intent in the schema but never implemented
     the warn — the timeline check enforces shape only, not
     vocabulary. C20's path 1c (canonicalize popular extensions
     in schema, then wire the warn) would model timeline's
     resolution after this check's aspect-enum implementation.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
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
