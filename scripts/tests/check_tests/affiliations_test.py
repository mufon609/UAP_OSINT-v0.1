"""Per-check unit test for affiliations.

Per ``meta/schema.yaml::types.research-artifact.conditional_keys``,
``affiliations`` is required only when ``target_node_type == person``.
This test exercises the schema gate (out-of-scope target → no-op),
the entry-shape requirements (organization_path, role, source), the
shared lifecycle helpers (id, added_date, duplicate detection), and
the manifest-path consistency check.
"""

from _fixtures import make_base_ctx, make_research_ctx
from checks import affiliations


_SCHEMA = {
    "types": {
        "research-artifact": {
            "conditional_keys": {
                "affiliations": {
                    "required_when_any_of": [{"target_node_type_in": ["person"]}],
                },
            },
        },
    },
}


def _ctx(items, *, target_type="person", manifest_paths=None):
    base = make_base_ctx(
        schema=_SCHEMA,
        manifest_paths=manifest_paths if manifest_paths is not None
        else {"government/x.pdf"},
    )
    return make_research_ctx(
        base=base, target_type=target_type, data={"affiliations": items},
    )


_CLEAN_ENTRY = {
    "id": "a1", "added_date": "2026-01-01",
    "organization_path": "/organizations/x",
    "role": "Director",
    "source": {"path": "government/x.pdf", "location": "p. 1, ¶1"},
}


def test_clean_entry_no_issues():
    assert list(affiliations.check(_ctx([_CLEAN_ENTRY]))) == []


def test_out_of_scope_target_type_no_ops():
    # Section gate: target_type != person → check skips entirely,
    # even though entry-shape is otherwise broken.
    broken = {"id": "a1", "added_date": "2026-01-01"}
    ctx = _ctx([broken], target_type="document")
    assert list(affiliations.check(ctx)) == []


def test_missing_organization_path():
    item = dict(_CLEAN_ENTRY)
    del item["organization_path"]
    issues = list(affiliations.check(_ctx([item])))
    assert any("organization_path" in iss.message for iss in issues)


def test_missing_role():
    item = dict(_CLEAN_ENTRY)
    del item["role"]
    issues = list(affiliations.check(_ctx([item])))
    assert any("role" in iss.message for iss in issues)


def test_organization_path_must_start_with_slash():
    item = dict(_CLEAN_ENTRY, organization_path="organizations/x")
    issues = list(affiliations.check(_ctx([item])))
    assert any("must start with" in iss.message for iss in issues)


def test_source_path_not_in_manifest():
    item = dict(_CLEAN_ENTRY,
                source={"path": "government/missing.pdf", "location": "p. 1, ¶1"})
    ctx = _ctx([item], manifest_paths={"government/x.pdf"})
    issues = list(affiliations.check(ctx))
    assert any("not in sources/manifest.yaml" in iss.message for iss in issues)


def test_source_missing_location():
    item = dict(_CLEAN_ENTRY, source={"path": "government/x.pdf"})
    issues = list(affiliations.check(_ctx([item])))
    assert any("'path' and 'location'" in iss.message for iss in issues)


def test_duplicate_id():
    a = dict(_CLEAN_ENTRY)
    b = dict(_CLEAN_ENTRY, organization_path="/organizations/y", role="Deputy")
    # Both share id "a1"
    issues = list(affiliations.check(_ctx([a, b])))
    assert any("duplicate id" in iss.message for iss in issues)


def test_missing_added_date_lifecycle():
    item = dict(_CLEAN_ENTRY)
    del item["added_date"]
    issues = list(affiliations.check(_ctx([item])))
    assert any("added_date" in iss.message for iss in issues)


def test_section_absent_no_ops():
    # affiliations key absent on artifact: check returns without issues.
    # (iff_section emits the placement error in this case, not affiliations.)
    base = make_base_ctx(schema=_SCHEMA, manifest_paths={"government/x.pdf"})
    ctx = make_research_ctx(base=base, target_type="person", data={})
    assert list(affiliations.check(ctx)) == []
