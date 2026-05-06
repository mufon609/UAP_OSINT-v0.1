"""naming-quirks check — research-artifact ResearchContext check.

Source-form vs canonical-form variance log: each entry records an
``observed`` form (in source) + ``canonical`` form + resolution
(preserve-as-sic-in-quotes / use-canonical / disputed / unresolved)
+ source path. Universal — runs on every artifact.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "naming_quirks"

VALID_RESOLUTIONS = {
    "preserve-as-sic-in-quotes", "use-canonical", "disputed", "unresolved",
}


def check(ctx):
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
        if res is not None and res not in VALID_RESOLUTIONS:
            yield Issue(
                ctx.rel, "error",
                f"naming_quirks[{i}] ({nq.get('id')!r}): resolution {res!r} "
                f"not in {sorted(VALID_RESOLUTIONS)}",
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
