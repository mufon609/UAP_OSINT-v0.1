"""yaml-hash-truncation check — pre-parse research-artifact ResearchContext check.

Scans raw lines for unquoted scalar values that contain ``space + #``
and get silently truncated by YAML's comment handling. Surfaces as
warn — the YAML is technically valid; the check flags a likely
contributor mistake where prose with an embedded ``#N`` reference
loses everything after the ``#`` to YAML's trailing-comment handling.

Pre-parse: runs against the file's raw line text BEFORE
``yaml.safe_load``. The orchestrator opens the file once and exposes
the lines via ``ctx.raw_lines``; this check only reads.

Heuristic tolerates one-line trailing comments (post-`#` content under
3 words plausibly a deliberate contributor note). Only warns when the
post-`#` content looks substantive (≥ 3 words) — that's the shape that
indicates accidental truncation of prose. Known accepted false-
negative: short ``#N`` references trailing prose (``key: see Issue #3``)
truncate but don't warn since the post-`#` token count is below the
threshold; the introducing commit treated that as the cost of keeping
``# WIP``-style annotations from drowning the warn channel.

Origin: surfaced during the F.4c FLIR1 media pilot (commit ``c065e4a``).
The pilot's research artifact carried a methodology field whose
unquoted scalar contained ``validate.py check #11 returns warn...`` —
YAML's space-`#` rule truncated the value at ``check`` and the post-`#`
clause was silently lost from the rendered Open Questions section. The
3-word threshold was calibrated against that specific shape.
"""

import re
from checks import Issue


CHECK_NAME = "yaml_hash_truncation"


# Pattern for lines that look like ``key: value # more content`` where
# the ``#`` is preceded by whitespace and followed by non-whitespace,
# inside an UNQUOTED scalar value. Two common false-positives are
# explicitly permitted: pure comment lines, and lines where ``#``
# appears at the very start of the value (those don't truncate
# meaningful content).
_PATTERN = re.compile(
    r"^(\s*-?\s*[A-Za-z_][\w-]*:\s+)"      # group 1: key + colon + first whitespace
    r"([^'\"|>#\s].+?)"                      # group 2: unquoted value (non-trivial)
    r"(\s+#\S.*)$"                           # group 3: whitespace + # + non-ws + rest
)


def check(ctx):
    """Yield warn-level Issue for any line where YAML's comment handling
    will silently truncate a substantive scalar."""
    for lineno, line in enumerate(ctx.raw_lines, start=1):
        m = _PATTERN.match(line.rstrip("\n"))
        if not m:
            continue
        comment_part = m.group(3).strip()
        post_hash = comment_part[1:].strip()  # drop leading "#"
        # Heuristic: post-# content >= 3 words suggests accidental
        # truncation of prose. Fewer words = plausibly a deliberate
        # terse annotation; don't warn.
        if len(post_hash.split()) < 3:
            continue
        yield Issue(
            ctx.rel, "warn",
            f"line {lineno}: value contains ` #` followed by substantive content "
            f"— YAML will silently treat everything after `#` as a comment and "
            f"truncate the scalar. If the `#` is intentional content (e.g., "
            f"\"Issue #3\", \"channel #23\"), quote the entire value "
            f"(single or double quotes) or use a YAML literal block (`|`). "
            f"Post-`#` content that will be truncated: {post_hash[:80]!r}",
            check_name=CHECK_NAME,
        )
