"""naming-quirks check — research-artifact ResearchContext check.

Source-form vs canonical-form variance log. Each entry records an
``observed`` form (in source) + ``canonical`` form + resolution
(preserve-as-sic-in-quotes / use-canonical / disputed / unresolved)
+ source path. Universal — runs on every artifact.

Use case: when a source uses a non-canonical form (auto-caption typo,
OCR artifact, alias-of-record), silently substituting the canonical
form in ``quotes.text`` would break the verbatim-quote check. The
naming_quirks entry preserves the variance so the contributor-
discipline workflow has structured backing. The discipline itself
(when to preserve-as-sic vs use-canonical, when to add a reader-
visible prose flag) lives in ``meta/conventions.md`` and the
feedback memories.

This check enforces the entry-shape and resolution-enum.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "naming_quirks"


def check(ctx):
    valid_resolutions = ctx.schema["types"]["research-artifact"][
        "naming_quirk_entry"]["resolution_values"]

    items = entries(ctx.data, "naming_quirks")
    yield from check_unique_ids(ctx.rel, items, "naming_quirks", CHECK_NAME)
    for i, nq in enumerate(items):
        if not isinstance(nq, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, nq, "naming_quirks", i, CHECK_NAME)
        for field in ("observed", "canonical", "location", "source_path", "resolution"):
            if field not in nq:
                yield Issue(
                    ctx.rel, "error",
                    f"naming_quirks[{i}] ({nq.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        res = nq.get("resolution")
        if res is not None and res not in valid_resolutions:
            yield Issue(
                ctx.rel, "error",
                f"naming_quirks[{i}] ({nq.get('id')!r}): resolution {res!r} "
                f"not in {sorted(valid_resolutions)}",
                check_name=CHECK_NAME,
            )
        sp = nq.get("source_path")
        if sp and sp not in ctx.manifest_paths:
            yield Issue(
                ctx.rel, "error",
                f"naming_quirks[{i}] ({nq.get('id')!r}): source_path "
                f"{sp!r} not in sources/manifest.yaml",
                check_name=CHECK_NAME,
            )
