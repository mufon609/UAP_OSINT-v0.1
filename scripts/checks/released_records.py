"""released-records check — type-conditional research-artifact check (foia).

Present on foia artifacts (empty list while nothing has been released).
Each entry: required {document_path, source}, optional {release_date,
disposition, exemptions, pages, release_label}, plus the universal
lifecycle fields.

  - ``document_path`` → a ``/documents/{slug}`` path (stub permitted —
    an unbuilt target lands on the broken-link registry once rendered);
    no duplicates within the list.
  - ``disposition`` → ERROR outside
    ``released_record_entry.disposition_values`` when set.
  - ``exemptions`` → list of non-empty strings when set.
  - ``release_date`` → ISO ``YYYY-MM-DD`` / ``YYYY-MM`` when set (the
    rendered ``Date Released`` column is chronologically checked).
  - ``source`` → dict with path + location, path in the manifest.

The document side's back-pointer (frontmatter ``released_via``) is held
to this list by ``released_via_consistency``.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

import re

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "released_records"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
_DOC_PATH = re.compile(r"^/documents/[^/\s]+$")


def check(ctx):
    if not section_in_scope(ctx, "released_records"):
        return
    if "released_records" not in ctx.data:
        return

    valid_dispositions = ctx.schema["types"]["research-artifact"][
        "released_record_entry"]["disposition_values"]
    items = entries(ctx.data, "released_records")
    yield from check_unique_ids(ctx.rel, items, "released_records", CHECK_NAME)
    seen_paths = set()
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        yield from check_lifecycle_fields(ctx.rel, e, "released_records", i, CHECK_NAME)

        dp = e.get("document_path")
        if not isinstance(dp, str) or not _DOC_PATH.match(dp.strip()):
            yield Issue(
                ctx.rel, "error",
                f"released_records[{i}] ({eid!r}): document_path {dp!r} must "
                f"be a /documents/{{slug}} node path",
                check_name=CHECK_NAME,
            )
        elif dp.strip() in seen_paths:
            yield Issue(
                ctx.rel, "error",
                f"released_records[{i}] ({eid!r}): duplicate document_path {dp!r}",
                check_name=CHECK_NAME,
            )
        else:
            seen_paths.add(dp.strip())

        disp = e.get("disposition")
        if disp is not None and disp not in valid_dispositions:
            yield Issue(
                ctx.rel, "error",
                f"released_records[{i}] ({eid!r}): disposition {disp!r} not in "
                f"{valid_dispositions}",
                check_name=CHECK_NAME,
            )

        ex = e.get("exemptions")
        if ex is not None and (
            not isinstance(ex, list)
            or not all(isinstance(x, str) and x.strip() for x in ex)
        ):
            yield Issue(
                ctx.rel, "error",
                f"released_records[{i}] ({eid!r}): exemptions must be a list "
                f"of citation strings as the response prints them",
                check_name=CHECK_NAME,
            )

        rd = e.get("release_date")
        if rd is not None and not _ISO_DATE.match(str(rd).strip()):
            yield Issue(
                ctx.rel, "error",
                f"released_records[{i}] ({eid!r}): release_date {rd!r} must be "
                f"YYYY-MM-DD (or YYYY-MM)",
                check_name=CHECK_NAME,
            )

        yield from require_source_dict(
            ctx.rel, e, "released_records", i, ctx.manifest_paths, CHECK_NAME,
        )
