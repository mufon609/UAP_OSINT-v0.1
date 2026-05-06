"""section-rules check — per-node NodeContext check.

Walks ``type_spec.section_rules`` and enforces three sub-rules per
section (per design doc §6 — three sub-checks share H2 extraction and
per-section text retrieval; splitting into three modules would
fragment shared state without buying isolation):

  - ``prose_only``: section must not contain a markdown table
  - ``split: [...]``: section must carry the listed H3 subsections
    (``### Confirmed`` is required when listed; ``### Flagged`` is
    omitted when empty by convention, so the walker skips Flagged
    even if listed)
  - ``requires_quote_attribution``: any block-quote in the section
    must be paired with an attribution ``| Source | … |`` row

Lift from validate.py validate_node (C11 session-3 migration). Carries
the small parsing helpers (``section_has_table``,
``count_quote_blocks_and_attributions``, ``extract_h3_subsections``)
that previously lived inline; only consumer of each was this walker.
"""

import re

from checks import Issue


CHECK_NAME = "section_rules"


def _section_has_table(section_text):
    return bool(
        re.search(r"^\|[^\n]*\|\s*\n\|[\s:|-]+\|", section_text, re.MULTILINE)
    )


def _count_quote_blocks_and_attributions(section_text):
    """Count ``> blockquote`` lines and ``| Source | …`` attribution rows
    in a section. Used to enforce the structural rule that a section
    flagged ``requires_quote_attribution`` either has no quotes (empty
    section is fine) or has a Source row for each quote — the renderer
    always pairs a block-quote with an attribution table whose Source
    row points at the cited archived file.
    """
    quotes = sum(1 for line in section_text.splitlines() if line.strip().startswith(">"))
    attributions = sum(1 for line in section_text.splitlines() if line.strip().startswith("| Source |"))
    return quotes, attributions


def _extract_h3_subsections(section_text):
    return re.findall(r"^### (.+?)\s*$", section_text, re.MULTILINE)


def check(ctx):
    section_rules = ctx.type_spec.get("section_rules", {})
    h2_sections = ctx.h2_sections
    for section_name, rules in section_rules.items():
        if section_name not in h2_sections:
            continue
        section_text = ctx.section_text(section_name)
        if section_text is None:
            continue

        if rules.get("prose_only") and _section_has_table(section_text):
            yield Issue(
                ctx.rel, "error",
                f"Section '{section_name}' must be prose only (no tables)",
                check_name=CHECK_NAME,
            )

        if "split" in rules:
            h3s = _extract_h3_subsections(section_text)
            for sub in rules["split"]:
                if sub == "Flagged":
                    continue  # omitted when empty by convention
                if sub not in h3s:
                    yield Issue(
                        ctx.rel, "error",
                        f"Section '{section_name}' missing '### {sub}' subsection",
                        check_name=CHECK_NAME,
                    )

        if rules.get("requires_quote_attribution"):
            quotes, attributions = _count_quote_blocks_and_attributions(section_text)
            if quotes > 0 and attributions == 0:
                yield Issue(
                    ctx.rel, "error",
                    f"Section '{section_name}' has quotes but no attribution "
                    f"blocks (each block-quote needs a `| Source | … |` row "
                    f"pointing at the cited archived file)",
                    check_name=CHECK_NAME,
                )
