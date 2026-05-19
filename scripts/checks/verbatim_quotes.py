"""verbatim-quote check — per-artifact ResearchContext check (load-bearing).

For every entry in ``quotes[]`` whose ``source.path`` points at an
archived file under ``sources/``, confirm the quote ``text`` appears
as a substring of the extracted source text. The single mechanical
backstop against silent drift between an artifact's quote text and
the source it claims to draw on.

Runs unconditionally on every research artifact. Confirmation against
the source is a precondition for inclusion at the artifact layer, not
a marker the contributor opts into; the rendered node body inherits
the verified quote text from the artifact by construction. The check
has no rendered counterpart (no "Verified" row) by design — the source
link IS the evidence for readers. See ``meta/conventions.md``
"Confirmation is a precondition for inclusion" for the rationale.

Failure messages name the artifact, the quote's id + index, the cited
source path, and a preview of the unmatched text — enough for a
contributor to navigate and fix without further detective work.

Layered enforcement around quote integrity:

  - ``quotes`` (artifact-side entry-shape): text + source dict + per-
    target-type observation_type / context / speaker_id requirements.
    Runs first; this check assumes shape errors already surfaced.
  - This check (``verbatim_quotes``): the quote text actually appears
    verbatim in the cited source file.
  - ``coverage`` (cross-layer): the artifact's quote text appears in
    the rendered node body. Source → artifact → node is the chain.

Requires ``pdftotext`` for PDF sources (poppler-utils on Linux);
HTML / TXT sources read directly via ``lib._common.extract_source_text``.
PDFs flagged ``extraction_type: ocr-scan`` / ``extraction-lossy`` in
``sources/manifest.yaml`` prefer a same-stem ``.txt`` sibling (clean
transcription) over ``pdftotext`` output. Binary-by-design sources
(``image`` / ``video`` / ``audio`` per manifest format) warn rather
than error — the check can't substring-match against bytes that
aren't text.
"""

from checks import Issue
from checks._research_utils import entries
from lib._common import (
    BINARY_FORMATS,
    SOURCES_DIR,
    extract_source_text,
    manifest_format,
    normalize_for_compare,
)


CHECK_NAME = "verbatim_quotes"


def check(ctx):
    """Yield Issues for any quote whose ``text`` doesn't appear in the
    cited source file. Errors on missing source files or quote-not-
    found; warns on extraction failure (binary or pdftotext missing).

    Skips entries that the ``quotes`` check has already flagged as
    structurally malformed (missing text, missing source dict, missing
    path). The ``quotes`` check is dispatched earlier in
    ``_ARTIFACT_CHECKS``; one diagnostic per defect.
    """
    for i, q in enumerate(entries(ctx.data, "quotes")):
        if not isinstance(q, dict):
            continue
        text = q.get("text")
        if not text or not isinstance(text, str):
            continue  # quotes check yields the shape error
        src = q.get("source")
        if not isinstance(src, dict):
            continue  # quotes check yields the shape error
        rel_source = src.get("path")
        if not rel_source:
            continue  # quotes check yields the shape error

        qid = q.get("id")
        source_file = SOURCES_DIR / rel_source
        if not source_file.exists():
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({qid!r}): cites missing source file: "
                f"sources/{rel_source}",
                check_name=CHECK_NAME,
            )
            continue
        source_text = extract_source_text(source_file)
        if source_text is None:
            # Distinguish binary-by-design (per BINARY_FORMATS) from
            # extraction-infrastructure failure. pdftotext didn't fail
            # on a .mp4; it was never going to run. Binary-source-citing
            # quotes require manual contributor verification — the
            # validator can't substring-match against bytes that aren't
            # text. Frame the warning accordingly.
            fmt = manifest_format(rel_source)
            if fmt in BINARY_FORMATS:
                yield Issue(
                    ctx.rel, "warn",
                    f"quotes[{i}] ({qid!r}): cites sources/{rel_source} "
                    f"(format: {fmt}) — verbatim-quote check requires manual "
                    f"contributor verification of binary source",
                    check_name=CHECK_NAME,
                )
            else:
                yield Issue(
                    ctx.rel, "warn",
                    f"quotes[{i}] ({qid!r}): cites sources/{rel_source} but "
                    f"text extraction failed (pdftotext missing or failed)",
                    check_name=CHECK_NAME,
                )
            continue
        norm_quote = normalize_for_compare(text)
        norm_source = normalize_for_compare(source_text)
        if norm_quote not in norm_source:
            preview = text[:80] + ("..." if len(text) > 80 else "")
            yield Issue(
                ctx.rel, "error",
                f'quotes[{i}] ({qid!r}): NOT FOUND in sources/{rel_source}: '
                f'"{preview}"',
                check_name=CHECK_NAME,
            )
