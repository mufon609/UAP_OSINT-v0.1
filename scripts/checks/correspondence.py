"""correspondence check — type-conditional research-artifact check (foia).

Present on foia artifacts. Each entry is one archived letter that moved
the request: required {date, letter_type, source}, optional {sender,
recipient, sender_path, recipient_path, tracking_number, summary}, plus
the universal lifecycle fields.

  - ``letter_type`` → ERROR outside
    ``correspondence_entry.letter_type_values``.
  - ``date`` → ERROR when not an ISO ``YYYY-MM-DD`` / ``YYYY-MM`` date
    (the rendered Correspondence and Timeline tables are chronologically
    checked; an unparseable date would sink the row).
  - ``sender_path`` / ``recipient_path`` → must start with ``/``.
  - ``source`` → dict with path + location, path in the manifest: every
    correspondence entry cites the archived letter itself.

``summary`` is contributor prose, scanned by the prose-drift check
(``types.foia.prose_drift_fields.per_entry``), not here.

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


CHECK_NAME = "correspondence"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def check(ctx):
    if not section_in_scope(ctx, "correspondence"):
        return
    if "correspondence" not in ctx.data:
        return

    valid_types = ctx.schema["types"]["research-artifact"][
        "correspondence_entry"]["letter_type_values"]
    items = entries(ctx.data, "correspondence")
    yield from check_unique_ids(ctx.rel, items, "correspondence", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        yield from check_lifecycle_fields(ctx.rel, e, "correspondence", i, CHECK_NAME)

        date = str(e.get("date") or "").strip()
        if not date:
            yield Issue(
                ctx.rel, "error",
                f"correspondence[{i}] ({eid!r}): missing required 'date'",
                check_name=CHECK_NAME,
            )
        elif not _ISO_DATE.match(date):
            yield Issue(
                ctx.rel, "error",
                f"correspondence[{i}] ({eid!r}): date {date!r} must be "
                f"YYYY-MM-DD (or YYYY-MM when only the month is attested)",
                check_name=CHECK_NAME,
            )

        lt = e.get("letter_type")
        if lt not in valid_types:
            yield Issue(
                ctx.rel, "error",
                f"correspondence[{i}] ({eid!r}): letter_type {lt!r} not in "
                f"{valid_types}",
                check_name=CHECK_NAME,
            )

        for field in ("sender_path", "recipient_path"):
            v = e.get(field)
            if v and (not isinstance(v, str) or not v.startswith("/")):
                yield Issue(
                    ctx.rel, "error",
                    f"correspondence[{i}] ({eid!r}): {field} {v!r} must start with '/'",
                    check_name=CHECK_NAME,
                )

        yield from require_source_dict(
            ctx.rel, e, "correspondence", i, ctx.manifest_paths, CHECK_NAME,
        )
