"""table-cell-word-budget check — per-node NodeContext check.

Walks every H2 section and warns on any table cell whose word count
exceeds ``schema.limits.table_cell_words_soft``. The budget is a
soft guideline pointing at cells that should promote to a ``###``
subsection or a finding node — warnings only, never errors.

Markdown link wraps (``[`/path`]``) and emphasis markers are stripped
before counting so a cell carrying many cross-reference links isn't
flagged just for them.

``Note`` columns are exempt — they're designed to carry 1-3 sentences
of source-attested nuance per the BACKLOG B1 M1 render-the-`.note`
convention. The word-budget is a promote-to-subsection heuristic for
terse label cells (org names, role titles, dates); it doesn't apply
to columns whose purpose is prose. The check tracks the most recent
table header row in the section to identify Note-column positions.

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
    counting words. Skips cells in ``Note`` columns (identified by the
    most recent header row preceding each data row)."""
    out = []
    note_columns = set()
    pending_header = False
    for line in section_text.splitlines():
        if not _is_table_row(line):
            # Reset Note-column map when leaving a table (e.g., blank line)
            note_columns = set()
            pending_header = False
            continue
        cells = _split_cells(line)
        if _is_separator_row(line):
            pending_header = False
            continue
        if pending_header:
            # The most recent non-separator table row was a candidate header;
            # this current row could be a data row OR another header (a new
            # table starting without intervening prose). Re-evaluate.
            pass
        # Decide whether this row is a header. Heuristic: if any cell name
        # in this row case-insensitively equals 'note' AND every cell is a
        # short non-prose label, treat as header. Conservative: just check
        # for 'Note' cell.
        if any(c.strip().lower() == "note" for c in cells):
            note_columns = {i for i, c in enumerate(cells)
                            if c.strip().lower() == "note"}
            pending_header = True
            continue
        # Data row — apply word budget to non-Note columns
        for i, cell in enumerate(cells):
            if i in note_columns:
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
