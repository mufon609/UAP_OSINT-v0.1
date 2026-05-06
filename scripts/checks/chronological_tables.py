"""chronological-ordering check — per-node NodeContext check.

Universal discipline: any markdown table with a date-bearing column is
ordered earliest-first. Applies across every node type and every
section.

Walks each H2 section for tables (header + separator + data rows),
identifies the date column by header name (case-insensitive match
against ``DATE_HEADERS``), parses ISO YYYY-MM-DD / prefix-truncated
forms (``YYYY-MM`` / ``YYYY``) and range cells (taking the leftmost
date), and errors if rows aren't in ascending order. Warns on
unparseable date strings (natural-language dates, non-ISO formats —
promoted to error if a pattern emerges).

Upgrades the schema's ``chronological: true`` flag from descriptive-
only to enforced.

First NodeContext-consuming check migrated to the C11 contract;
exercises the per-node iteration shape end-to-end.

Origin: introduced at commit ``8007ef1`` (F.1a — person schema under
statements-only discipline + check #15 chronological), as a paired
landing with the schema's ``section_rule: {chronological: true}``
flag on Timeline / Provenance / Ownership Timeline across organization
/ event / document / media / location node types. Defensive design
shape — created with the schema flag rather than in response to a
specific ordering bug. F.1a's commit message explicitly framed the
check as the "now enforced by validator check #15" companion to the
schema declaration.

Severity model split: unparseable date cells warn (format discipline
is contributor judgment territory; some legitimate date forms might
pre-date a strictly-ISO requirement, e.g. inherited "2003 – 2004
USAF Master Sergeant" range cells); out-of-order pairs error
(ordering is mechanical). The split matches the impartial-validator
discipline established by prose_drift (see
``feedback_validator_impartiality.md``) — the check enforces
mechanical invariants and reports format issues without classifying.

Range-cell handling: ``_DATE_RANGE_SEPARATORS`` ordered longest-
spaced-first so " – " (em-dash with surrounding spaces) consumes the
spaces before bare "–" matches inside it. Empty-left fallback to
right handles the "– 2021" rendered shape for bracketed-end-with-
unknown-start (per the AARO Phillips Deputy Director research-queue
note about period conventions); the row sorts by its attested end
date when the start is null. Placeholder strings ("—", "tbd",
"present", "ongoing", "n/a", "undated") parse as None and skip the
ordering pair check — the check can't sort what doesn't have a
date, but doesn't fail the table either.

DATE_HEADERS is an explicit allowlist rather than a regex pattern —
prevents false positives on accidentally-date-shaped content
("Section 12", "Year 1") at the cost of needing manual addition for
new date column header names. New table-emitting renderers should
either reuse a recognized header or add to the set; preserves
mechanical reliability over inferential cleverness.

Migration: ``8007ef1`` (F.1a introduction) → ``4d626a4`` (rename of
check #15 → "chronological-ordering" in cross-references) →
``d65451b`` (C11 session 2 — first NodeContext check migrated to
per-module shape) → ``ecabd52`` (post-cluster retrofit: NodeContext
gained ``h2_sections`` + ``section_text`` lazy caches in C11 session
3 / commit 60bb88d, but this module had migrated in session 2 and
missed the cache pickup; ecabd52 retrofits to read the cache
properties so this check shares H2 extraction with required_sections
/ section_rules / table_cell_word_budget / conditionally_required
on the same NodeContext). C18 confirmed byte-identity through the
per-module migration despite the cache-utilization shift.
"""

import re

from checks import Issue


CHECK_NAME = "chronological_tables"


DATE_HEADERS = {
    "date", "date / time", "date/time",
    "period", "start", "start date", "dates",
    "date captured", "date released",
}

# Range separators between start and end dates in a single cell. Ordered
# longest-first so "—" doesn't match inside " – ".
_DATE_RANGE_SEPARATORS = (" – ", " — ", " to ", " - ", "–", "—", "-to-")


_TABLE_RE = re.compile(
    r"(?P<header_line>^\|(?P<header>[^\n]+)\|\s*)\n"
    r"(?P<sep_line>^\|(?P<sep>[\s:|-]+)\|\s*)\n"
    r"(?P<rows>(?:^\|[^\n]+\|\s*\n?)+)",
    re.MULTILINE,
)


def parse_date_token(s):
    """Return (year, month, day) tuple suitable for sort comparison, or
    None if unparseable. Range cells take the leftmost date. Missing
    month / day default to 0, so '2004' < '2004-11' < '2004-11-14'
    under tuple comparison.
    """
    if not s:
        return None
    s = s.strip()
    if s.lower() in {"—", "-", "n/a", "undated", "tbd", "present", "ongoing", ""}:
        return None
    # Range: take the left side. If the left side is empty (end-only
    # period rendered as "– 2021" — signals bracketed end with unknown
    # start, e.g., "former X" attestation without a specific start date),
    # take the right side instead so the row still sorts by its attested
    # end date.
    for sep in _DATE_RANGE_SEPARATORS:
        if sep in s:
            left, _, right = s.partition(sep)
            left = left.strip()
            right = right.strip()
            s = left if left else right
            break
    m = re.match(r"^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", s)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2)) if m.group(2) else 0
        d = int(m.group(3)) if m.group(3) else 0
        return (y, mo, d)
    return None


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
                d = parse_date_token(cell)
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
