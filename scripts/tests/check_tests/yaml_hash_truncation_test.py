"""Per-check unit test for yaml_hash_truncation.

The check is a pre-parse warn — it scans raw lines for unquoted
scalars where YAML would silently truncate at ` #`. The substantive-
post-`#`-content heuristic (≥ 3 words) keeps the warning targeted on
likely accidental truncation rather than firing on every legitimate
YAML comment.
"""

from _fixtures import make_research_ctx
from checks import yaml_hash_truncation


def _ctx(*lines):
    return make_research_ctx(
        raw_lines=[ln if ln.endswith("\n") else ln + "\n" for ln in lines]
    )


def test_clean_yaml_no_warnings():
    ctx = _ctx("id: meta/research/test", "type: research-artifact")
    assert list(yaml_hash_truncation.check(ctx)) == []


def test_quoted_scalar_with_hash_no_warning():
    # Quoted values are not subject to YAML's ` #` comment handling;
    # the regex deliberately exempts lines whose value starts with a
    # quote character.
    ctx = _ctx("note: 'see Issue #3 in the tracker'")
    assert list(yaml_hash_truncation.check(ctx)) == []


def test_terse_inline_comment_no_warning():
    # Heuristic: post-`#` content < 3 words is plausibly a deliberate
    # contributor annotation, not accidental prose truncation.
    ctx = _ctx("status: active # WIP")
    assert list(yaml_hash_truncation.check(ctx)) == []


def test_substantive_post_hash_content_warns():
    ctx = _ctx("note: see Issue #3 for the full open-question context")
    issues = list(yaml_hash_truncation.check(ctx))
    assert len(issues) == 1
    iss = issues[0]
    assert iss.level == "warn"
    assert iss.check_name == "yaml_hash_truncation"
    assert "line 1" in iss.message


def test_warning_carries_line_number_for_later_lines():
    ctx = _ctx(
        "id: meta/research/test",
        "type: research-artifact",
        "note: refers to Issue #3 documented in the tracker thread",
    )
    issues = list(yaml_hash_truncation.check(ctx))
    assert len(issues) == 1
    assert "line 3" in issues[0].message


def test_pure_comment_line_no_warning():
    # A line starting with `#` (after optional whitespace) is a comment,
    # not a key:value pair; the regex requires `key:` at line start.
    ctx = _ctx("# this whole line is a comment with substantive content")
    assert list(yaml_hash_truncation.check(ctx)) == []
