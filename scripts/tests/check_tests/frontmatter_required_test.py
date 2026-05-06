"""Per-check unit test for frontmatter_required.

Verifies the check fires one error per missing required field listed
in ``type_spec.frontmatter.required``, and stays silent when every
required field is present.
"""

from _fixtures import make_node_ctx
from checks import frontmatter_required


_TYPE_SPEC = {"frontmatter": {"required": ["id", "type", "schema_version"]}}


def test_clean_input_emits_no_issues():
    ctx = make_node_ctx(
        fm={"id": "people/x", "type": "person", "schema_version": 1},
        type_spec=_TYPE_SPEC,
    )
    assert list(frontmatter_required.check(ctx)) == []


def test_missing_required_field_emits_one_error():
    ctx = make_node_ctx(
        fm={"id": "people/x", "type": "person"},
        type_spec=_TYPE_SPEC,
    )
    issues = list(frontmatter_required.check(ctx))
    assert len(issues) == 1
    iss = issues[0]
    assert iss.level == "error"
    assert iss.check_name == "frontmatter_required"
    assert "schema_version" in iss.message


def test_multiple_missing_fields_emit_separate_errors():
    ctx = make_node_ctx(
        fm={"id": "people/x"},
        type_spec=_TYPE_SPEC,
    )
    issues = list(frontmatter_required.check(ctx))
    assert len(issues) == 2
    msgs = " ".join(iss.message for iss in issues)
    assert "type" in msgs and "schema_version" in msgs


def test_empty_required_list_no_ops():
    ctx = make_node_ctx(
        fm={},
        type_spec={"frontmatter": {"required": []}},
    )
    assert list(frontmatter_required.check(ctx)) == []
