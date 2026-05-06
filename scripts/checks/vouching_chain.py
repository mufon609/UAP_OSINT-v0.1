"""vouching-chain check — archetype-conditional research-artifact check.

Present on whistleblower person artifacts. Each entry: required
{voucher_path, attestation, source}, optional {evidentiary_basis,
confidence, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "vouching_chain"

VALID_EVIDENTIARY_BASIS = {
    "primary-source", "sworn-testimony", "on-record", "self-attested", "secondary",
}
VALID_CONFIDENCE = {"high", "medium", "low"}


def check(ctx):
    if ctx.target_type is None:
        return
    expected = ctx.target_type == "person" and ctx.target_archetype == "whistleblower"
    if not expected:
        if "vouching_chain" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'vouching_chain' section should not be present "
                f"(belongs only on whistleblower person artifacts)",
                check_name=CHECK_NAME,
            )
        return
    if "vouching_chain" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'vouching_chain' section missing "
            f"(target archetype is 'whistleblower', which requires it)",
            check_name=CHECK_NAME,
        )
        return

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
        if eb and eb not in VALID_EVIDENTIARY_BASIS:
            yield Issue(
                ctx.rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"evidentiary_basis {eb!r} not in {sorted(VALID_EVIDENTIARY_BASIS)}",
                check_name=CHECK_NAME,
            )
        conf = e.get("confidence")
        if conf and conf not in VALID_CONFIDENCE:
            yield Issue(
                ctx.rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"confidence {conf!r} not in {sorted(VALID_CONFIDENCE)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "vouching_chain", i, ctx.manifest_paths, CHECK_NAME,
        )
