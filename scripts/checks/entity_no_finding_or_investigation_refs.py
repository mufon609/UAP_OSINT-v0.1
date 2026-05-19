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

Walks the entire artifact dict recursively for any string that
contains ``/findings/`` or ``/investigations/`` — entities_referenced
wrap_paths, prose strings, source descriptions, anchor refs, anywhere.
Each match yields an error with the field path where the reference was
found.

Symmetric to ``finding_no_investigation_refs`` (which enforces the
finding-side prohibition). Together the two checks lock both ends of
the directional contract.

No-ops on finding / investigation / meta artifacts — those are the
synthesis and governance layers. Entity-layer scope is derived from
schema's ``architecture_layers.entity`` via ``entity_type_names()``,
so adding a new content-node type is a one-line schema edit that
extends the contract automatically.
"""

from checks import Issue
from lib._common import entity_type_names


CHECK_NAME = "entity_no_finding_or_investigation_refs"


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
    for field_path, value in _walk(ctx.data, ""):
        for needle in ("/findings/", "/investigations/"):
            if needle in value:
                yield Issue(
                    ctx.rel, "error",
                    f"entity artifact references the synthesis layer at "
                    f"{field_path!r}: {value[:80]!r}. Entity nodes carry "
                    f"facts; findings and investigations consume them. "
                    f"The flow is one-directional — entity nodes must "
                    f"not reference findings or investigations (see "
                    f"meta/conventions.md 'Three-layer evidentiary "
                    f"architecture').",
                    check_name=CHECK_NAME,
                )
                break  # one Issue per field, regardless of which needle hit
