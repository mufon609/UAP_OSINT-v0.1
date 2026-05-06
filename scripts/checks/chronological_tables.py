"""chronological-ordering check — per-node NodeContext check.

Universal discipline: any markdown table with a date-bearing column
is ordered earliest-first. Applies across every node type and every
section, upgrading the schema's ``chronological: true`` flag from
descriptive-only to enforced.

Walks each H2 section for tables (header + separator + data rows),
identifies the date column by header name (case-insensitive match
against ``DATE_HEADERS``), parses ISO YYYY-MM-DD / prefix-truncated
forms (``YYYY-MM`` / ``YYYY``) and range cells (taking the leftmost
date), and errors if rows aren't in ascending order.

Severity split:

  - Out-of-order pairs ERROR (ordering is mechanical).
  - Unparseable date cells WARN (format discipline is contributor
    judgment; legitimate non-ISO forms surface here without blocking).

Range-cell handling: ``_DATE_RANGE_SEPARATORS`` ordered longest-
spaced-first so ``" – "`` (em-dash with surrounding spaces) consumes
the spaces before bare ``–`` matches inside it. Empty-left fallback
to right handles ``"– 2021"`` (bracketed end with unknown start) —
the row sorts by its attested end date. Placeholder strings ("—",
"tbd", "present", "ongoing", "n/a", "undated") parse as None and
skip the pair check.

DATE_HEADERS is an explicit allowlist rather than a regex pattern —
prevents false positives on accidentally-date-shaped headers
("Section 12", "Year 1") at the cost of needing manual addition for
new date column header names.
"""

import re

from checks import Issue
from lib._common import parse_date_tuple


CHECK_NAME = "chronological_tables"


DATE_HEADERS = {
    "date", "date / time", "date/time",
    "period", "start", "start date", "dates",
    "date captured", "date released",
}


_TABLE_RE = re.compile(
    r"(?P<header_line>^\|(?P<header>[^\n]+)\|\s*)\n"
    r"(?P<sep_line>^\|(?P<sep>[\s:|-]+)\|\s*)\n"
    r"(?P<rows>(?:^\|[^\n]+\|\s*\n?)+)",
    re.MULTILINE,
)


def _parse_table_row(row_line):
    """Split a ``| a | b | c |`` row into trimmed cell strings."""
    inner = row_line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def check(ctx):
    """Yield Issues for any date-bearing table where rows aren't
    earliest-first. Warn on unparseable date cells; error on out-of-
    order rows. Uses NodeContext lazy h2_sections + section_text caches
    to share H2 extraction with the other section-walking checks
    (required_sections, section_rules, table_cell_word_budget,
    conditionally_required)."""
    for section_name in ctx.h2_sections:
        section_text = ctx.section_text(section_name)
        if section_text is None:
            continue

        for m in _TABLE_RE.finditer(section_text):
            headers = [h.strip().lower() for h in m.group("header").split("|")]
            date_col = None
            for i, h in enumerate(headers):
                if h in DATE_HEADERS:
                    date_col = i
                    break
            if date_col is None:
                continue

            # Parse each data row's date cell (skip empty-placeholder rows)
            rows = m.group("rows").strip().splitlines()
            parsed_dates = []
            for row_line in rows:
                cells = _parse_table_row(row_line)
                if date_col >= len(cells):
                    continue
                if all(c == "" for c in cells):
                    continue  # template placeholder row
                cell = cells[date_col]
                d = parse_date_tuple(cell)
                if d is None and cell:
                    yield Issue(
                        ctx.rel, "warn",
                        f"Section '{section_name}': unparseable date "
                        f"{cell!r} in '{headers[date_col] or '?'}' column",
                        check_name=CHECK_NAME,
                    )
                parsed_dates.append((cell, d))

            # Verify ascending order across parseable entries
            previous_cell, previous = None, None
            for cell, d in parsed_dates:
                if d is None:
                    continue
                if previous is not None and d < previous:
                    yield Issue(
                        ctx.rel, "error",
                        f"Section '{section_name}': table rows not in "
                        f"chronological order (saw {cell!r} after "
                        f"{previous_cell!r} in "
                        f"'{headers[date_col] or '?'}' column; "
                        f"earliest first)",
                        check_name=CHECK_NAME,
                    )
                    break
                previous, previous_cell = d, cell
