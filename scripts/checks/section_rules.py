"""section-rules check — per-node NodeContext check.

Walks ``type_spec.section_rules`` and enforces three sub-rules per
section:

  - ``prose_only``: section must not contain a markdown table
  - ``split: [...]``: section must carry the listed H3 subsections.
    ``### Confirmed`` is required when listed; ``### Flagged`` is
    omitted when empty by convention (``meta/conventions.md``
    "Confirmed vs Flagged"), so the walker skips Flagged even when
    the schema's split rule names it.
  - ``requires_quote_attribution``: any block-quote in the section
    must be paired with an attribution ``| Source | … |`` row.

The three sub-rules share H2 extraction and per-section text retrieval
via ``NodeContext.h2_sections`` / ``section_text``, so they live in
one module rather than three.

Helpers ``_section_has_table``, ``_count_quote_blocks_and_attributions``,
and ``_extract_h3_subsections`` are private to this walker.
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
    # Every content type declares ``section_rules`` per schema.yaml;
    # direct subscript surfaces a loud KeyError if a type loses the
    # block.
    section_rules = ctx.type_spec["section_rules"]
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
