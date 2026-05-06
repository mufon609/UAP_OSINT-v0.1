"""witnesses-testimony check — kind-conditional research-artifact check.

Present on hearing-kind event artifacts (type=event AND kind=hearing —
NOT on transcript-hearings, where ``hearing`` is also a kind value).
Cross-reference table mapping witnesses to their oath status +
transcript / written-testimony nodes; what a hearing "established" is
the verbatim record carried by the linked nodes, so the event navigates
to them rather than paraphrasing.

Each entry: required {witness_path, oath_status, source}, optional
{transcript_node, written_testimony_node, note}.

The schema gate is the canonical AND-conjunction case for
``required_when_any_of``:

    witnesses_testimony:
      required_when_any_of:
        - target_node_type_in: [event]
          target_node_kind_in: [hearing]

Both fields must match for the section to be in scope. Gating
delegated to ``section_in_scope`` (schema-driven); placement errors
come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "witnesses_testimony"


def check(ctx):
    if not section_in_scope(ctx, "witnesses_testimony"):
        return
    if "witnesses_testimony" not in ctx.data:
        return

    valid_oath_status = ctx.schema["types"]["research-artifact"][
        "witnesses_testimony_entry"]["oath_status_values"]

    items = entries(ctx.data, "witnesses_testimony")
    yield from check_unique_ids(ctx.rel, items, "witnesses_testimony", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "witnesses_testimony", i, CHECK_NAME)
        for field in ("witness_path", "oath_status"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        wp = e.get("witness_path")
        if wp and not wp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"witness_path {wp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        oath = e.get("oath_status")
        if oath and oath not in valid_oath_status:
            yield Issue(
                ctx.rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"oath_status {oath!r} not in {sorted(valid_oath_status)}",
                check_name=CHECK_NAME,
            )
        for optional_path_field in ("transcript_node", "written_testimony_node"):
            v = e.get(optional_path_field)
            if v and not v.startswith("/"):
                yield Issue(
                    ctx.rel, "error",
                    f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                    f"{optional_path_field} {v!r} must start with '/'",
                    check_name=CHECK_NAME,
                )
        yield from require_source_dict(
            ctx.rel, e, "witnesses_testimony", i, ctx.manifest_paths, CHECK_NAME,
        )
