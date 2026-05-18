"""investigation_hypothesis_citation check — investigation-only research-artifact check.

Citation discipline for the speculation-tolerant prose surfaces on
investigation artifacts: each hypothesis_evaluation entry,
best_current_answer, and counter_evidence entry must carry a
non-empty ``sources[]`` rollup listing the findings or entity-node
anchors the contributor drew on.

This check replaces the prose-drift check on speculation-tolerant
surfaces. Prose-drift can't apply to investigation analytical prose
because investigations explicitly speculate beyond what any single
source attests. The structural discipline — every hypothesis
subsection lists the sources it draws on, with a brief contributor
description of each — is what makes the audit trail readable
without inline citation clutter.

Per-source validation:
  - exactly one of ``finding_path`` or ``entity_path`` (not both, not
    neither)
  - when ``entity_path`` is set, ``anchor`` must also be set
  - ``description`` field present + ≥10 chars (reasonable navigation
    aid; warn-level for descriptions 1-9 chars)

No-ops on non-investigation artifacts.
"""

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "investigation_hypothesis_citation"

_MIN_STATUS_CHARS = 10
_MAX_STATUS_CHARS = 300
_MIN_DESCRIPTION_CHARS = 10


def _check_source_entry(rel, source, container_label, idx, check_name):
    """Validate a single sources[] entry. Yields Issues for any
    violation of the finding_path xor (entity_path + anchor) +
    description discipline.
    """
    if not isinstance(source, dict):
        yield Issue(
            rel, "error",
            f"{container_label}.sources[{idx}]: must be a dict",
            check_name=check_name,
        )
        return

    has_finding = bool(source.get("finding_path"))
    has_entity = bool(source.get("entity_path"))

    if has_finding and has_entity:
        yield Issue(
            rel, "error",
            f"{container_label}.sources[{idx}]: must carry either "
            f"'finding_path' or 'entity_path', not both",
            check_name=check_name,
        )
    elif not has_finding and not has_entity:
        yield Issue(
            rel, "error",
            f"{container_label}.sources[{idx}]: must carry either "
            f"'finding_path' or 'entity_path'",
            check_name=check_name,
        )

    if has_entity and not source.get("anchor"):
        yield Issue(
            rel, "error",
            f"{container_label}.sources[{idx}]: entity_path "
            f"{source.get('entity_path')!r} requires an 'anchor' "
            f"(quote id like 'q24', or H2 section name)",
            check_name=check_name,
        )

    description = source.get("description") or ""
    if not description:
        yield Issue(
            rel, "error",
            f"{container_label}.sources[{idx}]: missing required "
            f"'description' (1-2 sentence summary of what this "
            f"source contributes)",
            check_name=check_name,
        )
    elif len(description) < _MIN_DESCRIPTION_CHARS:
        yield Issue(
            rel, "warn",
            f"{container_label}.sources[{idx}]: 'description' "
            f"shorter than {_MIN_DESCRIPTION_CHARS} chars "
            f"({description!r}); brief but readable descriptions "
            f"make the audit trail navigable",
            check_name=check_name,
        )


def _check_text_field(rel, container, field_name, container_label, check_name):
    """Yield Issue when the analytical-text field is missing or empty."""
    text = container.get(field_name) or ""
    if not text.strip():
        yield Issue(
            rel, "error",
            f"{container_label}: missing required {field_name!r} "
            f"(analytical prose must be present)",
            check_name=check_name,
        )


def _check_sources_list(rel, container, container_label, check_name):
    """Validate that container.sources[] is non-empty and each entry
    well-formed. Yields Issues for any violation."""
    sources = container.get("sources")
    if not isinstance(sources, list) or not sources:
        yield Issue(
            rel, "error",
            f"{container_label}: missing or empty 'sources' rollup. "
            f"Each speculation-tolerant prose surface must list the "
            f"findings or entity-node anchors it draws on (see "
            f"meta/conventions.md 'Three-layer evidentiary architecture').",
            check_name=check_name,
        )
        return
    for i, source in enumerate(sources):
        yield from _check_source_entry(
            rel, source, container_label, i, check_name,
        )


