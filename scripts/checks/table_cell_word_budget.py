"""table-cell-word-budget check — per-node NodeContext check.

Walks every H2 section and warns on any table cell whose word count
exceeds ``schema.limits.table_cell_words_soft``. The budget is a
soft guideline pointing at cells that should promote to a ``###``
subsection or a finding node — warnings only, never errors.

Markdown link wraps (``[`/path`]``) and emphasis markers are stripped
before counting so a cell carrying many cross-reference links isn't
flagged just for them.

The budget value is read via direct subscript so schema drift fails
loudly rather than silently degrading.
"""

import re

from checks import Issue


CHECK_NAME = "table_cell_word_budget"


def _table_cell_overages(section_text, budget):
    """Return list of (cell_preview, word_count) for cells exceeding the
    budget. Strips markdown link syntax and emphasis markers before
    counting words."""
    out = []
    for line in section_text.splitlines():
        if not (line.strip().startswith("|") and line.count("|") >= 2):
            continue
        if re.match(r"^\s*\|[\s:|-]+\|\s*$", line):
            continue  # separator row
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for cell in cells:
            stripped = re.sub(r"\[`[^`]+`\]", "", cell)
            stripped = re.sub(r"[*_`]", "", stripped)
            words = stripped.split()
            if len(words) > budget:
                preview = cell[:60] + ("..." if len(cell) > 60 else "")
                out.append((preview, len(words)))
    return out


def check(ctx):
    budget = ctx.schema["limits"]["table_cell_words_soft"]
    for section_name in ctx.h2_sections:
        section_text = ctx.section_text(section_name)
        if section_text is None:
            continue
        for preview, count in _table_cell_overages(section_text, budget):
            yield Issue(
                ctx.rel, "warn",
                f"Table cell in '{section_name}' exceeds word budget "
                f"({count}>{budget}): {preview}",
                check_name=CHECK_NAME,
            )
