"""cross-refs check — whole-artifact research-artifact check.

Verifies superseded_by / contradicted_by / corroborated_by refs on
every entry across every typed section point to existing entry ids
within the artifact (or are structured external refs). Refs that
don't match any local id warn (may be external — contributor verifies);
no error so legitimate cross-artifact refs aren't false-positive'd.

Enumerates over the full set of typed sections so newer sections
land in the cross-validation pass automatically. Update
``ALL_ENTRY_SECTIONS`` when a new typed section ships.
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
    "uap_scope_activity",
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
