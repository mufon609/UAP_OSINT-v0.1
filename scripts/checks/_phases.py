"""Per-phase validator dispatch — A2 increment 3 (the A4 mechanism).

Maps each check (by ``CHECK_NAME``) to the build-pipeline agent phase
whose output it validates, so an agent can run a phase-scoped pass
(``--phase {scout|marker|manager|meta-linker|builder}``) for fast
feedback on what it just produced, rather than the full ~67-check
sweep. The five phases mirror the agents formalized in
``prompts/build.md`` "The multi-agent pipeline (A2)".

Routing lives HERE, not on the check modules: per
``scripts/checks/__init__.py``, "the [dispatch] lists are the routing
source of truth" — phase is a routing/dispatch concern owned by the
orchestrator layer, so one reviewable map beats a constant scattered
across 67 modules.

Discipline:
  - ``preflight`` checks (parse / structure / version) run in EVERY
    phase — they gate everything downstream.
  - A check absent from the map defaults to ``builder`` (the final
    full pass), so a newly added check is always exercised by an
    unflagged run and is never silently dropped.
  - An unflagged run (``--phase`` not given) runs every check
    regardless — the global consistency pass. ``--phase`` only ever
    NARROWS a run; it never changes the full pass.
"""

PHASES = ("scout", "marker", "manager", "meta-linker", "builder")

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

    # scout — source archival (manifest + primary_sources)
    "manifest_parse": "scout",
    "manifest_value_enums": "scout",
    "manifest_archive_status": "scout",
    "manifest_checksums": "scout",
    "manifest_checksum_at_extraction": "scout",
    "manifest_extraction_type": "scout",
    "manifest_artifact_shape": "scout",
    "primary_sources": "scout",
    "doc_form_archival_status": "scout",

    # marker — verbatim quote extraction
    "quotes": "marker",
    "verbatim_quotes": "marker",
    "speakers": "marker",
    "speaker_baseline_consistency": "marker",

    # manager — free-prose synthesis (incl. A3 quote organization)
    "prose_drift": "manager",
    "top_scope_activity": "manager",
    "corroboration_items": "manager",
    "vouching_chain": "manager",
    "hypotheses": "manager",
    "open_questions": "manager",
    "establishes": "manager",
    "does_not_establish": "manager",

    # meta-linker — cross-reference surfaces + structured entries
    "timeline": "meta-linker",
    "chronological_tables": "meta-linker",
    "affiliations": "meta-linker",
    "relationships": "meta-linker",
    "program_involvement": "meta-linker",
    "publication_record": "meta-linker",
    "participants": "meta-linker",
    "witnesses_testimony": "meta-linker",
    "key_personnel": "meta-linker",
    "org_relationships": "meta-linker",
    "contracts": "meta-linker",
    "ownership_timeline": "meta-linker",
    "location_relationships": "meta-linker",
    "media_versioning": "meta-linker",
    "naming_quirks": "meta-linker",
    "rumors": "meta-linker",
    "cross_refs": "meta-linker",
    "cited_findings": "meta-linker",
    "contradictions": "meta-linker",
    "closure_path": "meta-linker",
    "resolution_history": "meta-linker",
    "iff_section": "meta-linker",
    "finding_no_investigation_refs": "meta-linker",
    "finding_source_in_entity_node": "meta-linker",
    "entity_no_finding_or_investigation_refs": "meta-linker",
    "investigation_hypothesis_citation": "meta-linker",
    "investigation_closure_path_when_paused": "meta-linker",

    # builder — render-time structure + cross-layer (also the default)
    "status_archetype_kind": "builder",
    "conditionally_required": "builder",
    "required_sections": "builder",
    "section_rules": "builder",
    "link_resolution": "builder",
    "table_cell_word_budget": "builder",
    "coverage": "builder",
    "boundary": "builder",
    "description_token_drift": "builder",
    "phase_iii_inputs": "builder",
    "governance_files": "builder",
}


def phase_of(check_name):
    """Phase a check belongs to. Unlisted checks default to ``builder``
    so the full pass always exercises them."""
    return CHECK_PHASE.get(check_name, "builder")


def in_scope(check_name, requested_phase):
    """Whether a check should run for the requested ``--phase``.

    ``requested_phase`` None → full pass (everything runs). Otherwise a
    check runs iff it is a ``preflight`` check (always) or its phase
    equals the requested phase.
    """
    if requested_phase is None:
        return True
    p = phase_of(check_name)
    return p == "preflight" or p == requested_phase
