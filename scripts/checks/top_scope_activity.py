"""top-scope-activity check — type-conditional research-artifact check.

Present on location artifacts. Tracks documented institutional
activity within the topic's scope at the location (on this UAP
fork: NIDS investigations, AAWSAP / BAASS contract work, Fugal-
era research, etc.); popular lore without primary-source backing
belongs in ``rumors``, not here.

Each entry: required {period_start, activity, source}, optional
{period_end, actor_paths (list), note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``5a67ec1`` (F.6a — "schema +
validator + scaffolder for location-type research artifacts").
Same anchor as ``ownership_timeline`` and
``location_relationships``; F.6a added all three location-specific
structured fields together.

Topic-specific scope filter. The section's load-bearing
distinction is institutional-vs-popular: only documented
institutional activity within the topic's scope belongs here;
popular lore goes in ``rumors``. Unique among entry-list checks
in carrying this contributor-discipline distinction explicitly
in the schema + docstring. The check itself enforces shape only;
the institutional-vs-popular distinction is contributor judgment
at authoring time.

Topic-neutralized at C22 (commit ``ffad3ed``). Field name was
formerly ``uap_scope_activity``; the rename to
``top_scope_activity`` (and its sibling ``top_relevance`` on
person artifacts) decoupled the field key from the UAP-specific
display name. The rendered section header
(``## UAP-Scope Activity`` on this fork) is now composed at
render time from ``meta/topic/overview.md::display_name`` via
``load_topic()`` — see ``scripts/build-from-research.py``
``render_top_scope_activity``. A fork sets a different
``display_name`` and the renderer substitutes accordingly without
touching this check, the schema field key, or any artifact data.

Period-bearing pattern. Same period_start / period_end shape as
``ownership_timeline`` (F.6a sibling), ``key_personnel`` (F.5a),
``contracts`` (F.5a), and ``affiliations`` (F.1b). All five
share the pending "known start, unknown end (but not ongoing)"
research-queue thread.

actor_paths multi-path validation. Optional list of "/" paths.
Same shape as ``contracts.deliverables``. Each list element
validated as a string starting with "/".

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


CHECK_NAME = "top_scope_activity"


def check(ctx):
    if not section_in_scope(ctx, "top_scope_activity"):
        return
    if "top_scope_activity" not in ctx.data:
        return

    items = entries(ctx.data, "top_scope_activity")
    yield from check_unique_ids(ctx.rel, items, "top_scope_activity", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "top_scope_activity", i, CHECK_NAME)
        for field in ("period_start", "activity"):
            if field not in e or not str(e.get(field) or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"top_scope_activity[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        paths = e.get("actor_paths") or []
        if paths and not isinstance(paths, list):
            yield Issue(
                ctx.rel, "error",
                f"top_scope_activity[{i}] ({e.get('id')!r}): "
                f"actor_paths must be a list (got {type(paths).__name__})",
                check_name=CHECK_NAME,
            )
        elif isinstance(paths, list):
            for j, p in enumerate(paths):
                if not isinstance(p, str) or not p.startswith("/"):
                    yield Issue(
                        ctx.rel, "error",
                        f"top_scope_activity[{i}] ({e.get('id')!r}): "
                        f"actor_paths[{j}] must be a repo path starting "
                        f"with '/' (got {p!r})",
                        check_name=CHECK_NAME,
                    )
        yield from require_source_dict(
            ctx.rel, e, "top_scope_activity", i, ctx.manifest_paths, CHECK_NAME,
        )
