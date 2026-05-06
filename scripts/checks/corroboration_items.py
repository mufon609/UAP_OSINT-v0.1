"""corroboration-items check — archetype/kind-conditional research-artifact check.

Present on eyewitness person artifacts (other observers of events the
person witnessed) OR encounter event artifacts (observers of this
encounter).

Each entry: required {observer_path, observation_type, source},
optional {observed_event_ref, note}.

Gating delegated to ``section_in_scope`` (schema-driven; OR-combines
the archetype + kind rules from ``conditional_keys``); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8007ef1`` (F.1a — person schema under
statements-only discipline + check #15 chronological) as one of six
original entry-list-pattern checks for the F.1a person redesign:
check_timeline, check_corroboration_items, check_program_involvement,
check_publication_record, check_vouching_chain (five archetype-
conditional surfaces) + check_chronological_tables (universal). All
six landed together to make the new structured-data person
artifacts mechanically validatable. Same renderer-coupled-defensive
pattern as ``affiliations`` (anchored at F.1b) — entry-shape
enforcement so the renderer can rely on the structured data.

Cross-reference surface, NOT a statement surface — per
``meta/conventions.md``, archetype-specific sections (Corroboration
/ Claim Inventory / Program Involvement / Publication Record) are
cross-reference / metadata surfaces. The ``.note`` field on each
entry describes *why* the cross-reference exists (e.g., "Other
F/A-18F pilot in Fravor's 2-plane flight; testimony confirms
wingman also lost visual at intercept") and is out of prose-drift
scope per the 2026-04-21 second scope cut — the note's descriptor
pool isn't anchored to a single source.

Schema scope expansion at C15: originally scoped to eyewitness
archetype only (F.1a). Commit ``dc95d39`` (C15) added the OR-
combine to cover encounter event kind as well — the OR-disjunction
case that was one of the canonical motivations for the
``required_when_any_of`` grammar upgrade (witnesses_testimony was
the AND-conjunction case anchored in iff_section's investigation).

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through both the C15 scope expansion
and the per-module migration.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "corroboration_items"


def check(ctx):
    if not section_in_scope(ctx, "corroboration_items"):
        return
    if "corroboration_items" not in ctx.data:
        return

    # Schema-driven enum: ``observation_type`` values come from
    # ``corroboration_entry.observation_type_values`` (different value
    # set than ``quote_entry.observation_type_values`` despite the
    # shared field name — corroboration is testimonial/instrumented/
    # government-statement/documentary; quote is direct/relayed).
    valid_observation_types = ctx.schema["types"]["research-artifact"][
        "corroboration_entry"]["observation_type_values"]

    items = entries(ctx.data, "corroboration_items")
    yield from check_unique_ids(ctx.rel, items, "corroboration_items", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "corroboration_items", i, CHECK_NAME)
        for field in ("observer_path", "observation_type"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"corroboration_items[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        ot = e.get("observation_type")
        if ot and ot not in valid_observation_types:
            yield Issue(
                ctx.rel, "error",
                f"corroboration_items[{i}] ({e.get('id')!r}): "
                f"observation_type {ot!r} not in {sorted(valid_observation_types)}",
                check_name=CHECK_NAME,
            )
        op = e.get("observer_path")
        if op and not op.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"corroboration_items[{i}] ({e.get('id')!r}): "
                f"observer_path {op!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "corroboration_items", i, ctx.manifest_paths, CHECK_NAME,
        )
