"""released-via-consistency check — per-node NodeContext check (document-only).

A document's optional frontmatter ``released_via`` back-points to the
``/foia/{slug}`` node(s) whose release produced it. The back-pointer is a
provenance claim, so it must agree with the forward record: the foia
node's research artifact lists the document in ``released_records[]``
(``document_path``). A ``released_via`` the foia artifact does not attest
is an unsupported provenance claim → error.

An unbuilt foia target (no artifact yet) is left to ``link_resolution``,
which records it on the broken-link registry — the same backlog treatment
as any other forward stub. A non-foia target path is an error: the field
points only at foia nodes.

No-ops when node_type is not ``document`` or ``released_via`` is unset.
"""

from checks import Issue
from lib._common import RESEARCH_DIR, frontmatter_node_paths, strict_yaml_load


CHECK_NAME = "released_via_consistency"


def _released_document_paths(artifact_path):
    """Return the set of ``released_records[].document_path`` values on a
    foia artifact (leading-slash normalized), or None when the artifact is
    absent / unparseable (other validators own those cases)."""
    if not artifact_path.exists():
        return None
    try:
        with open(artifact_path) as f:
            data = strict_yaml_load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    out = set()
    for e in data.get("released_records") or []:
        if isinstance(e, dict) and isinstance(e.get("document_path"), str):
            out.add("/" + e["document_path"].strip().lstrip("/"))
    return out


def check(ctx):
    if ctx.node_type != "document":
        return
    self_path = "/" + str(ctx.rel).removesuffix(".md")
    for target in frontmatter_node_paths("document", ctx.fm):
        parts = target.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "foia":
            yield Issue(
                ctx.rel, "error",
                f"released_via {target!r} must be a /foia/{{slug}} node path",
                check_name=CHECK_NAME,
            )
            continue
        released = _released_document_paths(RESEARCH_DIR / f"{parts[1]}.yaml")
        if released is None:
            continue  # unbuilt foia node — link_resolution registers the stub
        if self_path not in released:
            yield Issue(
                ctx.rel, "error",
                f"released_via {target!r}: that foia node's research artifact "
                f"does not list {self_path} in released_records[] — add the "
                f"release there (with its source) or drop the back-pointer",
                check_name=CHECK_NAME,
            )
