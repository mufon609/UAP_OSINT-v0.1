"""speakers check — type-conditional research-artifact check.

Present on every transcript artifact (both kinds). Each entry:
required {name, source}, optional {role, node_link, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``6cb131a`` ("F.3b — transcript
renderer + speakers field + check #16 closure"). Same renderer-
coupled-defensive shape as the F.1a / F.1b / F.2 / F.5 / F.6
entry-list family — entry-shape enforcement so the F.3 transcript
renderer can rely on the structured Speakers section.

Universal-on-transcript scope. Applies to BOTH transcript kinds
(hearing AND other). Same kind-agnostic scope as
``participants`` (universal-on-event). Distinct from
``witnesses_testimony`` which is hearing-only.

Cross-reference surface, NOT a statement surface. Per the schema's
speakers entry: speakers names the participants in the transcript
record but doesn't carry their statements (those live in the
``quotes`` section of the same artifact, per the
statements-only-discipline). This separation matches the broader
toolkit pattern — entries here cross-reference participants;
quotes carry verbatim content.

``role`` is free-text by design. The schema lists common values
(Witness, Chair, Committee Member, Host, Interviewer, Guest,
Moderator, Presenter) but doesn't enum-restrict them — same
free-text rationale as ``affiliations.role`` and
``key_personnel.role`` (diversity of role descriptors across
transcript types can't be cleanly enum'd). The role field is
explicitly OUT of prose-drift scope per the 2026-04-21 second
scope cut (cross-reference structural descriptor; not synthesis
content) — see ``feedback_prose_drift_warnings_must_resolve.md``.

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


CHECK_NAME = "speakers"


def check(ctx):
    if not section_in_scope(ctx, "speakers"):
        return
    if "speakers" not in ctx.data:
        return

    items = entries(ctx.data, "speakers")
    yield from check_unique_ids(ctx.rel, items, "speakers", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "speakers", i, CHECK_NAME)
        if "name" not in e or not str(e.get("name") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): missing required 'name'",
                check_name=CHECK_NAME,
            )
        nl = e.get("node_link")
        if nl and not str(nl).startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): "
                f"node_link {nl!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "speakers", i, ctx.manifest_paths, CHECK_NAME,
        )
