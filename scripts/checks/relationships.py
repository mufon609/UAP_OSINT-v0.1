"""relationships check — type-conditional research-artifact check.

Person-to-person relationships. Present on person artifacts. Each
entry: required {person_path, relationship, source}, optional
{flagged, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``491e6f3`` (F.1b — person renderer
in build-from-research.py + five person-required artifact keys),
alongside affiliations. Both required for the F.1b person renderer
to emit the Affiliations + Relationships tables with Confirmed /
Flagged splits. Same renderer-coupled-defensive shape as
affiliations; F.1b extended the D.4-era entry-list pattern to
affiliations + relationships when the renderer required structured
data.

Constrained to person→person targets. ``person_path`` must point
to a /people/... path; "/" prefix is the only structural validation.
``relationship`` is free-text — same rationale as
``location_relationships.relationship`` (heterogeneous human
relationship vocabulary that closed enum can't capture; "flying
partner", "disclosure collaborator", "advisor", "superior",
"colleague", "source" per the schema's listed examples).

Distinct from sibling relationship-style checks via target type:

  - ``relationships`` (this check): person → person
  - ``affiliations``: person → organization
  - ``org_relationships``: org → org
  - ``location_relationships``: location → anything (heterogeneous)

Confirmed/Flagged split rendering inherited from F.1b's renderer
via the entry's optional ``flagged`` boolean field.

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


CHECK_NAME = "relationships"


def check(ctx):
    if not section_in_scope(ctx, "relationships"):
        return
    if "relationships" not in ctx.data:
        return

    items = entries(ctx.data, "relationships")
    yield from check_unique_ids(ctx.rel, items, "relationships", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "relationships", i, CHECK_NAME)
        for field in ("person_path", "relationship"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"relationships[{i}] ({e.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        pp = e.get("person_path")
        if pp and not pp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"relationships[{i}] ({e.get('id')!r}): "
                f"person_path {pp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "relationships", i, ctx.manifest_paths, CHECK_NAME,
        )
