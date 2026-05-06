"""Per-check unit test for conditionally_required.

Exercises both routes the check dispatches on: frontmatter-field route
(lowercase keys; presence + vocabulary check) and section-name route
(Title-Case keys; H2 presence check), plus condition-evaluation
edge cases (inactive / active / malformed grammar).
"""

from _fixtures import make_node_ctx
from checks import conditionally_required


_TYPE_SPEC_DOCUMENT = {
    "conditionally_required": {"archival_status": "doc_form == book"},
    "archival_status_values": ["full-text-archived", "excerpts-only", "not-archived"],
}

_TYPE_SPEC_MEDIA = {
    "conditionally_required": {"Media Versioning": "derivation_of is set"},
}


def test_inactive_condition_no_ops():
    # doc_form != "book" → condition is false; no requirement applies.
    ctx = make_node_ctx(
        fm={"doc_form": "article"},
        type_spec=_TYPE_SPEC_DOCUMENT,
    )
    assert list(conditionally_required.check(ctx)) == []


def test_active_condition_field_missing_emits_error():
    ctx = make_node_ctx(
        fm={"doc_form": "book"},
        type_spec=_TYPE_SPEC_DOCUMENT,
    )
    issues = list(conditionally_required.check(ctx))
    assert len(issues) == 1
    iss = issues[0]
    assert iss.level == "error"
    assert "archival_status" in iss.message


def test_active_condition_invalid_value_emits_error():
    ctx = make_node_ctx(
        fm={"doc_form": "book", "archival_status": "bogus-value"},
        type_spec=_TYPE_SPEC_DOCUMENT,
    )
    issues = list(conditionally_required.check(ctx))
    assert len(issues) == 1
    assert "bogus-value" in issues[0].message
    assert "Valid:" in issues[0].message


def test_active_condition_valid_value_no_ops():
    ctx = make_node_ctx(
        fm={"doc_form": "book", "archival_status": "full-text-archived"},
        type_spec=_TYPE_SPEC_DOCUMENT,
    )
    assert list(conditionally_required.check(ctx)) == []


def test_section_name_route_active_section_missing():
    ctx = make_node_ctx(
        rel="media/x.md",
        fm={"derivation_of": "/media/parent"},
        text="# Title\n\n## Description\n\nbody\n",
        type_spec=_TYPE_SPEC_MEDIA,
    )
    issues = list(conditionally_required.check(ctx))
    assert len(issues) == 1
    assert "Media Versioning" in issues[0].message


def test_section_name_route_active_section_present():
    ctx = make_node_ctx(
        rel="media/x.md",
        fm={"derivation_of": "/media/parent"},
        text="# Title\n\n## Media Versioning\n\nbody\n",
        type_spec=_TYPE_SPEC_MEDIA,
    )
    assert list(conditionally_required.check(ctx)) == []


def test_section_name_route_condition_false_no_ops():
    # No derivation_of → condition false; section absence is not enforced.
    ctx = make_node_ctx(
        rel="media/x.md",
        fm={},
        text="# Title\n\n## Description\n\nbody\n",
        type_spec=_TYPE_SPEC_MEDIA,
    )
    assert list(conditionally_required.check(ctx)) == []


def test_malformed_condition_emits_error():
    ctx = make_node_ctx(
        type_spec={"conditionally_required": {"foo": "garbage condition string"}},
    )
    issues = list(conditionally_required.check(ctx))
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert "garbage condition string" in issues[0].message


def test_no_conditionally_required_block_no_ops():
    ctx = make_node_ctx(type_spec={})
    assert list(conditionally_required.check(ctx)) == []
