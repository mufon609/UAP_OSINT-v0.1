"""finding_no_finding_refs check — finding-only research-artifact check.

Same-tier prohibition (Tier 3): a finding never references **another** finding.
Findings are independent, cluster-neutral multi-source patterns; cross-finding
synthesis belongs on an investigation (Tier 4), not inside a finding. Per
the build-protocol "Tier linking contract".

For a finding artifact, walks every string leaf and flags any reference to
another finding's node slug (from ``ctx.synthesis_slugs['finding']`` minus this
finding's own slug) — both the ``/findings/<slug>`` path form and a bare-slug
prose mention are caught by one boundary-anchored alternation (the boundaries
keep a slug from matching as a fragment of a longer hyphenated token). This
finding's own slug — which appears in its ``id`` / ``target_node`` — is excluded,
so a self-reference is not a violation.

No-ops on non-finding artifacts and when this is the only finding (the
other-slug set is then empty). Symmetric to
``investigation_no_investigation_refs`` (the Tier-4 same-tier check) and to the
cross-tier ``finding_no_investigation_refs``.
"""

import re

from checks import Issue


CHECK_NAME = "finding_no_finding_refs"


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
    if ctx.target_type != "finding":
        return
    if not isinstance(ctx.data, dict):
        return
    own = (ctx.data.get("target_node") or "").rsplit("/", 1)[-1]
    slug_re = _other_slug_re(ctx.synthesis_slugs.get("finding") or frozenset(), own)
    if slug_re is None:
        return
    for field_path, value in _walk(ctx.data, ""):
        m = slug_re.search(value)
        if m:
            yield Issue(
                ctx.rel, "error",
                f"finding artifact references another finding at {field_path!r} "
                f"(slug {m.group(1)!r}): {value[:80]!r}. Findings are independent "
                f"and cluster-neutral — a finding never references another finding "
                f"(Tier-3 same-tier prohibition; cross-finding synthesis belongs on "
                f"an investigation). See the build-protocol 'Tier "
                f"linking contract'.",
                check_name=CHECK_NAME,
            )
