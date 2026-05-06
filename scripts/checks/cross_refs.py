"""cross-refs check — whole-artifact research-artifact check.

Verifies superseded_by / contradicted_by / corroborated_by refs on
every entry across every typed section point to existing entry ids
within the artifact (or are structured external refs). Refs that
don't match any local id warn (may be external — contributor verifies);
no error so legitimate cross-artifact refs aren't false-positive'd.

Enumerates over the full set of typed sections so newer sections
land in the cross-validation pass automatically. Update
``ALL_ENTRY_SECTIONS`` when a new typed section ships.

Origin: foundational from the initial commit (``af5f789``) with 6
sections in ALL_ENTRY_SECTIONS: quotes, claims, entities_referenced,
naming_quirks, research_gaps, rumors. The check evolved across both
axes — sections added AND sections removed — as the schema grew and
simplified.

Sections added (15 across F.1a–F.6 renderer landings):
  - F.1a (``8007ef1``): timeline, corroboration_items,
    program_involvement, publication_record, vouching_chain
  - F.1b (``491e6f3``): affiliations, relationships
  - F.2:  participants, witnesses_testimony
  - F.3:  speakers
  - F.4:  media_versioning
  - F.5:  key_personnel, org_relationships, contracts
  - F.6:  ownership_timeline, top_scope_activity,
          location_relationships

Sections removed (2):
  - ``cde69cf`` (claims[] layer elimination, 2026-04-21): claims
  - ``7ec1d61`` (Open Questions / research_gaps removal):
    research_gaps

Net 4 retained from the initial 6 + 17 added (the 2 removed were
among the original 4 not retained) = 21 sections currently in the
ALL_ENTRY_SECTIONS list.

Anchor pattern: hybrid additive-and-reductive multi-stage. Distinct
from purely-additive (``quotes``: rules accumulated across F.1a +
83b19c6 + cde69cf), purely-reductive (``artifact_top_level``: 5 keys
removed across 4 commits), and dual-evolution (``entities``:
vocabulary expanded + cross-ref simplified + discipline evolved).
``cross_refs`` evolved in BOTH directions as new typed sections
shipped via F.1a–F.6 AND legacy sections shed during claims-
elimination + Open Questions removal.

Warn-not-error severity is intentional. The schema's
``entry_lifecycle_fields`` spec explicitly allows external refs
(``superseded_by / contradicted_by / corroborated_by ... entry id
within this artifact, or external ref``). Refs that don't resolve
locally MIGHT be cross-artifact pointers — the validator surfaces
the unresolved ref for contributor judgment without false-
positive'ing on legitimate external pointers. The cross-artifact
resolver work for these pointers is BACKLOG A3 / E.3 (deferred).

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through both the section-list
expansions and the C11 migration.
"""

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "cross_refs"

# Every entry-bearing typed section that participates in lifecycle
# field + cross-ref checks. A section listed here need not be present
# on every artifact — presence is gated by type / kind / archetype
# rules at the per-section check level. ``entries()`` returns [] for
# absent sections, so enumerating all sections is safe regardless of
# which ones any given artifact carries.
ALL_ENTRY_SECTIONS = [
    "quotes",
    "entities_referenced",
    "naming_quirks",
    "rumors",
    "timeline",
    "affiliations",
    "relationships",
    "corroboration_items",
    "program_involvement",
    "publication_record",
    "vouching_chain",
    "participants",
    "witnesses_testimony",
    "speakers",
    "media_versioning",
    "key_personnel",
    "org_relationships",
    "contracts",
    "ownership_timeline",
    "top_scope_activity",
    "location_relationships",
]


def check(ctx):
    all_ids = set()
    for section in ALL_ENTRY_SECTIONS:
        for entry in entries(ctx.data, section):
            if isinstance(entry, dict) and entry.get("id"):
                all_ids.add(entry["id"])

    for section in ALL_ENTRY_SECTIONS:
        for i, entry in enumerate(entries(ctx.data, section)):
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id", "?")
            for field in ("superseded_by", "contradicted_by"):
                val = entry.get(field)
                if val and isinstance(val, str) and val not in all_ids:
                    yield Issue(
                        ctx.rel, "warn",
                        f"{section}[{i}] ({eid!r}): {field} {val!r} does "
                        f"not match any entry id in this artifact (may "
                        f"be external ref — verify)",
                        check_name=CHECK_NAME,
                    )
            corrob = entry.get("corroborated_by", [])
            if isinstance(corrob, list):
                for ref in corrob:
                    if isinstance(ref, str) and ref not in all_ids:
                        yield Issue(
                            ctx.rel, "warn",
                            f"{section}[{i}] ({eid!r}): corroborated_by "
                            f"ref {ref!r} does not match any entry id "
                            f"(may be external ref — verify)",
                            check_name=CHECK_NAME,
                        )
