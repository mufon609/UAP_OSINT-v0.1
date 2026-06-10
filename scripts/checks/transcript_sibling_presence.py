"""transcript-sibling-presence check — ResearchContext check (transcript
artifacts).

The seam this closes. ``speaker_attribution_consistency`` cross-validates
each transcript quote's ``speaker_id`` against the verified attribution
sibling — but a source with no verified sibling is *skipped* there by
design (presence is a separate invariant). Without a presence gate, a
label-less or unclassified transcript source (``transcript_provenance``
absent or ``unknown``) ships hand-keyed ``speaker_id`` green: the one
mechanical attribution check silently never runs. This check is the
presence gate.

Allowlist, not blocklist. Only the two human-attested labeled classes —
``stenographic`` / ``published-transcript`` (schema
``artifact_entry.transcript_provenance_values``) — carry trustworthy
inline speaker labels and need no sibling. Every other provenance
(``auto-caption``, ``human-corrected-caption``, an explicit ``unknown``,
or an absent flag) requires a verified ``-attribution.yaml`` sibling
before the artifact's quotes can carry ``speaker_id``. Keying on the
allowlist rather than enumerating the label-less classes means an
unclassified source fails closed. The fix is
``/prepare-transcript-sibling`` (and classifying the source's real
provenance in the manifest while there).

Phase: extract — sibling presence is a precondition of the extract-phase
attribution chain (``stamp-speaker-id.py`` derive +
``speaker_attribution_consistency``). It fires once the artifact exists
with its source set, after the ``/build`` 4c gate has had its chance to
produce the sibling; the archive phase would fire at scaffold time,
before 4c runs.

Sibling resolution is shared with ``speaker_attribution_consistency``
(``_load_siblings`` — verified siblings indexed by their declared
``source_path``), so "present" here is exactly "will not be skipped
there".

Severity: warn, not error — transcript nodes built before this gate
existed carry hand-attributed quotes on sibling-less sources, and a
backfill via ``/prepare-transcript-sibling`` is the only honest fix
(see the BACKLOG backfill item). Promote to error once every
label-less transcript source in the corpus carries a verified sibling;
a missing sibling is definitionally a defect, so error is this check's
end state.
"""

from checks import Issue
from checks.speaker_attribution_consistency import _load_siblings
from lib._common import iter_artifacts


CHECK_NAME = "transcript_sibling_presence"

# Provenance classes whose bytes carry human-attested inline speaker
# labels — the only classes that need no attribution sibling.
_LABELED = frozenset({"stenographic", "published-transcript"})


def check(ctx):
    if ctx.target_type != "transcript":
        return

    sources = ctx.data.get("primary_sources") or []
    if not isinstance(sources, list) or not sources:
        return

    path_to_artifact = {
        artifact.get("path"): artifact
        for _, artifact in iter_artifacts(ctx.manifest_entries)
    }
    siblings = None  # loaded lazily — most artifacts aren't transcript-sourced

    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        path = src.get("path")
        artifact = path_to_artifact.get(path)
        if artifact is None:
            continue  # unregistered path is primary_sources' finding
        if artifact.get("format") != "transcript":
            continue
        provenance = artifact.get("transcript_provenance")
        if provenance in _LABELED:
            continue
        if siblings is None:
            siblings = _load_siblings()
        if path in siblings:
            continue
        yield Issue(
            ctx.rel, "warn",
            f"primary_sources[{i}]: transcript source {path!r} "
            f"(transcript_provenance: "
            f"{provenance if provenance is not None else 'absent — unclassified'}) "
            f"has no verified attribution sibling — speaker_id cannot be "
            f"derived, and speaker_attribution_consistency would silently "
            f"skip it. Only stenographic / published-transcript sources "
            f"carry trustworthy inline labels; produce + verify + register "
            f"a sibling via /prepare-transcript-sibling (and set the "
            f"source's real transcript_provenance in the manifest if it is "
            f"unclassified)",
            check_name=CHECK_NAME,
        )
