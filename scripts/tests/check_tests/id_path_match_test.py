"""Per-check unit test for id_path_match.

Verifies the check fires when the frontmatter ``id`` field doesn't
match the node's file path (with ``.md`` stripped), and stays silent
when ``id`` is absent (frontmatter_required handles that case).
"""

from _fixtures import make_node_ctx
from checks import id_path_match


def test_id_matching_path_no_issues():
    ctx = make_node_ctx(rel="people/alex.md", fm={"id": "people/alex"})
    assert list(id_path_match.check(ctx)) == []


def test_id_mismatch_emits_error():
    ctx = make_node_ctx(rel="people/alex.md", fm={"id": "people/wrong-slug"})
    issues = list(id_path_match.check(ctx))
    assert len(issues) == 1
    iss = issues[0]
    assert iss.level == "error"
    assert iss.check_name == "id_path_match"
    assert "people/wrong-slug" in iss.message
    assert "people/alex" in iss.message


def test_absent_id_no_ops():
    ctx = make_node_ctx(rel="people/alex.md", fm={})
    assert list(id_path_match.check(ctx)) == []


def test_falsy_id_no_ops():
    ctx = make_node_ctx(rel="people/alex.md", fm={"id": ""})
    assert list(id_path_match.check(ctx)) == []
