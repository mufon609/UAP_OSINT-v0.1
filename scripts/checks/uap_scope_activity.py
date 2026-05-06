"""uap-scope-activity check — type-conditional research-artifact check.

Present on location artifacts. Tracks documented institutional UAP-
scope activity at the location (NIDS investigations, AAWSAP / BAASS
contract work, Fugal-era research, etc.); popular paranormal lore
without primary-source backing belongs in ``rumors``, not here.

Each entry: required {period_start, activity, source}, optional
{period_end, actor_paths (list), note}.

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


CHECK_NAME = "uap_scope_activity"


def check(ctx):
    if not section_in_scope(ctx, "uap_scope_activity"):
        return
    if "uap_scope_activity" not in ctx.data:
        return

    items = entries(ctx.data, "uap_scope_activity")
    yield from check_unique_ids(ctx.rel, items, "uap_scope_activity", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "uap_scope_activity", i, CHECK_NAME)
        for field in ("period_start", "activity"):
            if field not in e or not str(e.get(field) or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"uap_scope_activity[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        paths = e.get("actor_paths") or []
        if paths and not isinstance(paths, list):
            yield Issue(
                ctx.rel, "error",
                f"uap_scope_activity[{i}] ({e.get('id')!r}): "
                f"actor_paths must be a list (got {type(paths).__name__})",
                check_name=CHECK_NAME,
            )
        elif isinstance(paths, list):
            for j, p in enumerate(paths):
                if not isinstance(p, str) or not p.startswith("/"):
                    yield Issue(
                        ctx.rel, "error",
                        f"uap_scope_activity[{i}] ({e.get('id')!r}): "
                        f"actor_paths[{j}] must be a repo path starting "
                        f"with '/' (got {p!r})",
                        check_name=CHECK_NAME,
                    )
        yield from require_source_dict(
            ctx.rel, e, "uap_scope_activity", i, ctx.manifest_paths, CHECK_NAME,
        )
