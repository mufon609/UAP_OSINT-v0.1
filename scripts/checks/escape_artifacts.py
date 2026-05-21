"""escape_artifacts check — NodeContext (rendered-output format hygiene).

Flags a doubled apostrophe (``''``) that leaks into the rendered node body on
a NON-blockquote line. In rendered Markdown a literal ``''`` is always a YAML
escaping bug: a single-quoted scalar collapses ``''``→``'`` at parse time, so
a surviving ``''`` means an *unquoted* scalar carried a doubled apostrophe
(``context: ...Knapp''s...``) or a single-quoted scalar over-escaped
(``''''``). These land in label / attribution / note cells (``significance``,
``context``, ``.note``, key_personnel / contract notes) that are neither
verbatim-quote-checked nor prose-drift-scanned — so nothing else catches them
and they ship green.

Blockquote lines (start with ``>``) are exempt: ``''`` there can be
source-verbatim quote text (e.g. stenographic quote marks), preserved by
design — the verbatim-quote check owns that text.
"""

from checks import Issue

CHECK_NAME = "escape_artifacts"


def check(ctx):
    for i, line in enumerate((ctx.text or "").split("\n"), start=1):
        if line.lstrip().startswith(">"):
            continue
        if "''" in line:
            yield Issue(
                ctx.rel, "error",
                f"line {i}: doubled-apostrophe escape artifact `''` in rendered "
                f"output (an unquoted YAML scalar carried `''`, or a single-quoted "
                f"scalar over-escaped to `''''`). Fix the scalar in the artifact: "
                f"single-quote it (then `''` is the correct escape) or use a single "
                f"`'`. Context: {line.strip()[:70]!r}",
                check_name=CHECK_NAME,
            )
