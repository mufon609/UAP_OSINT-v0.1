"""verbatim-quote check — per-node NodeContext check (load-bearing).

For every block-quote with an attribution Source pointing at an
archived file under ``sources/``, confirm the quote appears as a
substring of the extracted source text. The single mechanical backstop
against silent drift between an artifact's quote text and the source
it claims to draw on.

Runs unconditionally. Confirmation against the source is a precondition
for inclusion in node bodies, not a marker the contributor opts into;
the check has no rendered counterpart (no "Verified" row) by design —
the source link IS the evidence for readers. See ``meta/conventions.md``
"Confirmation is a precondition for inclusion" and the
``meta/toolkit-notes/pilot-failure-2026-04-17.md`` postmortem; this
check is the rationale-of-record fix for the failure modes documented
there. Reference the postmortem before proposing to weaken or remove.

Failure messages name the node, the line number of the block-quote,
the cited source file, and a preview of the unmatched text — enough
for a contributor to navigate and fix without further detective work.

Requires ``pdftotext`` for PDF sources (poppler-utils on Linux);
HTML / TXT sources read directly via ``lib._common.extract_source_text``.
PDFs flagged ``extraction_type: ocr-scan`` / ``extraction-lossy`` in
``sources/manifest.yaml`` prefer a same-stem ``.txt`` sibling (clean
transcription) over ``pdftotext`` output. Binary-by-design sources
(``image`` / ``video`` / ``audio`` per manifest format) warn rather
than error — the check can't substring-match against bytes that
aren't text.
"""

import re

from checks import Issue
from lib._common import (
    SOURCES_DIR,
    extract_source_text,
    manifest_format,
    normalize_for_compare,
)


CHECK_NAME = "verbatim_quotes"


_BLOCKQUOTE_BLOCK = re.compile(
    r"(^>[ \t].+(?:\n>[ \t].*)*)",
    re.MULTILINE,
)


def _find_quote_source_pairs(text):
    """Yield (quote_text, source_ref, line_no) for each block-quote
    followed by an attribution table containing a Source row.

    line_no is the 1-indexed line number of the block-quote's first
    line in the original text — surfaced in failure messages so
    contributors can locate the quote in the rendered node directly.
    """
    for bq_match in _BLOCKQUOTE_BLOCK.finditer(text):
        raw = bq_match.group(1)
        # Strip leading "> " from each line, join with spaces
        quote_lines = [re.sub(r"^>[ \t]?", "", line) for line in raw.splitlines()]
        quote_text = " ".join(line for line in quote_lines if line.strip())
        # Strip surrounding quote marks
        quote_text = re.sub(r'^["“”‘’]+', "", quote_text)
        quote_text = re.sub(r'["“”‘’]+$', "", quote_text)
        quote_text = quote_text.strip()
        if not quote_text:
            continue
        # Look for Source row within ~2500 chars after the quote
        after = text[bq_match.end():bq_match.end() + 2500]
        src_match = re.search(
            r"^\|\s*Source\s*\|\s*([^|]+?)\s*\|",
            after, re.MULTILINE,
        )
        if not src_match:
            continue
        source_ref = src_match.group(1).strip()
        line_no = text.count("\n", 0, bq_match.start()) + 1
        yield quote_text, source_ref, line_no


def check(ctx):
    """Yield Issues for any block-quote whose text doesn't appear in
    the cited source file. Errors on missing source files or quote-
    not-found; warns on extraction failure (binary or pdftotext
    missing)."""
    for quote_text, source_ref, line_no in _find_quote_source_pairs(ctx.text):
        # Extract local source path from markdown link (../sources/foo.pdf)
        path_match = re.search(r"\(\.\./sources/([^)]+)\)", source_ref)
        if not path_match:
            # Source refers to a node link (e.g. [`/transcripts/...`]) rather
            # than a file. Can't mechanically verify — skip (soft case).
            continue
        rel_source = path_match.group(1)
        source_file = SOURCES_DIR / rel_source
        if not source_file.exists():
            yield Issue(
                ctx.rel, "error",
                f"Quote at line {line_no} cites missing source file: sources/{rel_source}",
                check_name=CHECK_NAME,
            )
            continue
        source_text = extract_source_text(source_file)
        if source_text is None:
            # Distinguish binary-by-design (image/video/audio per manifest
            # format) from extraction-infrastructure failure. pdftotext
            # didn't fail on a .mp4; it was never going to run. Binary-
            # source-citing quotes require manual contributor verification —
            # the validator can't substring-match against bytes that aren't
            # text. Frame the warning accordingly.
            fmt = manifest_format(rel_source)
            if fmt in ("image", "video", "audio"):
                yield Issue(
                    ctx.rel, "warn",
                    f"Quote at line {line_no} cites sources/{rel_source} "
                    f"(format: {fmt}) — verbatim-quote check requires manual "
                    f"contributor verification of binary source",
                    check_name=CHECK_NAME,
                )
            else:
                yield Issue(
                    ctx.rel, "warn",
                    f"Quote at line {line_no} cites sources/{rel_source} but "
                    f"text extraction failed (pdftotext missing or failed)",
                    check_name=CHECK_NAME,
                )
            continue
        norm_quote = normalize_for_compare(quote_text)
        norm_source = normalize_for_compare(source_text)
        if norm_quote not in norm_source:
            preview = quote_text[:80] + ("..." if len(quote_text) > 80 else "")
            yield Issue(
                ctx.rel, "error",
                f'Quote at line {line_no} NOT FOUND in sources/{rel_source}: "{preview}"',
                check_name=CHECK_NAME,
            )
