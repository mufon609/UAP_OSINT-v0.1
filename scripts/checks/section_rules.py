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
    """Returns (blocks, attributions) for a section.

    ``blocks`` is the number of distinct contiguous block-quote runs
    (each `>`-prefixed run between blank/non-quote lines counts as
    one). ``attributions`` is the sum of two surfaces produced by
    the renderer:

      - ``| Source |`` rows from the long-form attribution table
      - italicized inline attribution lines (``_…_`` on a line by
        themselves) emitted by the compact-quote renderer for
        sub-threshold quotes

    The two surfaces are equivalent for the
    `requires_quote_attribution` rule's purpose — both pair a
    block-quote with its source attribution. A partial-attribution
    case (3 blocks, 1 source row, 0 italic lines) trips the gate.
    """
    lines = section_text.splitlines()
    blocks = 0
    in_block = False
    for line in lines:
        is_quote = line.strip().startswith(">")
        if is_quote and not in_block:
            blocks += 1
            in_block = True
        elif not is_quote:
            in_block = False
    source_rows = sum(
        1 for line in lines if line.strip().startswith("| Source |")
    )
    italic_lines = 0
    for line in lines:
        s = line.strip()
        if len(s) > 2 and s.startswith("_") and s.endswith("_"):
            italic_lines += 1
    return blocks, source_rows + italic_lines


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
            blocks, attributions = _count_quote_blocks_and_attributions(section_text)
            if blocks > attributions:
                yield Issue(
                    ctx.rel, "error",
                    f"Section '{section_name}' has {blocks} block-quote(s) "
                    f"but only {attributions} attribution surface(s) "
                    f"(each block-quote needs either a `| Source | … |` row "
                    f"or an italicized inline attribution line)",
                    check_name=CHECK_NAME,
                )
