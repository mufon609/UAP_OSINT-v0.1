"""Per-check unit test for iff_section.

Exercises the schema-driven placement-error dispatch against the
``required_when_any_of`` grammar (per BACKLOG C15): each rule's fields
AND-combine; the rule list OR-combines. Includes an AND-combined rule
(``witnesses_testimony``: type=event AND kind=hearing) to confirm the
conjunctive case fires correctly — the case the flat OR-keys grammar
couldn't express.
"""

from _fixtures import make_base_ctx, make_research_ctx
from checks import iff_section


_SCHEMA = {
    "types": {
        "research-artifact": {
            "conditional_keys": {
                "rumors": {
                    "required_when_any_of": [
                        {"target_node_type_in":
                            ["person", "organization", "event", "location"]},
                    ],
                },
                "witnesses_testimony": {
                    "required_when_any_of": [
                        {
                            "target_node_type_in": ["event"],
                            "target_node_kind_in": ["hearing"],
                        },
                    ],
                },
            },
        },
    },
}


def _ctx(**kw):
    base = make_base_ctx(schema=_SCHEMA)
    return make_research_ctx(base=base, **kw)


def test_in_scope_section_present_no_issues():
    ctx = _ctx(target_type="person", data={"rumors": []})
    assert list(iff_section.check(ctx)) == []


def test_in_scope_section_missing_emits_error():
    ctx = _ctx(target_type="person", data={})
    issues = list(iff_section.check(ctx))
    assert any(iss.level == "error" and "rumors" in iss.message
               and "missing" in iss.message for iss in issues)


def test_out_of_scope_section_present_emits_error():
    # rumors not applicable to documents; section presence is wrong.
    ctx = _ctx(target_type="document", data={"rumors": []})
    issues = list(iff_section.check(ctx))
    assert any(iss.level == "error" and "rumors" in iss.message
               and "should not be present" in iss.message for iss in issues)


def test_AND_combined_rule_partial_match_out_of_scope():
    # type=event satisfies only half the witnesses_testimony rule;
    # kind=encounter does not satisfy target_node_kind_in: [hearing].
    ctx = _ctx(target_type="event", target_kind="encounter",
               data={"witnesses_testimony": [], "rumors": []})
    issues = list(iff_section.check(ctx))
    assert any("witnesses_testimony" in iss.message
               and "should not be present" in iss.message for iss in issues)


def test_AND_combined_rule_full_match_in_scope():
    ctx = _ctx(target_type="event", target_kind="hearing",
               data={"witnesses_testimony": [], "rumors": []})
    assert list(iff_section.check(ctx)) == []


def test_target_type_none_short_circuits():
    # Defensive: when target discovery fails upstream, this check
    # cannot evaluate any rule and must stay silent.
    ctx = _ctx(target_type=None, data={"rumors": []})
    assert list(iff_section.check(ctx)) == []


def test_unknown_section_not_in_schema_no_ops():
    # iff_section only walks declared conditional_keys; ignores
    # everything else in the artifact.
    ctx = _ctx(target_type="person",
               data={"rumors": [], "some_unrelated_section": "value"})
    issues = list(iff_section.check(ctx))
    msgs = " ".join(iss.message for iss in issues)
    assert "some_unrelated_section" not in msgs
