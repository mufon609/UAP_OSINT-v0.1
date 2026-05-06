"""speakers check — type-conditional research-artifact check.

Present on every transcript artifact (both kinds). Each entry:
required {name, source}, optional {role, node_link, note}.

Cross-reference surface, NOT a statement surface — speakers names
the participants in the transcript record; their actual statements
live in the artifact's ``quotes`` section per the statements-only
discipline.

``role`` is free-text. Common values (Witness, Chair, Committee
Member, Host, Interviewer, Guest, Moderator, Presenter) are listed
in the schema but not enum-restricted — diversity of role
descriptors across transcript types can't be cleanly enum'd. The
role field is OUT of prose-drift scope (cross-reference structural
descriptor, not synthesis content).

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


CHECK_NAME = "speakers"


def check(ctx):
    if not section_in_scope(ctx, "speakers"):
        return
    if "speakers" not in ctx.data:
        return

    items = entries(ctx.data, "speakers")
    yield from check_unique_ids(ctx.rel, items, "speakers", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "speakers", i, CHECK_NAME)
        if "name" not in e or not str(e.get("name") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): missing required 'name'",
                check_name=CHECK_NAME,
            )
        nl = e.get("node_link")
        if nl and not str(nl).startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): "
                f"node_link {nl!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "speakers", i, ctx.manifest_paths, CHECK_NAME,
        )
