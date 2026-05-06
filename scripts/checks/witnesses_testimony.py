"""witnesses-testimony check — kind-conditional research-artifact check.

Present on hearing-kind event artifacts. Cross-reference table mapping
witnesses to their oath status + transcript / written testimony nodes.
Each entry: required {witness_path, oath_status, source}, optional
{transcript_node, written_testimony_node, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``13a2859`` ("F.2a — event schema:
collapse What The Hearing Established → Witnesses & Testimony
cross-reference"). The section replaced a prior synthesis-prose
section ("What The Hearing Established") that contained
contributor-written summaries of hearing outcomes — same drift
surface as the claims layer that was eliminated repo-wide.
F.2a's collapse turns the synthesis surface into a structured
cross-reference table: witnesses → oath status → transcript /
written-testimony node paths. What a hearing "established" is
now the verbatim record carried by the linked transcript +
testimony nodes; the event node navigates to them rather than
paraphrasing.

The ``witnesses_testimony`` schema gate is THE canonical AND-
conjunction case for the C15 grammar upgrade. The section belongs
on event-hearings (type=event AND kind=hearing) but NOT on
transcript-hearings (type=transcript AND kind=hearing). The
pre-C15 flat OR-keys grammar (separate
``required_when_target_node_type_in: [event]`` +
``required_when_target_node_kind_in: [hearing]`` lines top-level
OR'd) over-fired on transcript-hearings. The conjunction here
forced the grammar upgrade to ``required_when_any_of: [list of
AND-rules]``. See the iff_section module's docstring for the
broader grammar-upgrade story; this section's gate is the
schema example that codifies the conjunction:

    witnesses_testimony:
      required_when_any_of:
        - target_node_type_in: [event]
          target_node_kind_in: [hearing]

Single AND-rule under the any_of list — both fields must match for
the section to be in scope.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through both the C15 schema-grammar
upgrade and the C11 migration.
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

VALID_OATH_STATUS = {"sworn", "unsworn", "affirmation", "unknown"}


def check(ctx):
    if not section_in_scope(ctx, "witnesses_testimony"):
        return
    if "witnesses_testimony" not in ctx.data:
        return

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
        if oath and oath not in VALID_OATH_STATUS:
            yield Issue(
                ctx.rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"oath_status {oath!r} not in {sorted(VALID_OATH_STATUS)}",
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
