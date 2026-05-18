"""finding_source_in_entity_node check — finding-only research-artifact check.

Enforces the three-layer evidentiary architecture conservation rule:
findings DUPLICATE primary-source content from entity nodes; the entity
node is updated first before the finding can use it. Per
``meta/conventions.md`` "Three-layer evidentiary architecture":

    Findings DUPLICATE primary-source content from entity nodes BY
    DESIGN. If a finding cites material the relevant entity node
    doesn't yet attest, the entity node is updated first (primary
    source confirmed + archived) before the finding can use it.

Mechanism: for each ``quotes[].source.path`` on a finding artifact,
look up the source path in ``ctx.source_to_artifacts`` (the cross-
artifact index built once at orchestrator entry by
``load_source_to_artifacts_index()``). The index covers entity-type
artifacts only — people, organizations, documents, events,
transcripts, media, locations. If the source path is not cited by any
entity-type artifact's ``primary_sources[]``, the finding is sourcing
material that has no canonical entity-node home.

Severity error. The convention is explicit, not advisory; a warning
would re-create the soft-enforcement gap that produced the original
discipline failure.

Source-path-level granularity (not quote-text-level). The check
verifies the source has at least one entity-node home; verifying the
specific quote text appears in some entity's ``quotes[]`` is a
stricter Level 2 contract that introduces false-positive surface from
legitimate span variations between a finding-evidence quote and an
entity-node quote (different leading lines, different trailing
sentences of the same passage). Level 1 catches the structural gap;
Level 2 can graduate later if Level 1 leaves a real failure case.

No-ops on non-finding artifacts.
"""

from checks import Issue


CHECK_NAME = "finding_source_in_entity_node"


def check(ctx):
    if ctx.target_type != "finding":
        return
    if not isinstance(ctx.data, dict):
        return
    index = ctx.source_to_artifacts
    for i, q in enumerate(ctx.data.get("quotes") or []):
        if not isinstance(q, dict):
            continue
        src = q.get("source")
        if not isinstance(src, dict):
            continue
        path = src.get("path")
        if not isinstance(path, str) or not path:
            continue
        if path not in index:
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): source path {path!r} is "
                f"not cited in any entity-type research artifact's "
                f"primary_sources[]. Per meta/conventions.md \"Three-"
                f"layer evidentiary architecture\", findings duplicate "
                f"primary-source content from entity nodes; the entity "
                f"node is updated first before the finding can use it. "
                f"Build the canonical entity node (typically a "
                f"/documents/{{slug}} node owning this source) and add "
                f"this path to its primary_sources[], then re-validate.",
                check_name=CHECK_NAME,
            )
