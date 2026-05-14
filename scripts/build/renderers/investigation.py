"""Investigation-type renderer.

Renders investigation nodes — speculation-tolerant hypothesis evaluation
consuming findings + entity-node facts. Section order: Question →
Description → Hypotheses → Cited Findings → Hypothesis Evaluation →
Open Questions → Best-Current Answer → (Counter-Evidence if populated)
→ (Closure Path when paused or populated) → (Resolution History if
populated) → Associated Nodes.

Hypothesis Evaluation, Best-Current Answer, and Counter-Evidence each
carry their own **Sources:** rollup; the
``investigation_hypothesis_citation`` check enforces non-empty rollups
on these speculation-tolerant prose surfaces.
"""

from ._common import (
    SECTION_SEP,
    _render_sources_rollup,
    _wrap_path,
    sort_by_date,
)
from ._universal import (
    render_associated_nodes,
    render_description,
)


def render_title_investigation(artifact):
    """H1 title for investigation nodes. ``document_intrinsic.full_name``
    overrides when populated; falls back to slug-derived title."""
    di = artifact.get("document_intrinsic") or {}
    name = di.get("full_name")
    if name:
        return f"# {name}\n"
    target = artifact.get("target_node") or ""
    slug = target.rsplit("/", 1)[-1] if "/" in target else target
    display = slug.replace("-", " ").title() if slug else "Investigation"
    return f"# {display}\n"


def render_question(artifact, fm):
    """`## Question` — the open question being pursued. Mirrors the
    frontmatter `question` field for at-a-glance reading on the body."""
    question = (fm.get("question") or artifact.get("question") or "").strip()
    lines = ["## Question", ""]
    if question:
        lines.append(question)
    else:
        lines.append("<!-- TODO: populate `question` in the artifact / frontmatter -->")
    return "\n".join(lines) + "\n"


def render_hypotheses(artifact):
    """`## Hypotheses` — numbered list from hypotheses[]. Each entry:
    **H{id}** — {statement}."""
    items = [h for h in (artifact.get("hypotheses") or []) if isinstance(h, dict)]
    lines = ["## Hypotheses", ""]
    if not items:
        lines.append("<!-- TODO: populate `hypotheses` in the research artifact -->")
        return "\n".join(lines) + "\n"
    for h in items:
        hid = (h.get("id") or "?").upper()
        statement = (h.get("statement") or "").strip()
        lines.append(f"- **{hid}** — {statement}")
    return "\n".join(lines) + "\n"


def render_cited_findings(artifact):
    """`## Cited Findings` — table of findings consumed by this
    investigation. Columns: Finding | Pattern | Relevance."""
    items = [c for c in (artifact.get("cited_findings") or []) if isinstance(c, dict)]
    lines = ["## Cited Findings", "",
             "| Finding | Pattern | Relevance |",
             "|---|---|---|"]
    if not items:
        lines.append("|  |  |  |")
        return "\n".join(lines) + "\n"
    for c in items:
        fp = c.get("finding_path") or ""
        wrap = _wrap_path(fp) if fp else ""
        pattern = (c.get("pattern_statement") or "").replace("|", "\\|")
        relevance = (c.get("relevance") or "").replace("|", "\\|")
        lines.append(f"| {wrap} | {pattern} | {relevance} |")
    return "\n".join(lines) + "\n"


def render_hypothesis_evaluation(artifact):
    """`## Hypothesis Evaluation` — per-hypothesis H3 cards. Each card:
    H3 heading with hypothesis statement, **Status:** verdict line,
    analytical prose, **Sources:** rollup of findings + entity anchors.

    Hypothesis-id lookup is case-insensitive (hypotheses[].id and
    hypothesis_evaluation[].hypothesis_id may be authored in mixed case;
    the renderer normalizes to lowercase for lookup and uppercases for
    display). The investigation_hypothesis_citation check enforces
    that every hypothesis_id resolves to a hypotheses[] entry."""
    items = [e for e in (artifact.get("hypothesis_evaluation") or []) if isinstance(e, dict)]
    hyps = {
        (h.get("id") or "").lower(): h
        for h in (artifact.get("hypotheses") or []) if isinstance(h, dict)
    }

    head = "## Hypothesis Evaluation\n"
    if not items:
        return head + "\n<!-- TODO: populate `hypothesis_evaluation` in the research artifact -->\n"

    blocks = []
    for e in items:
        hid_raw = e.get("hypothesis_id") or ""
        hid = hid_raw.upper()
        statement = (hyps.get(hid_raw.lower(), {}).get("statement") or "").strip()
        heading = f"### {hid} — {statement}" if statement else f"### {hid}"
        status = (e.get("status") or "").strip()
        text = (e.get("text") or "").strip()
        sources_block = _render_sources_rollup(e.get("sources"))

        lines = [heading, ""]
        if status:
            lines.append(f"**Status:** {status}")
            lines.append("")
        if text:
            lines.append(text)
            lines.append("")
        if sources_block:
            lines.append(sources_block.rstrip())
        blocks.append("\n".join(lines).rstrip())

    return head + "\n" + "\n\n".join(blocks) + "\n"


