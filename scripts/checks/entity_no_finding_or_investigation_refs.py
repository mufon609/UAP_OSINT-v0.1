"""entity_no_finding_or_investigation_refs check — entity-only research-artifact check.

Enforces the three-layer evidentiary architecture directional contract
from the entity side: entity nodes do not reference findings or
investigations. Facts flow up to the synthesis layer; the synthesis
layer does not flow back into the fact substrate. Per
``meta/conventions.md`` "Three-layer evidentiary architecture":

    Entity nodes carry facts. Findings consume entity-node facts to
    document multi-source patterns. Investigations consume findings
    and entity-node facts to evaluate hypotheses. The flow is
    one-directional — entity nodes do not reference findings or
    investigations.

Walks the entire artifact dict recursively for any string that contains a
``/findings/`` or ``/investigations/`` path **or a bare finding /
investigation node slug** (from ``ctx.synthesis_slugs``) — prose strings,
source descriptions, anchor refs, anywhere. The bare-slug case catches a
prose reference like "the <slug> finding" that carries no path. Each match
yields an error with the field path where the reference was found.

Symmetric to ``finding_no_investigation_refs`` (which enforces the
finding-side prohibition). Together the two checks lock both ends of
the directional contract.

No-ops on finding / investigation / meta artifacts — those are the
synthesis and governance layers. Entity-layer scope is derived from
schema's ``architecture_layers.entity`` via ``entity_type_names()``,
so adding a new content-node type is a one-line schema edit that
extends the contract automatically.
"""

import re

from checks import Issue
from lib._common import entity_type_names


CHECK_NAME = "entity_no_finding_or_investigation_refs"


def _forbidden_slug_re(slugs):
    """Compile a boundary-anchored alternation over node slugs, or None if
    the set is empty. The boundaries (no adjacent word-char or hyphen) keep a
    slug from matching as a fragment of a longer hyphenated token — e.g. a
    source filename that merely shares a place name."""
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
    if ctx.target_type not in entity_type_names():
        return
    if not isinstance(ctx.data, dict):
        return
    forbidden = ((ctx.synthesis_slugs.get("finding") or frozenset())
                 | (ctx.synthesis_slugs.get("investigation") or frozenset()))
    slug_re = _forbidden_slug_re(forbidden)
    for field_path, value in _walk(ctx.data, ""):
        hit = next((n for n in ("/findings/", "/investigations/") if n in value), None)
        if hit is None and slug_re is not None:
            m = slug_re.search(value)
            if m:
                hit = f"bare slug {m.group(1)!r}"
        if hit is None:
            continue  # one Issue per field, regardless of which form hit
        yield Issue(
            ctx.rel, "error",
            f"entity artifact references the synthesis layer at "
            f"{field_path!r} ({hit}): {value[:80]!r}. Entity nodes carry "
            f"facts; findings and investigations consume them. The flow is "
            f"one-directional — entity nodes must not reference findings or "
            f"investigations, even by bare slug in prose (see "
            f"meta/conventions.md 'Tier model and linking contract').",
            check_name=CHECK_NAME,
        )
