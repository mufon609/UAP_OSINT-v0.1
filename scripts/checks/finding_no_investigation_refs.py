"""finding_no_investigation_refs check — finding-only research-artifact check.

Enforces the directional contract: findings DO NOT reference the
investigations that consume them. Investigations link to findings;
findings stay cluster-neutral so they can be cited from multiple
investigations.

Walks the entire artifact dict recursively for any string that
contains ``/investigations/`` — entities_referenced wrap_paths,
prose strings, source descriptions, anchor refs, anywhere. Each
match yields an error with the field path where the reference was
found.

No-ops on non-finding artifacts.
"""

from checks import Issue


CHECK_NAME = "finding_no_investigation_refs"


def _walk(value, path):
    """Yield (path, string) tuples for every string-valued leaf in
    ``value``. ``path`` is the dotted-key trail to the value for
    error-message provenance.
    """
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")


def check(ctx):
    if ctx.target_type != "finding":
        return
    if not isinstance(ctx.data, dict):
        return
    for field_path, value in _walk(ctx.data, ""):
        if "/investigations/" in value:
            yield Issue(
                ctx.rel, "error",
                f"finding artifact references an investigation at "
                f"{field_path!r}: {value[:80]!r}. Findings must stay "
                f"cluster-neutral; investigations cite findings, not "
                f"the other way around (see meta/conventions.md "
                f"'Three-layer evidentiary architecture').",
                check_name=CHECK_NAME,
            )
