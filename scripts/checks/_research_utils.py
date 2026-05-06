"""Shared helpers for research-artifact checks.

Every per-section entry check in validate-research.py walks the same
shape: list of entries, each a dict with ``id`` + ``added_date``
lifecycle fields, optional ``source: {path, location}`` dict whose
path must appear in ``sources/manifest.yaml``. The four helpers below
factor that shape so each per-check module isn't a ~50-line copy of
the same scaffolding.

Module name carries a leading underscore to signal "private to the
checks/ package — internal scaffolding, not contract surface."
``checks.Issue`` and the Context types are the public contract.
"""

from checks import Issue


def entries(data, section):
    """Return list of entries for a section, or [] if absent or
    malformed. Always a list — caller can iterate without None
    checks."""
    v = data.get(section)
    return v if isinstance(v, list) else []


def check_unique_ids(rel, items, section_name, check_name):
    """Yield Issues for any entry missing 'id' or duplicating an id
    already seen in this section."""
    seen = set()
    for i, entry in enumerate(items):
        if not isinstance(entry, dict):
            yield Issue(
                rel, "error",
                f"{section_name}[{i}]: entry must be a dict",
                check_name=check_name,
            )
            continue
        eid = entry.get("id")
        if eid is None:
            yield Issue(
                rel, "error",
                f"{section_name}[{i}]: missing required 'id' field",
                check_name=check_name,
            )
            continue
        if eid in seen:
            yield Issue(
                rel, "error",
                f"{section_name}[{i}]: duplicate id {eid!r}",
                check_name=check_name,
            )
        seen.add(eid)


def check_lifecycle_fields(rel, entry, section_name, i, check_name):
    """Every entry requires id + added_date. Yields Issues for any
    missing field."""
    for field in ("id", "added_date"):
        if field not in entry:
            yield Issue(
                rel, "error",
                f"{section_name}[{i}] ({entry.get('id', '?')!r}): "
                f"missing required lifecycle field {field!r}",
                check_name=check_name,
            )


def require_source_dict(rel, entry, section_name, i, manifest_paths, check_name):
    """Verify entry.source is a dict with path + location, and the
    path appears in the manifest. Yields Issues for any violation."""
    src = entry.get("source")
    if not isinstance(src, dict):
        yield Issue(
            rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"'source' must be a dict with path + location",
            check_name=check_name,
        )
        return
    if "path" not in src or "location" not in src:
        yield Issue(
            rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"source must include 'path' and 'location'",
            check_name=check_name,
        )
    if src.get("path") and src["path"] not in manifest_paths:
        yield Issue(
            rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"source.path {src['path']!r} not in sources/manifest.yaml",
            check_name=check_name,
        )
