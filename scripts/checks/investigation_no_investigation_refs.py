"""investigation_no_investigation_refs check — investigation-only check.

Same-tier prohibition (Tier 4): an investigation never references **another**
investigation. Investigations are the top of the iceberg — they consume findings
(Tier 3) and entity facts (Tier 2); nothing references an investigation,
including other investigations. Per ``meta/conventions.md`` "Tier model and
linking contract".

For an investigation artifact, walks every string leaf and flags any reference
to another investigation's node slug (from ``ctx.synthesis_slugs['investigation']``
minus this investigation's own slug) — both the ``/investigations/<slug>`` path
form and a bare-slug prose mention, via one boundary-anchored alternation. This
investigation's own slug (in its ``id`` / ``target_node``) is excluded, so a
self-reference is not a violation. Downward references to findings
(``finding_path: /findings/...``) and entity nodes are allowed and untouched.

No-ops on non-investigation artifacts and when this is the only investigation
(the other-slug set is then empty). Symmetric to ``finding_no_finding_refs``
(the Tier-3 same-tier check).
"""

import re

from checks import Issue


CHECK_NAME = "investigation_no_investigation_refs"


def _walk(value, path):
    """Yield (path, string) tuples for every string-valued leaf in ``value``."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")


def _other_slug_re(slugs, own):
    """Boundary-anchored alternation over node slugs excluding ``own``, or None
    if nothing remains."""
    others = sorted(s for s in slugs if s and s != own)
    if not others:
        return None
    return re.compile(
        r"(?<![\w-])(" + "|".join(re.escape(s) for s in others) + r")(?![\w-])"
    )


def check(ctx):
    if ctx.target_type != "investigation":
        return
    if not isinstance(ctx.data, dict):
        return
    own = (ctx.data.get("target_node") or "").rsplit("/", 1)[-1]
    slug_re = _other_slug_re(ctx.synthesis_slugs.get("investigation") or frozenset(), own)
    if slug_re is None:
        return
    for field_path, value in _walk(ctx.data, ""):
        m = slug_re.search(value)
        if m:
            yield Issue(
                ctx.rel, "error",
                f"investigation artifact references another investigation at "
                f"{field_path!r} (slug {m.group(1)!r}): {value[:80]!r}. An "
                f"investigation is the top tier — nothing references an "
                f"investigation, including other investigations (Tier-4 same-tier "
                f"prohibition). See meta/conventions.md 'Tier model and linking "
                f"contract'.",
                check_name=CHECK_NAME,
            )
