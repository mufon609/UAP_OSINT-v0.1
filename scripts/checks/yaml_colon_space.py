"""yaml-colon-space check — pre-parse research-artifact ResearchContext check.

Parallel pre-parse mechanism to ``yaml_hash_truncation``. Scans for
unquoted scalar values containing an inner ``: `` (colon followed by
space). YAML's block-mapping parser may treat the inner ``: `` as a
nested key/value separator, either parse-erroring or silently
mis-parsing the scalar.

Heuristic skips:

  - URL schemes (word preceding inner colon ∈ known scheme set:
    http, https, mailto, etc.) — those are legitimate URLs.
  - Digit-preceded colons (line numbers, timestamps, ordinals).

Warns only when the post-colon content is ≥2 words, reducing false
positives on single-word sub-keys.

Runs against ``ctx.raw_lines`` before yaml.safe_load.

Origin: introduced at commit ``d9a63a1`` ("validate-research: add
YAML colon-space pre-parse check (BACKLOG #11)") in response to a
real artifact incident — the 2026-04-20 Cluster B hearing-event
pilot. A NewsNation submission title in a publication_record entry
contained an inner ``: `` sequence, which YAML's block-mapping
parser interpreted as a nested key/value separator and broke the
artifact. Fix at the time: single-quote the title + replace the
inner colon with an em-dash. Same shape as ``yaml_hash_truncation``
(real artifact incident → preventive pre-parse check); the two are
structural parallels with different inner-punctuation triggers.

The threshold difference between the two pre-parse checks
(yaml_hash_truncation uses ≥3-word post-`#`; this check uses
≥2-word post-colon) is calibrated to different false-positive
shapes. After ``#``, terse annotations like ``# WIP`` (1 word) are
common contributor practice and shouldn't fire — only ≥3 words
indicates accidental prose truncation. After an inner ``: ``,
legitimate single-word ``key: ` sub-keys are rarer; the lower
threshold catches more real cases without producing the noise that
``# WIP``-style annotations would after ``#``.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
"""

import re

from checks import Issue


CHECK_NAME = "yaml_colon_space"

_PATTERN = re.compile(
    r"^(\s*-?\s*[A-Za-z_][\w-]*:\s+)"     # group 1: outer key + colon + first whitespace
    r"([^'\"|>#\s].*?)"                     # group 2: unquoted value start
    r"(\w+):\s+"                            # group 3: word-preceding-inner-colon
    r"(\S.+)$"                              # group 4: substantive post-colon content
)

_URL_SCHEMES = frozenset({
    "http", "https", "ftp", "ftps", "mailto", "ssh", "file", "git",
    "svn", "ws", "wss", "sftp", "rsync",
})


def check(ctx):
    for lineno, line in enumerate(ctx.raw_lines, start=1):
        m = _PATTERN.match(line.rstrip("\n"))
        if not m:
            continue
        preceding_word = m.group(3)
        post = m.group(4)
        if preceding_word.lower() in _URL_SCHEMES:
            continue
        if preceding_word.isdigit():
            continue
        if len(post.split()) < 2:
            continue
        yield Issue(
            ctx.rel, "warn",
            f"line {lineno}: value contains `{preceding_word}: ` (word "
            f"followed by colon + space) inside an unquoted scalar — "
            f"YAML's block-mapping parser may treat the inner `: ` as a "
            f"key/value separator, either causing a parse error or "
            f"silently truncating the scalar. Fix: quote the entire value "
            f"(single or double quotes), OR replace the inner colon with "
            f"an em-dash `—` / semicolon `;` if typographically "
            f"appropriate. Post-colon content: {post[:60]!r}",
            check_name=CHECK_NAME,
        )
