"""associated-entities check — research-artifact ResearchContext check.

Validates the optional ``associated_entities`` top-level field: the
complete, authoritative list of every load-bearing entity the node's
primary source(s) name, as canonical ``/{type}/{slug}`` paths.
``scripts/build/associate.py`` unions these into the ``## Associated
Nodes`` link set it harvests from body wraps — the mechanism that lets
an entity named ONLY inside a verbatim quote (which can never be wrapped:
the verbatim-quote check rejects a link injected into ``quote.text``)
reach Associated Nodes WITHOUT depending on the author re-naming it in
``description`` prose. See the build-protocol "name it, wrap it" contract
and ``schema-research-artifact.yaml::optional_keys.associated_entities``.

The field is OPTIONAL during the corpus-wide rollout (absence is silent,
so existing un-swept nodes don't break — they are the C5 backlog queue).
When the field IS present this check enforces:

  1. Shape — a flat list of well-formed ``/{type}/{slug}`` strings whose
     ``{type}`` is a real content directory; no duplicates (the list is
     deduped by contract).
  2. Completeness superset — every entity a node wraps inline in its OWN
     authored prose (``description`` / ``background`` / ``top_relevance``
     / ``credibility_notes``) MUST also appear in ``associated_entities``.
     The field is the single auditable record of everything the node
     names; an inline wrap that isn't in the field means the field is no
     longer complete. (associate.py still renders the wrap correctly via
     its body scan — this guards the field's integrity, not the rendered
     section.)

The fuzzy "is some quote-named institution missing from the field?"
discovery is deliberately NOT a gate WARN here (it cannot be made
false-positive-free, and a persistent advisory would dirty the
0-warning clean baseline). That net lives in the read-only
``scripts/tools/coverage-suggest.py`` diagnostic + the auditor's manual
pass (.claude/agents/auditor.md), judged per case.
"""

import re

from checks import Issue
from lib._common import content_dirs


CHECK_NAME = "associated_entities"

# Same wrap form associate.py harvests: [`/type/slug`].
_WRAP = re.compile(r"\[`(/[^`]+)`\]")

# Authored-prose fields a node may wrap entities in. extrinsic_authorship
# is intentionally excluded — an externally-attested redacted author is
# carried by the redacted-author convention, not associated_entities.
_PROSE_FIELDS = ("description", "background", "top_relevance", "credibility_notes")


def _valid_path(p, valid_types):
    if not isinstance(p, str):
        return False
    parts = p.strip("/").split("/")
    return len(parts) == 2 and parts[0] in valid_types and bool(parts[1])


def check(ctx):
    data = ctx.data
    if "associated_entities" not in data:
        return  # optional; absence is silent (C5 rollout)

    ae = data.get("associated_entities")
    if not isinstance(ae, list):
        yield Issue(
            ctx.rel, "error",
            f"associated_entities must be a list of /type/slug paths; "
            f"got {type(ae).__name__}",
            check_name=CHECK_NAME,
        )
        return

    valid_types = set(content_dirs())

    # 1. Shape + duplicates
    seen = set()
    members = set()
    for i, p in enumerate(ae):
        if not _valid_path(p, valid_types):
            yield Issue(
                ctx.rel, "error",
                f"associated_entities[{i}] ({p!r}): not a well-formed "
                f"/{{type}}/{{slug}} path (type must be one of "
                f"{sorted(valid_types)})",
                check_name=CHECK_NAME,
            )
            continue
        if p in seen:
            yield Issue(
                ctx.rel, "error",
                f"associated_entities[{i}] ({p!r}): duplicate entry "
                f"(the list is deduped by contract)",
                check_name=CHECK_NAME,
            )
        seen.add(p)
        members.add(p)

    # 2. Completeness superset — every inline prose-wrap must be a member.
    self_path = "/" + str(data.get("target_node") or "").strip("/")
    for field in _PROSE_FIELDS:
        text = data.get(field)
        if not isinstance(text, str):
            continue
        for wrap in _WRAP.findall(text):
            if wrap == self_path:
                continue  # self-reference (associate.py discards it too)
            if wrap not in members:
                yield Issue(
                    ctx.rel, "error",
                    f"{field} wraps {wrap!r} but it is absent from "
                    f"associated_entities — the field must list every "
                    f"entity the node names (add {wrap!r})",
                    check_name=CHECK_NAME,
                )
