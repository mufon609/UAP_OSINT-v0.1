"""request-state check — per-node NodeContext check (foia-only).

A foia node carries two lifecycle fields that must not be conflated:
``status`` keeps the repo-wide node-status meaning (validated by
``status_archetype_kind``), while ``request_state`` records where the
records REQUEST stands. This check enforces ``request_state`` against the
closed vocabulary ``types.foia.request_state_values`` in
``meta/schema.yaml``.

Presence is ``frontmatter_required``'s job (``request_state`` is in the
foia type's required frontmatter); this check uses the same
presence-guard semantics as ``status_archetype_kind`` — it fires whenever
the key is present, including a nullified ``request_state:`` — so the two
layers leave no gap between them.

No-ops when node_type is not ``foia``.
"""

from checks import Issue


CHECK_NAME = "request_state"


def check(ctx):
    if ctx.node_type != "foia":
        return
    if "request_state" not in ctx.fm:
        return  # frontmatter_required owns absence
    # Direct subscript: the vocabulary is declared on the foia type spec;
    # absence would be schema drift and should fail loudly.
    valid = ctx.type_spec["request_state_values"]
    value = ctx.fm["request_state"]
    if value not in valid:
        yield Issue(
            ctx.rel, "error",
            f"Invalid request_state {value!r}. Valid: {valid}",
            check_name=CHECK_NAME,
        )
