"""contracts check — kind-conditional research-artifact check.

Present on gov-contractor organization artifacts (the kind whose
existence IS a government contract). Each entry: required
{contract_number, contracting_agency, period_start, source},
optional {period_end, primary_counterparty_path, subject, value,
deliverables, note}. ``deliverables`` (when set) is a list of
``/documents/...`` paths the contract produced.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8d377c0`` (F.5a — "schema + template
+ validator + scaffolder for organization renderer"). Same
renderer-coupled-defensive shape as the F.1a / F.1b / F.2 / etc.
entry-list family — entry-shape enforcement so the F.5 renderer
can rely on the structured data when emitting the Primary
Contracts table on gov-contractor org node bodies.

Currently exercises 2 corpus artifacts: ``/organizations/arlo-
solutions`` (multi-vendor BPA + IDV awards) and ``/organizations/
sancorp-consulting`` (AAWSAP / AARO support contracts). Schema
contract_entry shape is the heaviest entry-list shape investigated
— 4 required fields (contract_number, contracting_agency,
period_start, source) + 6 optional fields (period_end,
primary_counterparty_path, subject, value, deliverables, note).
The check correspondingly carries more validation than typical
entry-list checks: deliverables list-of-paths shape check,
primary_counterparty_path leading-slash, plus the universal
entry-list helpers.

BACKLOG C6 cross-reference. Two arlo-solutions contract entries
(c10 / c11) currently carry multi-sentence analytical prose in
``value`` (intended for short dollar-string labels per the
schema spec). The prose belongs in ``.note`` per scope, but
``.note`` doesn't render on the Primary Contracts table today —
that's the BACKLOG B1 (table renderers drop .note field) gap.
C6 schedules the migration once B1 ships. This check doesn't
enforce the dollar-string shape on ``value`` — the schema's
guidance ("$22 million" / "$22M") is contributor convention, not
a mechanical constraint here. The BACKLOG entries track the
migration; this check stays at shape-only validation.

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
