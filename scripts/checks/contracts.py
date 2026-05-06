"""contracts check — kind-conditional research-artifact check.

Present on gov-contractor organization artifacts (the kind whose
existence IS a government contract). Each entry: required
{contract_number, contracting_agency, period_start, source},
optional {period_end, primary_counterparty_path, subject, value,
deliverables, note}. ``deliverables`` (when set) is a list of
``/documents/...`` paths the contract produced.

The contract entry shape is the heaviest in the entry-list family
(4 required + 6 optional). This check correspondingly carries more
validation than typical entry-list checks: deliverables list-of-paths
shape check, primary_counterparty_path leading-slash, plus the
universal entry-list helpers.

The schema's ``value`` guidance ("$22 million" / "$22M") is
contributor convention; this check enforces only the entry shape, not
the dollar-string format.

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


CHECK_NAME = "contracts"


def check(ctx):
    if not section_in_scope(ctx, "contracts"):
        return
    if "contracts" not in ctx.data:
        return

    items = entries(ctx.data, "contracts")
    yield from check_unique_ids(ctx.rel, items, "contracts", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "contracts", i, CHECK_NAME)
        for field in ("contract_number", "contracting_agency", "period_start"):
            if field not in e or not str(e.get(field) or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"contracts[{i}] ({e.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        pcp = e.get("primary_counterparty_path")
        if pcp and not pcp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"contracts[{i}] ({e.get('id')!r}): "
                f"primary_counterparty_path {pcp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        deliverables = e.get("deliverables") or []
        if deliverables and not isinstance(deliverables, list):
            yield Issue(
                ctx.rel, "error",
                f"contracts[{i}] ({e.get('id')!r}): "
                f"deliverables must be a list (got {type(deliverables).__name__})",
                check_name=CHECK_NAME,
            )
        elif isinstance(deliverables, list):
            for j, d in enumerate(deliverables):
                if not isinstance(d, str) or not d.startswith("/"):
                    yield Issue(
                        ctx.rel, "error",
                        f"contracts[{i}] ({e.get('id')!r}): "
                        f"deliverables[{j}] must be a repo path starting "
                        f"with '/' (got {d!r})",
                        check_name=CHECK_NAME,
                    )
        yield from require_source_dict(
            ctx.rel, e, "contracts", i, ctx.manifest_paths, CHECK_NAME,
        )
