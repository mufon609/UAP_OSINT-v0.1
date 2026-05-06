"""table-cell-word-budget check — per-node NodeContext check.

Walks every H2 section and warns on any table cell whose word count
exceeds the schema's ``limits.table_cell_words_soft`` budget. The
budget is a soft guideline pointing at cells that should promote to
a ``###`` subsection or a finding node — not a hard error; warnings
only.

The schema currently declares the budget as ``55``. The hardcoded
fallback (``55``) covers the rare case where ``ctx.schema`` is
unreadable; it tracks the schema's actual value so a schema-load
failure doesn't silently shift the threshold.

Markdown link wraps (``[`/path`]``) are stripped before counting so a
cell carrying many cross-reference links isn't flagged just for the
links.

Origin: foundational from the initial commit (``af5f789``); the
budget started at ``50`` per the original schema. Bumped to ``55``
at commit ``44272af`` ("scripts/lib: extract cross-script helpers
+ warning cleanup pass") when the warning-cleanup pass found that
two of the then-current five cell-budget warnings were firing on
legitimate-sized cells; raising the soft cap by 5 cleared them
without forcing structural changes. The hardcoded fallback in this
module wasn't synced at the time; the C17 audit picked up the lag
and synced fallback to schema's current 55.

Migration: ``60bb88d`` (C11 session 3 lift to per-module shape).
Carries ``_table_cell_overages`` (only consumer is this check).
C18 confirmed byte-identity through the C11 migration.

Anchor pattern: stable schema-driven check with fallback-default
sync. The check shape is foundational (since af5f789); the
threshold value lives in schema and has bumped once (50 → 55) for
operational reasons. The C17 fallback sync is a small consistency
fix, not behavior change in normal operation (the schema-lookup
path always wins when the schema is readable).
"""

import re

from checks import Issue


CHECK_NAME = "table_cell_word_budget"


# Fallback when ctx.schema is unreadable. Tracks the schema's current
# table_cell_words_soft value (55 since commit 44272af); update this
# constant if the schema bumps the soft cap so the fallback doesn't
# silently shift the threshold on schema-load failure.
_FALLBACK_BUDGET = 55


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
    budget = ctx.schema.get("limits", {}).get("table_cell_words_soft", _FALLBACK_BUDGET)
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
