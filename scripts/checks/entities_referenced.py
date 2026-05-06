"""entities-referenced check — research-artifact ResearchContext check.

Cross-reference index: every named entity (person / organization /
document / event / transcript / media / location / finding) the
artifact mentions, with its canonical wrap_path. Universal — runs on
every artifact. ``references[].quote_id`` values are cross-checked
against the artifact's quotes section.

This check is the cross-reference graph backbone:

  - ``wrap_path`` drives the broken-link registry (``link_resolution``
    walks both body links and frontmatter node-path fields against
    the same wrap-path values).
  - ``wrap_path`` drives Associated Nodes (``associate.py`` walks
    body ``[`/path`]`` wraps post-build).
  - ``stub_linking`` verifies wrap_paths actually appear as wrap-
    links in the rendered node body.

The "named-in-prose-but-not-registered" failure mode is invisible
to this check — entities lacking a wrap_path because they aren't
registered produce no signal. Contributor discipline (every interview
venue + host + transcript-to-be is registered as an entities_referenced
entry) closes that gap; see ``feedback_interview_node_entities`` in
the project memory directory.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "entities_referenced"


def check(ctx):
    valid_entity_types = ctx.schema["types"]["research-artifact"][
        "entity_entry"]["entity_type_values"]

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
        elif et not in valid_entity_types:
            yield Issue(
                ctx.rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): entity_type "
                f"{et!r} not in {sorted(valid_entity_types)}",
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
