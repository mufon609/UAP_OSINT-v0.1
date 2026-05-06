"""vouching-chain check — archetype-conditional research-artifact check.

Present on whistleblower person artifacts. Each entry: required
{voucher_path, attestation, source}, optional {evidentiary_basis,
confidence, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8007ef1`` (F.1a — person schema under
statements-only discipline) as one of the four archetype-conditional
checks landed together for the F.1a redesign (alongside
corroboration_items, program_involvement, publication_record).
Same renderer-coupled-defensive shape as its siblings.

Two CLOSED enum fields:

  - ``evidentiary_basis``: {primary-source, sworn-testimony,
    on-record, self-attested, secondary}. Categorizes how the
    voucher knows what they're attesting.
  - ``confidence``: {high, medium, low}. Contributor's evidentiary
    confidence in the vouching.

Both shared with ``program_involvement`` (which uses the same
evidentiary_basis + confidence enums); the vocabulary represents the
toolkit's common evidentiary-quality classification, applied
wherever a credibility-attestation cross-reference exists.

Schema-vs-renderer drift fixed during this C17 investigation. Two
schema comments previously claimed Vouching Chain "renders inside
``## Credibility Notes``" or "appended to this section's content";
the actual ``render_vouching_chain`` in build-from-research.py emits
it as a STANDALONE ``## Vouching Chain`` H2 section between
Credibility Notes and Associated Nodes (the renderer's own comment
explicitly confirms this is the design, "to preserve the document
structure"). Schema comments updated to match the renderer in this
commit; the check itself was always shape-only and never depended
on the rendering placement, so no validator change was needed.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "vouching_chain"


def check(ctx):
    if not section_in_scope(ctx, "vouching_chain"):
        return
    if "vouching_chain" not in ctx.data:
        return

    # Shared research-artifact-level enums (also consumed by
    # program_involvement).
    research_artifact = ctx.schema["types"]["research-artifact"]
    valid_evidentiary_basis = research_artifact["evidentiary_basis_values"]
    valid_confidence = research_artifact["confidence_values"]

    items = entries(ctx.data, "vouching_chain")
    yield from check_unique_ids(ctx.rel, items, "vouching_chain", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "vouching_chain", i, CHECK_NAME)
        for field in ("voucher_path", "attestation"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"vouching_chain[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        vp = e.get("voucher_path")
        if vp and not vp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"voucher_path {vp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        eb = e.get("evidentiary_basis")
        if eb and eb not in valid_evidentiary_basis:
            yield Issue(
                ctx.rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"evidentiary_basis {eb!r} not in {sorted(valid_evidentiary_basis)}",
                check_name=CHECK_NAME,
            )
        conf = e.get("confidence")
        if conf and conf not in valid_confidence:
            yield Issue(
                ctx.rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"confidence {conf!r} not in {sorted(valid_confidence)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "vouching_chain", i, ctx.manifest_paths, CHECK_NAME,
        )
