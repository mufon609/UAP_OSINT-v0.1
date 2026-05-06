"""entities-referenced check — research-artifact ResearchContext check.

Cross-reference index: every named entity (person/org/document/event/
transcript/media/location/finding) the artifact mentions, with
canonical wrap_path. Universal — runs on every artifact.

References to quote ids are cross-checked against the quotes section.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "entities_referenced"

VALID_ENTITY_TYPES = {
    "person", "organization", "document", "event", "transcript",
    "media", "location", "finding",
}


def check(ctx):
    items = entries(ctx.data, "entities_referenced")
    yield from check_unique_ids(ctx.rel, items, "entities_referenced", CHECK_NAME)
    quote_ids = {q.get("id") for q in entries(ctx.data, "quotes")
                 if isinstance(q, dict)}
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "entities_referenced", i, CHECK_NAME)
        et = e.get("entity_type")
        if et is None:
            yield Issue(
                ctx.rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): missing 'entity_type'",
                check_name=CHECK_NAME,
            )
        elif et not in VALID_ENTITY_TYPES:
            yield Issue(
                ctx.rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): entity_type "
                f"{et!r} not in {sorted(VALID_ENTITY_TYPES)}",
                check_name=CHECK_NAME,
            )
        if not e.get("name"):
            yield Issue(
                ctx.rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): missing 'name'",
                check_name=CHECK_NAME,
            )
        wp = e.get("wrap_path")
        if not wp:
            yield Issue(
                ctx.rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): missing 'wrap_path'",
                check_name=CHECK_NAME,
            )
        elif not wp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): wrap_path "
                f"{wp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        refs = e.get("references", [])
        if isinstance(refs, list):
            for ri, ref in enumerate(refs):
                if not isinstance(ref, dict):
                    continue
                if "quote_id" in ref and ref["quote_id"] not in quote_ids:
                    yield Issue(
                        ctx.rel, "error",
                        f"entities_referenced[{i}] ({e.get('id')!r}) "
                        f"references[{ri}]: quote_id {ref['quote_id']!r} "
                        f"does not match any quote.id",
                        check_name=CHECK_NAME,
                    )
