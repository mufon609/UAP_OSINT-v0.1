"""Per-check unit test for manifest_archive_status.

Covers the four archive_status states (none/local/wayback/both) under
both consistent and inconsistent entry shapes, plus the wayback_skip +
wayback_date contradiction guard.
"""

from _fixtures import make_base_ctx
from checks import manifest_archive_status


def _entry(**overrides):
    """Minimal manifest entry; tests override fields as needed."""
    base = {"url": "https://example.com/x", "format": "html"}
    base.update(overrides)
    return base


def test_clean_local_only_entry():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="archived", path="government/x.pdf", archive_status=1),
    ])
    assert list(manifest_archive_status.check(ctx)) == []


def test_clean_both_archived_entry():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="archived", path="government/x.pdf",
               wayback_date="2026-01-01", archive_status=3),
    ])
    assert list(manifest_archive_status.check(ctx)) == []


def test_clean_pending_entry():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="pending", archive_status=0),
    ])
    assert list(manifest_archive_status.check(ctx)) == []


def test_archive_status_field_missing():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="archived", path="government/x.pdf"),
    ])
    issues = list(manifest_archive_status.check(ctx))
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert "missing" in issues[0].message


def test_archive_status_out_of_range():
    ctx = make_base_ctx(manifest_entries=[_entry(archive_status=5)])
    issues = list(manifest_archive_status.check(ctx))
    assert len(issues) == 1
    assert "0, 1, 2, or 3" in issues[0].message


def test_archive_status_non_integer():
    ctx = make_base_ctx(manifest_entries=[_entry(archive_status="1")])
    issues = list(manifest_archive_status.check(ctx))
    assert len(issues) == 1
    assert "0, 1, 2, or 3" in issues[0].message


def test_bit0_falsely_set():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="pending", archive_status=1),
    ])
    issues = list(manifest_archive_status.check(ctx))
    assert len(issues) == 1
    assert "bit 0" in issues[0].message


def test_bit0_falsely_clear():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="archived", path="government/x.pdf", archive_status=0),
    ])
    issues = list(manifest_archive_status.check(ctx))
    assert len(issues) == 1
    assert "bit 0" in issues[0].message


def test_bit1_falsely_set():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="archived", path="government/x.pdf", archive_status=3),
    ])
    issues = list(manifest_archive_status.check(ctx))
    assert len(issues) == 1
    assert "bit 1" in issues[0].message


def test_wayback_skip_and_wayback_date_contradictory():
    ctx = make_base_ctx(manifest_entries=[
        _entry(status="archived", path="government/x.pdf",
               wayback_skip=True, wayback_date="2026-01-01",
               archive_status=3),
    ])
    issues = list(manifest_archive_status.check(ctx))
    assert any("contradictory" in iss.message for iss in issues)


def test_non_dict_entries_skipped():
    ctx = make_base_ctx(manifest_entries=["not a dict", None, 42])
    assert list(manifest_archive_status.check(ctx)) == []
