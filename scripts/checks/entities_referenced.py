"""entities-referenced check — research-artifact ResearchContext check.

Cross-reference index: every named entity (person/org/document/event/
transcript/media/location/finding) the artifact mentions, with
canonical wrap_path. Universal — runs on every artifact.

References to quote ids are cross-checked against the quotes section.

Origin: foundational from the initial commit (``af5f789``) with 6
entity types and BOTH ``quote_id`` + ``claim_id`` cross-references.
The check evolved across both axes — type vocabulary AND cross-
reference shape — as the surrounding system changed:

  - Type vocabulary expanded at ``26969ba`` (source-taxonomy
    consolidation): added ``transcript`` and ``media`` types
    alongside the schema additions; ``book`` was removed as a
    separate type (absorbed into ``document`` via ``doc_form:
    book``). Entity-type list went from 6 → 8 values.
  - Cross-reference layer simplified at ``cde69cf`` (claims[] layer
    elimination, 2026-04-21): the ``claim_id`` cross-reference loop
    was removed when ``claims[]`` was eliminated repo-wide. Today
    only ``quote_id`` cross-references remain.

The CONTRIBUTOR DISCIPLINE around the check also evolved through
real incidents. The 2026-04-22 alex-dietrich rebuild surfaced the
"named in prose but not registered" failure mode: CBS 60 Minutes,
the five long-form podcast venues, and their hosts/interviewers
were mentioned in Timeline events and quote contexts but absent
from entities_referenced. The check itself doesn't catch this —
``stub_linking`` catches "registered but not linked" (the inverse
direction); the "named-without-registered" case is invisible
because the check has no signal for entities that lack a wrap_path
because they aren't registered. Documented in
``feedback_interview_node_entities``: every interview venue + host
+ transcript-to-be must be registered as entities_referenced
entries with wrap_path. The fix bumped the Dietrich broken-link
count from 17 → 36 — each new entry corresponded to a real primary-
source venue / interviewer / transcript the node cited.

This check is the cross-reference graph backbone:

  - ``wrap_path`` drives the broken-link registry (``link_resolution``
    walks both body links and frontmatter node-path fields against
    the same wrap-path values)
  - ``wrap_path`` drives Associated Nodes (associate.py walks body
    ``[`/path`]`` wraps post-build)
  - ``stub_linking`` verifies wrap_paths actually appear as wrap-
    links in the rendered node body
  - This check verifies the entry-shape so all three downstream
    consumers can rely on it

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the 26969ba taxonomy expansion,
the cde69cf claim-id removal, and the per-module migration.

Anchor pattern: dual evolution. Multi-stage check (rule accumulation
across type-vocabulary expansion + claim-id removal) AND evolving
discipline (contributor practices around "every-venue-registered"
from the alex-dietrich pilot). First investigated check spanning
both the multi-stage-check pattern (cf. ``quotes``) and the
evolving-discipline pattern (cf. ``naming_quirks``).
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
