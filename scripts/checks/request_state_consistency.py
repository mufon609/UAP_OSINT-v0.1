"""request-state-consistency check — per-artifact ResearchContext check
(foia-only).

A foia node carries two records of where the request stands that must
not tell contradictory stories: the frontmatter ``request_state`` (this
check reads it via ``ctx.target_request_state``, discovered from the
target node) and the research artifact's own ``released_records[]``.

  - ``request_state`` in {released, partial-release} with an empty (or
    absent) ``released_records[]`` → ERROR: the state claims a release
    happened but no released record is on file.
  - ``request_state`` in {denied, no-records} with a non-empty
    ``released_records[]`` → WARN, not ERROR: not necessarily wrong (an
    earlier partial release can predate a final denial on the remainder,
    or the state may simply be stale after a later release) — flagged
    for contributor review rather than blocked.

Every other ``request_state`` value (submitted, acknowledged,
processing, appealed, closed) is unconstrained here.

No-ops when ``target_type`` is not ``foia``, or ``target_request_state``
is ``None`` (target node unbuilt / unreadable — left to other checks).
"""

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "request_state_consistency"

_REQUIRES_RECORDS = {"released", "partial-release"}
_SURPRISING_WITH_RECORDS = {"denied", "no-records"}


def check(ctx):
    if ctx.target_type != "foia":
        return
    state = ctx.target_request_state
    if state is None:
        return

    count = len(entries(ctx.data, "released_records"))

    if state in _REQUIRES_RECORDS and count == 0:
        yield Issue(
            ctx.rel, "error",
            f"request_state {state!r} requires at least one "
            f"released_records entry (none present) — add the release "
            f"(with its source), or the request_state is wrong",
            check_name=CHECK_NAME,
        )
    elif state in _SURPRISING_WITH_RECORDS and count > 0:
        entry_word = "entry" if count == 1 else "entries"
        yield Issue(
            ctx.rel, "warn",
            f"request_state {state!r} but released_records carries "
            f"{count} {entry_word} — confirm request_state isn't stale "
            f"(a later release should update it), or that the entries "
            f"record an earlier partial release that predates the final "
            f"{state!r}",
            check_name=CHECK_NAME,
        )
