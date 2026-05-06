"""naming-quirks check — research-artifact ResearchContext check.

Source-form vs canonical-form variance log: each entry records an
``observed`` form (in source) + ``canonical`` form + resolution
(preserve-as-sic-in-quotes / use-canonical / disputed / unresolved)
+ source path. Universal — runs on every artifact.

Origin: foundational from the initial commit (``af5f789``). Schema
entry shape, check function, and resolution enum all complete from
day one — the naming-variance use case was anticipated by the
toolkit's design (af5f789's ``naming_quirk_entry`` schema comment
already used "Leslie Keane → Leslie Kean" as the canonical example).
The check has been stable since.

The CONTRIBUTOR DISCIPLINE around the check evolved through specific
incidents even as the check shape didn't change:

  - F.1c Fravor pilot surfaced source-form vs canonical-form
    variance — the "Lue" Elizondo case: Fravor's testimony uses
    "Lue" (twice in sworn testimony, alias-of-record), canonical is
    "Luis". Documented in
    ``feedback_prose_drift_warnings_must_resolve.md``.
  - 2026-04-22 Cluster B / Grusch v2 surfaced auto-caption typos
    requiring ``preserve-as-sic-in-quotes`` (Bigalow Aerospace,
    lockie Martin, fraver, prinston, nits, etc. — silently
    substituting canonical would break the verbatim-quote check
    because the source bytes contain the typo).
  - 2026-05-05 (commit ``13f9e91``) codified the three-step
    contributor discipline for OCR-scan sources in
    ``meta/conventions.md``: (1) log each artifact as a
    naming_quirks entry, (2) preserve the source form verbatim in
    quote.text, (3) add a reader-visible prose flag in description
    / credibility_notes (since naming_quirks entries themselves
    don't render on node bodies — see
    ``feedback_reader_visibility_discipline.md``).

The check enforces the entry-shape and resolution-enum so the
contributor-discipline workflow has structured backing; the
discipline itself lives in conventions.md and the feedback memories.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.

Anchor pattern: stable check, evolving discipline. Distinct from
the multi-stage rule-accumulation pattern of ``quotes`` (where the
CHECK accumulated rules across F.1a + 83b19c6 + cde69cf); here the
check stayed fixed while the contributor practices around it
adapted to surfaced incidents.
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
