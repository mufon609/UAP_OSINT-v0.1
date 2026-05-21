"""Per-phase validator dispatch.

Maps each check (by ``CHECK_NAME``) to the build-pipeline phase whose
output it validates, so an agent can run a phase-scoped pass
(``--phase {archive|extract|organize|link|render}``) for fast feedback
on what it just produced, rather than the full ~67-check sweep. A phase
token is named after the role whose output it validates — see the agent
topology in ``prompts/topology.md``:

  archive   role 3 Archive          (manifest + primary_sources)
  extract   role 4 Worker           (verbatim quotes / speakers)
  organize  role 5 Build, organize  (free-prose synthesis)
  link      role 5 Build, link      (cross-reference surfaces + prose-drift)
  render    role 5 Build, render    (render-time structure + cross-layer)

Role 6 Audit runs the full unflagged pass. Roles 0/1/2 (Orchestrator,
Internal/External Investigator) produce no gated artifact state, so they
have no phase bucket here — their feedback is preflight + manifest tools.

Routing lives HERE, not on the check modules: per
``scripts/checks/__init__.py``, "the [dispatch] lists are the routing
source of truth" — phase is a routing/dispatch concern owned by the
orchestrator layer, so one reviewable map beats a constant scattered
across 67 modules.

``_PHASE_ALIASES`` also accepts the older phase names (``scout`` /
``marker`` / ``manager`` / ``meta-linker`` / ``builder``) and resolves
them to the canonical ones, so existing invocations keep working.

Discipline:
  - ``preflight`` checks (parse / structure / version) run in EVERY
    phase — they gate everything downstream.
  - A check absent from the map defaults to ``render`` (the final
    full pass), so a newly added check is always exercised by an
    unflagged run and is never silently dropped.
  - An unflagged run (``--phase`` not given) runs every check
    regardless — the global consistency pass. ``--phase`` only ever
    NARROWS a run; it never changes the full pass.
"""

# Canonical phase names (each = the role whose output it validates).
PHASES = ("archive", "extract", "organize", "link", "render")

# Older phase names → their canonical equivalents. Accepted on the CLI
# and resolved before comparison so existing invocations keep working.
_PHASE_ALIASES = {
    "scout": "archive",
    "marker": "extract",
    "manager": "organize",
    "meta-linker": "link",
    "builder": "render",
}

# Everything the ``--phase`` flag accepts: the canonical names plus the
# back-compat aliases.
PHASE_CHOICES = PHASES + tuple(_PHASE_ALIASES)

# check CHECK_NAME -> phase whose output it validates.
CHECK_PHASE = {
    # preflight — parse / structural / version; run in every phase
    "frontmatter_parse": "preflight",
    "frontmatter_required": "preflight",
    "artifact_parse": "preflight",
    "artifact_top_level": "preflight",
    "schema_version_compat": "preflight",
    "yaml_colon_space": "preflight",
    "yaml_hash_truncation": "preflight",
    "id_path_match": "preflight",

    # archive (role 3) — source archival (manifest + primary_sources)
    "manifest_parse": "archive",
    "manifest_value_enums": "archive",
    "manifest_archive_status": "archive",
    "manifest_files_present": "archive",
    "manifest_extraction_type": "archive",
    "manifest_artifact_shape": "archive",
    "primary_sources": "archive",
    "doc_form_archival_status": "archive",

    # extract (role 4) — verbatim quote extraction (the one quote boundary)
    "quotes": "extract",
    "verbatim_quotes": "extract",
    "speakers": "extract",
    "speaker_baseline_consistency": "extract",

    # organize (role 5) — free-prose synthesis (incl. claim-group quote organization)
    "top_scope_activity": "organize",
    "corroboration_items": "organize",
    "vouching_chain": "organize",
    "hypotheses": "organize",
    "open_questions": "organize",
    "establishes": "organize",
    "does_not_establish": "organize",

    # link (role 5) — cross-reference surfaces + structured entries.
    # prose_drift lives here (not organize): it scans per-entry synthesis
    # .note/.attestation fields on link-phase entries as well as the
    # organize-phase top-level prose, so the LATEST input phase is link.
    "prose_drift": "link",
    "timeline": "link",
    "affiliations": "link",
    "relationships": "link",
    "program_involvement": "link",
    "publication_record": "link",
    "participants": "link",
    "witnesses_testimony": "link",
    "key_personnel": "link",
    "org_relationships": "link",
    "contracts": "link",
    "ownership_timeline": "link",
    "location_relationships": "link",
    "media_versioning": "link",
    "naming_quirks": "link",
    "rumors": "link",
    "cross_refs": "link",
    "cited_findings": "link",
    "contradictions": "link",
    "closure_path": "link",
    "resolution_history": "link",
    "finding_no_investigation_refs": "link",
    "entity_no_finding_or_investigation_refs": "link",
    "investigation_hypothesis_citation": "link",
    "investigation_closure_path_when_paused": "link",

    # render (role 5 / role 6) — render-time structure + cross-layer
    # (also the default for unlisted checks). chronological_tables,
    # iff_section and finding_source_in_entity_node belong here because
    # they read state that exists only after render: the rendered node
    # body, the full section set, and the global cross-artifact index.
    "status_archetype_kind": "render",
    "conditionally_required": "render",
    "required_sections": "render",
    "section_rules": "render",
    "link_resolution": "render",
    "table_cell_word_budget": "render",
    "coverage": "render",
    "boundary": "render",
    "description_token_drift": "render",
    "phase_iii_inputs": "render",
    "governance_files": "render",
    "chronological_tables": "render",        # reads the RENDERED node body
    "iff_section": "render",                 # needs the full section set present
    "finding_source_in_entity_node": "render",  # needs the global cross-artifact index
}


def canonical_phase(requested_phase):
    """Resolve a CLI ``--phase`` value to its canonical name.

    Accepts both the canonical names and the alias names; passes
    ``None`` (full pass) and any unknown value through unchanged."""
    if requested_phase is None:
        return None
    return _PHASE_ALIASES.get(requested_phase, requested_phase)


def phase_of(check_name):
    """Phase a check belongs to. Unlisted checks default to ``render``
    so the full pass always exercises them."""
    return CHECK_PHASE.get(check_name, "render")


def in_scope(check_name, requested_phase):
    """Whether a check should run for the requested ``--phase``.

    ``requested_phase`` None → full pass (everything runs). Otherwise a
    check runs iff it is a ``preflight`` check (always) or its phase
    equals the requested phase. The requested phase is resolved through
    the back-compat aliases first.
    """
    if requested_phase is None:
        return True
    p = phase_of(check_name)
    return p == "preflight" or p == canonical_phase(requested_phase)