def check(ctx):
    if ctx.target_type != "investigation":
        return
    if not isinstance(ctx.data, dict):
        return

    # Build case-insensitive set of hypothesis ids for cross-reference
    # resolution. hypotheses[].id and hypothesis_evaluation[]
    # .hypothesis_id (and counter_evidence[].against_hypothesis_id) may
    # be authored in mixed case; the validator and renderer both
    # normalize to lowercase so a contributor case-mismatch produces
    # a clear error rather than silent degraded rendering.
    hypothesis_ids = {
        (h.get("id") or "").lower()
        for h in entries(ctx.data, "hypotheses")
        if isinstance(h, dict) and h.get("id")
    }

    # --- hypothesis_evaluation[] ---
    hypothesis_evals = entries(ctx.data, "hypothesis_evaluation")
    for i, he in enumerate(hypothesis_evals):
        if not isinstance(he, dict):
            continue
        hid = he.get("hypothesis_id") or f"index-{i}"
        label = f"hypothesis_evaluation[{i}] (hypothesis_id={hid!r})"

        # hypothesis_id is required (lifecycle check covers id; this
        # one verifies hypothesis_id specifically + cross-resolution)
        hid_value = he.get("hypothesis_id")
        if not hid_value:
            yield Issue(
                ctx.rel, "error",
                f"{label}: missing required 'hypothesis_id' "
                f"(must match an entry id in hypotheses[])",
                check_name=CHECK_NAME,
            )
        elif hid_value.lower() not in hypothesis_ids:
            yield Issue(
                ctx.rel, "error",
                f"{label}: hypothesis_id {hid_value!r} does not match "
                f"any id in hypotheses[] (case-insensitive lookup). "
                f"Known hypothesis ids: {sorted(hypothesis_ids)}",
                check_name=CHECK_NAME,
            )

        # status: free-text verdict, 10-300 chars
        status = he.get("status") or ""
        if not status.strip():
            yield Issue(
                ctx.rel, "error",
                f"{label}: missing required 'status' (free-text verdict "
                f"on this hypothesis — e.g., 'Substantiated as allegation "
                f"on record; not established as physical fact')",
                check_name=CHECK_NAME,
            )
        elif len(status) < _MIN_STATUS_CHARS:
            yield Issue(
                ctx.rel, "warn",
                f"{label}: 'status' shorter than {_MIN_STATUS_CHARS} "
                f"chars ({status!r}); verdicts should be specific enough "
                f"to communicate the evidentiary standing",
                check_name=CHECK_NAME,
            )
        elif len(status) > _MAX_STATUS_CHARS:
            yield Issue(
                ctx.rel, "warn",
                f"{label}: 'status' longer than {_MAX_STATUS_CHARS} "
                f"chars; verdicts should be a single sentence — move "
                f"longer analysis into the 'text' field",
                check_name=CHECK_NAME,
            )

        yield from _check_text_field(
            ctx.rel, he, "text", label, CHECK_NAME,
        )
        yield from _check_sources_list(
            ctx.rel, he, label, CHECK_NAME,
        )

    # --- best_current_answer (single object) ---
    # Tolerate empty/absent scaffold state — only enforce structure
    # when the contributor has begun populating the object (any non-
    # empty value triggers full validation).
    bca = ctx.data.get("best_current_answer")
    if isinstance(bca, dict) and bca:
        label = "best_current_answer"
        yield from _check_text_field(
            ctx.rel, bca, "text", label, CHECK_NAME,
        )
        yield from _check_sources_list(
            ctx.rel, bca, label, CHECK_NAME,
        )
    elif bca is not None and not isinstance(bca, dict):
        yield Issue(
            ctx.rel, "error",
            "best_current_answer: must be a dict with text + sources",
            check_name=CHECK_NAME,
        )

    # --- counter_evidence[] (optional list) ---
    counters = entries(ctx.data, "counter_evidence")
    for i, ce in enumerate(counters):
        if not isinstance(ce, dict):
            continue
        cid = ce.get("id") or f"index-{i}"
        label = f"counter_evidence[{i}] (id={cid!r})"

        against = ce.get("against_hypothesis_id")
        if not against:
            yield Issue(
                ctx.rel, "error",
                f"{label}: missing required 'against_hypothesis_id' "
                f"(must match an entry id in hypotheses[])",
                check_name=CHECK_NAME,
            )
        elif against.lower() not in hypothesis_ids:
            yield Issue(
                ctx.rel, "error",
                f"{label}: against_hypothesis_id {against!r} does not "
                f"match any id in hypotheses[] (case-insensitive "
                f"lookup). Known hypothesis ids: {sorted(hypothesis_ids)}",
                check_name=CHECK_NAME,
            )
        yield from _check_text_field(
            ctx.rel, ce, "text", label, CHECK_NAME,
        )
        yield from _check_sources_list(
            ctx.rel, ce, label, CHECK_NAME,
        )
