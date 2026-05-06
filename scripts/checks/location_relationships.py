"""location-relationships check — type-conditional research-artifact check.

Present on location artifacts. Heterogeneous entity_path target
(person / organization / document / event / transcript / media /
location / finding) — locations connect to anything the primary
source attests. Each entry: required {entity_path, relationship,
source}, optional {flagged, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``5a67ec1`` (F.6a — "schema +
validator + scaffolder for location-type research artifacts").
Same renderer-coupled-defensive shape as the F.1a / F.1b / F.2 /
F.5 entry-list family; F.6 added location-specific structured
fields (ownership_timeline, top_scope_activity,
location_relationships) when locations gained Phase II rendering.

UNIQUE design choice: heterogeneous target types. This is the ONLY
``relationship_entry`` shape in the schema that allows ANY entity
type as the target. Other relationship-style checks constrain
their target to a specific type:

  - ``relationships`` (person artifact): person → person
  - ``org_relationships`` (organization artifact): org → org
  - ``affiliations`` (person artifact): person → organization
  - ``location_relationships`` (this check): location → anything

Locations are inherently heterogeneous in their cross-references —
they connect to owners (person / organization), investigators,
documented events, on-site media, adjacent locations, and
findings. Per the schema entry comment: "because locations
connect to anything the primary source attests."

Free-text ``relationship`` field (NOT an enum). Unlike
``participants.capacity`` (closed enum, drives renderer sub-
grouping) or ``org_relationships.relationship_type`` (closed enum,
8 values + ``other``), ``location_relationships.relationship`` is
contributor prose — typical values include "Current owner",
"Conducted 1996-2004 investigation", "Site of documented
incident". The heterogeneous target types create combinatorial
complexity that a closed enum can't capture cleanly; free text
fits the cross-reference role at the cost of mechanical sub-
grouping.

The check accordingly validates only the entity_path shape (must
start with "/"); it does NOT validate the entity TYPE because
heterogeneous types are by design. Path-target validity is
implicitly enforced via ``link_resolution``'s broken-link
registry (which catches paths that don't resolve to a real node).

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


CHECK_NAME = "location_relationships"


def check(ctx):
    if not section_in_scope(ctx, "location_relationships"):
        return
    if "location_relationships" not in ctx.data:
        return

    items = entries(ctx.data, "location_relationships")
    yield from check_unique_ids(ctx.rel, items, "location_relationships", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "location_relationships", i, CHECK_NAME)
        for field in ("entity_path", "relationship"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"location_relationships[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        ep = e.get("entity_path")
        if ep and not str(ep).startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"location_relationships[{i}] ({e.get('id')!r}): "
                f"entity_path {ep!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "location_relationships", i, ctx.manifest_paths, CHECK_NAME,
        )
