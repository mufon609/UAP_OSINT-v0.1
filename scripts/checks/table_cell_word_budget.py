"""table-cell-word-budget check — per-node NodeContext check.

Walks every H2 section and warns on any table cell whose word count
exceeds ``schema.limits.table_cell_words_soft``. The budget is a
soft guideline pointing at cells that should promote to a ``###``
subsection or a finding node — warnings only, never errors.

Markdown link wraps (``[`/path`]``) and emphasis markers are stripped
before counting so a cell carrying many cross-reference links isn't
flagged just for them.

Prose-purpose columns are exempt — the word-budget is a
promote-to-subsection heuristic for terse label cells (org names, role
titles, dates) and doesn't apply to columns whose purpose is prose. Two
such columns: a ``Note`` column (designed to carry 1-3 sentences of
source-attested nuance), and the ``Value`` column of a ``| Field | Value |``
key-value table (the attribution block, Document Summary, Media Versioning,
etc.) — a key's value is whatever it is, with no promote-to-subsection
remedy. The check tracks the most recent table header row in the section to
identify these column positions.

The budget value is read via direct subscript so schema drift fails
loudly rather than silently degrading.
"""

import re

from checks import Issue


CHECK_NAME = "table_cell_word_budget"


def _is_separator_row(line):
    return bool(re.match(r"^\s*\|[\s:|-]+\|\s*$", line))


def _split_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_table_row(line):
    return line.strip().startswith("|") and line.count("|") >= 2


def _table_cell_overages(section_text, budget):
    """Return list of (cell_preview, word_count) for cells exceeding the
    budget. Strips markdown link syntax and emphasis markers before
    counting words. Skips cells in prose-purpose columns — a ``Note`` column
    or the ``Value`` column of a ``| Field | Value |`` key-value table —
    identified by the most recent header row preceding each data row."""
    out = []
    prose_columns = set()
    for line in section_text.splitlines():
        if not _is_table_row(line):
            # Reset the prose-column map when leaving a table (e.g., blank line)
            prose_columns = set()
            continue
        cells = _split_cells(line)
        if _is_separator_row(line):
            continue
        lowered = [c.strip().lower() for c in cells]
        # Header detection: a 'Note' label column, or a 'Field | Value'
        # key-value header whose Value column is a prose/value column by
        # design (same rationale as Note — not a terse-label column).
        if "note" in lowered or lowered == ["field", "value"]:
            prose_columns = {i for i, c in enumerate(lowered)
                             if c in ("note", "value")}
            continue
        # Data row — apply word budget to non-prose columns
        for i, cell in enumerate(cells):
            if i in prose_columns:
                continue
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
