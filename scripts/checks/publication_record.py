"""publication-record check — archetype-conditional research-artifact check.

Present on reporter person artifacts. Each entry: required
{publication, outlet, date, source}, optional {node_link, beat, note}.
Absent on other archetypes.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "publication_record"


def check(ctx):
    if ctx.target_type is None:
        return
    expected = ctx.target_type == "person" and ctx.target_archetype == "reporter"
    if not expected:
        if "publication_record" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'publication_record' section should not be present "
                f"(belongs only on reporter person artifacts)",
                check_name=CHECK_NAME,
            )
        return
    if "publication_record" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'publication_record' section missing "
            f"(target archetype is 'reporter', which requires it)",
            check_name=CHECK_NAME,
        )
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
