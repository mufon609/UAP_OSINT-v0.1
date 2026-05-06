"""table-cell-word-budget check — per-node NodeContext check.

Walks every H2 section and warns on any table cell whose word count
exceeds the schema's ``limits.table_cell_words_soft`` budget. The
budget is a soft guideline pointing at cells that should promote to
a ``###`` subsection or a finding node — not a hard error; warnings
only.

Markdown link wraps (``[`/path`]``) are stripped before counting so a
cell carrying many cross-reference links isn't flagged just for the
links.

Origin: foundational from the initial commit (``af5f789``); the
budget started at ``50`` per the original schema. Bumped to ``55``
at commit ``44272af`` ("scripts/lib: extract cross-script helpers
+ warning cleanup pass") when the warning-cleanup pass found that
two of the then-current five cell-budget warnings were firing on
legitimate-sized cells; raising the soft cap by 5 cleared them
without forcing structural changes.

Schema config is required; no fallback. The check reads
``ctx.schema["limits"]["table_cell_words_soft"]`` directly and lets
KeyError surface if the schema is missing the value. Earlier
iterations of the check used a ``.get(..., default)`` fallback
that masked schema drift — the af5f789 schema's initial budget of
50 stayed as the hardcoded fallback even after the schema bumped
to 55, drift unnoticed for ~3 weeks. The C17 audit removed the
fallback as part of a broader sweep across the six schema-config
fallback sites in the validator; principle is that schema is
foundational toolkit contract — missing required schema values
should fail loudly, not silently degrade.

Migration: ``60bb88d`` (C11 session 3 lift to per-module shape).
Carries ``_table_cell_overages`` (only consumer is this check).
C18 confirmed byte-identity through the C11 migration; the C17
fallback removal is a deliberate behavior change for the
schema-malformed path (silent fallback → loud KeyError).
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