def render_open_questions(artifact):
    """`## Open Questions` — questions the primary-source record does
    not resolve, each paired with what would resolve them."""
    items = [q for q in (artifact.get("open_questions") or []) if isinstance(q, dict)]
    lines = ["## Open Questions", ""]
    if not items:
        lines.append("<!-- TODO: populate `open_questions` in the research artifact -->")
        return "\n".join(lines) + "\n"
    for q in items:
        question = (q.get("question") or "").strip()
        resolve = (q.get("what_would_resolve") or "").strip()
        if resolve:
            lines.append(f"- **{question}** — {resolve}")
        else:
            lines.append(f"- {question}")
    return "\n".join(lines) + "\n"


def render_best_current_answer(artifact):
    """`## Best-Current Answer` — integrated cross-hypothesis judgment
    with its own sources rollup."""
    bca = artifact.get("best_current_answer")
    head = "## Best-Current Answer\n"
    # Treat both None and empty dict as scaffold state — emit TODO so
    # the contributor sees what to populate. Only a populated dict
    # enters the render-the-content branch.
    if not isinstance(bca, dict) or not bca:
        return head + "\n<!-- TODO: populate `best_current_answer` in the research artifact -->\n"
    text = (bca.get("text") or "").strip()
    sources_block = _render_sources_rollup(bca.get("sources"))
    lines = [head.rstrip(), ""]
    if text:
        lines.append(text)
        lines.append("")
    if sources_block:
        lines.append(sources_block.rstrip())
    return "\n".join(lines).rstrip() + "\n"


def render_counter_evidence(artifact):
    """`## Counter-Evidence` — discrete section for findings or facts
    that contradict the investigation's hypotheses. Conditional: returns
    empty when counter_evidence[] is empty."""
    items = [c for c in (artifact.get("counter_evidence") or []) if isinstance(c, dict)]
    if not items:
        return ""
    head = "## Counter-Evidence\n"
    blocks = []
    for c in items:
        against = (c.get("against_hypothesis_id") or "").upper()
        heading = f"### Against {against}" if against else "### Counter-evidence"
        text = (c.get("text") or "").strip()
        sources_block = _render_sources_rollup(c.get("sources"))
        lines = [heading, ""]
        if text:
            lines.append(text)
            lines.append("")
        if sources_block:
            lines.append(sources_block.rstrip())
        blocks.append("\n".join(lines).rstrip())
    return head + "\n" + "\n\n".join(blocks) + "\n"


def render_closure_path(artifact, fm):
    """`## Closure Path` — required when investigation status == paused;
    optional otherwise. Documents what external event would unblock
    the investigation."""
    items = [c for c in (artifact.get("closure_path") or []) if isinstance(c, dict)]
    status = fm.get("status")
    if not items and status != "paused":
        return ""
    head = "## Closure Path\n"
    if not items:
        return head + "\n<!-- TODO: status is 'paused' but closure_path is empty — populate the artifact -->\n"
    lines = [head.rstrip(), ""]
    for c in items:
        blocking = (c.get("blocking_event") or "").strip()
        expected = (c.get("expected_unblock_path") or "").strip()
        if expected:
            lines.append(f"- **{blocking}** — {expected}")
        else:
            lines.append(f"- {blocking}")
    return "\n".join(lines) + "\n"


def render_resolution_history(artifact):
    """`## Resolution History` — optional log of how the investigation
    has evolved. Conditional: empty when resolution_history[] empty."""
    items = sort_by_date(
        [r for r in (artifact.get("resolution_history") or []) if isinstance(r, dict)],
        "date",
    )
    if not items:
        return ""
    lines = ["## Resolution History", "",
             "| Date | Event |",
             "|---|---|"]
    for r in items:
        date = r.get("date") or ""
        event = (r.get("event") or "").replace("|", "\\|")
        lines.append(f"| {date} | {event} |")
    return "\n".join(lines) + "\n"


def render_body_investigation(artifact, fm):
    """Investigation-type body composition. Section order matches the
    schema's required_sections."""
    title = render_title_investigation(artifact).rstrip("\n") + "\n"
    sections = [
        render_question(artifact, fm),
        render_description(artifact),
        render_hypotheses(artifact),
        render_cited_findings(artifact),
        render_hypothesis_evaluation(artifact),
        render_open_questions(artifact),
        render_best_current_answer(artifact),
        render_counter_evidence(artifact),            # conditional
        render_closure_path(artifact, fm),            # conditional / paused
        render_resolution_history(artifact),          # conditional
        render_associated_nodes(),
    ]
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
