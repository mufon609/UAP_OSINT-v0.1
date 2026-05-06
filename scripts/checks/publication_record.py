"""publication-record check — archetype-conditional research-artifact check.

Present on reporter person artifacts. Each entry: required
{publication, outlet, date, source}, optional {node_link, beat, note}.

Shape-only: no enums. publication / outlet / date are all free-text
source-attested fields — the entry defers vocabulary to the
publishing record itself rather than imposing a closed enum.

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


CHECK_NAME = "publication_record"


def check(ctx):
    if not section_in_scope(ctx, "publication_record"):
        return
    if "publication_record" not in ctx.data:
        return

    items = entries(ctx.data, "publication_record")
    yield from check_unique_ids(ctx.rel, items, "publication_record", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "publication_record", i, CHECK_NAME)
        for field in ("publication", "outlet", "date"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"publication_record[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        yield from require_source_dict(
            ctx.rel, e, "publication_record", i, ctx.manifest_paths, CHECK_NAME,
        )
