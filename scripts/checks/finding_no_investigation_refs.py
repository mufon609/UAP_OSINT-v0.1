"""finding_no_investigation_refs check — finding-only research-artifact check.

Enforces the directional contract: findings DO NOT reference the
investigations that consume them. Investigations link to findings;
findings stay cluster-neutral so they can be cited from multiple
investigations.

Walks the entire artifact dict recursively for any string that contains an
``/investigations/`` path **or a bare investigation node slug** (from
``ctx.synthesis_slugs``) — prose strings, source descriptions, anchor refs,
anywhere. The bare-slug case catches a prose reference that carries no path.
Each match yields an error with the field path where the reference was found.

(This check is the finding→investigation half of the tier contract; the
finding→finding same-tier prohibition is enforced by the sibling
``finding_no_finding_refs`` check.)

No-ops on non-finding artifacts.
"""

import re

from checks import Issue


CHECK_NAME = "finding_no_investigation_refs"


def _forbidden_slug_re(slugs):
    """Boundary-anchored alternation over node slugs, or None if empty
    (boundaries keep a slug from matching as a fragment of a longer token)."""
    if not slugs:
        return None
    return re.compile(
        r"(?<![\w-])(" + "|".join(re.escape(s) for s in sorted(slugs)) + r")(?![\w-])"
    )


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
    slug_re = _forbidden_slug_re(ctx.synthesis_slugs.get("investigation") or frozenset())
    for field_path, value in _walk(ctx.data, ""):
        hit = "/investigations/" if "/investigations/" in value else None
        if hit is None and slug_re is not None:
            m = slug_re.search(value)
            if m:
                hit = f"bare slug {m.group(1)!r}"
        if hit is None:
            continue
        yield Issue(
            ctx.rel, "error",
            f"finding artifact references an investigation at "
            f"{field_path!r} ({hit}): {value[:80]!r}. Findings must stay "
            f"cluster-neutral; investigations cite findings, not the other "
            f"way around — even by bare slug in prose (see meta/conventions.md "
            f"'Tier model and linking contract').",
            check_name=CHECK_NAME,
        )
