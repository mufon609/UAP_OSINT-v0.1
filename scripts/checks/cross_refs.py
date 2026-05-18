"""cross-refs check — whole-artifact research-artifact check.

Verifies superseded_by / contradicted_by / corroborated_by refs on
every entry across every typed section point to existing entry ids
within the artifact (or are structured external refs). Refs that
don't match any local id warn (may be external — contributor verifies);
no error so legitimate cross-artifact refs aren't false-positive'd.

Sections to scan are derived from
``schema-research-artifact.yaml::conditional_keys`` plus the
universal entry-bearing top-level sections (``quotes``,
``entities_referenced``, ``naming_quirks``). Schema is the single
source of truth — when a new conditional section ships, this check
picks it up without a Python edit. Non-list values (prose fields like
``background`` / ``credibility_notes``, dict fields like
``event_intrinsic``) flow through ``entries()`` as empty iteration,
so enumerating every conditional_key is safe.

Warn-not-error severity is intentional. The schema's
``entry_lifecycle_fields`` spec explicitly allows external refs
(``superseded_by / contradicted_by / corroborated_by ... entry id
within this artifact, or external ref``). Refs that don't resolve
locally MIGHT be cross-artifact pointers — the validator surfaces
the unresolved ref for contributor judgment without false-
positive'ing on legitimate external pointers.
"""

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "cross_refs"

# Universal entry-bearing top-level sections — present on every
# artifact regardless of target type. ``primary_sources`` is
# deliberately excluded: its entries carry no ``id`` lifecycle field
# (per primary_sources.py docstring), so cross-ref scanning would no-op
# anyway.
_UNIVERSAL_ENTRY_SECTIONS = ("quotes", "entities_referenced", "naming_quirks")


def _all_entry_sections(ctx):
    """Universal entry-bearing sections + every conditional_key from the
    schema. Non-list conditional values (prose / dict fields) iterate as
    empty via ``entries()``, so the over-enumeration is safe."""
    conditional = ctx.schema["types"]["research-artifact"]["conditional_keys"]
    return list(_UNIVERSAL_ENTRY_SECTIONS) + list(conditional.keys())


def check(ctx):
    sections = _all_entry_sections(ctx)
    all_ids = set()
    for section in sections:
        for entry in entries(ctx.data, section):
            if isinstance(entry, dict) and entry.get("id"):
                all_ids.add(entry["id"])

    for section in sections:
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
