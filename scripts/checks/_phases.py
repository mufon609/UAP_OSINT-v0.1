"""Per-phase validator dispatch.

Maps each check (by ``CHECK_NAME``) to the build-pipeline phase whose
output it validates, so an agent can run a phase-scoped pass
(``--phase {archive|extract|organize|link|render}``) for fast feedback
on what it just produced, rather than the full check sweep. A phase
token is named after the role whose output it validates — see the agent
topology in ``prompts/topology.md``. (One-line phase descriptions are not
restated here; they live in ``PHASE_DESC`` below, surfaced via
``--list-phases``.) The phase -> owning role:

  archive   role 3 Archive
  extract   role 4 Worker
  organize  role 5 Build, organize
  link      role 5 Build, link
  render    role 5 Build, render

Role 6 Audit runs the full unflagged pass. Roles 0/1/2 (Orchestrator,
Internal/External Investigator) produce no gated artifact state, so they
have no phase bucket here — their feedback is preflight + manifest tools.

Routing lives HERE, not on the check modules: per
``scripts/checks/__init__.py``, "the [dispatch] lists are the routing
source of truth" — phase is a routing/dispatch concern owned by the
orchestrator layer, so one reviewable map beats a constant scattered
across the per-check modules.

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

# Everything the ``--phase`` flag accepts: the canonical names plus
# ``preflight`` (parse/structure-only — runs just the always-on checks,
# e.g. to confirm a freshly scaffolded artifact parses before any content
# exists). ``in_scope`` already routes ``preflight`` to the preflight
# checks alone.
PHASE_CHOICES = ("preflight",) + PHASES

# check CHECK_NAME -> phase whose output it validates.
CHECK_PHASE = {
    # preflight — parse / structural / version; run in every phase
    "frontmatter_parse": "preflight",
    "frontmatter_required": "preflight",
    "artifact_parse": "preflight",
    "artifact_top_level": "preflight",
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
    "pdf_page_count": "archive",  # declared pages vs the source PDF's physical count

    # extract (role 4) — verbatim quote extraction (the one quote boundary)
    "quotes": "extract",
    "verbatim_quotes": "extract",
    "quote_location_page": "extract",
    "location_format": "extract",  # roman / printed-folio location-ref guard
    "document_quote_source": "extract",
    "cited_works": "extract",
    "cited_works_uncaptured": "extract",
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
    # prose_drift lives here (not organize): it scans the per-entry
    # synthesis .attestation field on link-phase entries as well as the
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
    "cross_refs": "link",
    "cited_findings": "link",
    "contradictions": "link",
    "closure_path": "link",
    "resolution_history": "link",
    "finding_no_investigation_refs": "link",
    "finding_no_finding_refs": "link",
    "entity_no_finding_or_investigation_refs": "link",
    "investigation_no_investigation_refs": "link",
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
    "source_form_grounding": "render",
    "phase_iii_inputs": "render",
    "governance_files": "render",
    "chronological_tables": "render",        # reads the RENDERED node body
    "iff_section": "render",                 # needs the full section set present
    "finding_source_in_entity_node": "render",  # needs the global cross-artifact index
}

# One-line description of what each phase validates — the single
# human-readable source for them, surfaced via ``--list-phases`` and the
# build-protocol skill injection. Not restated in prose elsewhere: the
# docstring above and prompts/topology.md carry the phase tokens only.
PHASE_DESC = {
    "preflight": "parse / structure / version — always-on, runs in every phase",
    "archive": "manifest integrity + primary_sources + doc_form_archival_status",
    "extract": "verbatim quotes / speakers — the one quote boundary",
    "organize": "free-prose synthesis entry-shape",
    "link": "cross-reference surfaces + naming_quirks / prose_drift",
    "render": "render-time node structure + the cross-layer checks (coverage / boundary / description-drift)",
}

# phase -> the role that owns a fix when a check in that phase fails. The
# value is the subagent role name (``.claude/agents/{role}.md``) the
# orchestrator re-enters; ``route_failure`` reads this so the dissolved
# Error-agent routing stays derived from here, not restated. ``preflight``
# is owned by whichever role last wrote the artifact (no fixed owner).
# ``render`` failures are rebuilt by the builder, but a cross-layer
# (coverage / boundary) failure may signal an upstream gap — route_failure
# flags that. The auditor runs the full unflagged pass; it owns no single
# phase.
PHASE_ROLE = {
    "preflight": None,
    "archive": "archive",
    "extract": "worker",
    "organize": "builder",
    "link": "builder",
    "render": "builder",
}


def phase_of(check_name):
    """Phase a check belongs to. Unlisted checks default to ``render``
    so the full pass always exercises them."""
    return CHECK_PHASE.get(check_name, "render")


def role_of(check_name):
    """Subagent role that owns the fix for a failing ``check_name`` (via
    its phase). ``None`` for preflight (owned by the last writer). The
    fix target is always the artifact data, never the rendered node body."""
    return PHASE_ROLE.get(phase_of(check_name))


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


def _main(argv=None):
    """Read-only inspector for the phase routing map.

    Pure read-out of the constants above — no validation logic. Exists so
    the phase vocabulary has one queryable surface: the build-protocol
    skill injects ``--list-phases`` (so the contract every subagent reads
    is generated here, never transcribed), and ``route_failure`` /
    ``phase_routing_parity`` consume the same data.
    """
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="Inspect the build-phase routing map (read-only; the "
        "single source of truth for --phase scoping and check->phase->role "
        "routing). No side effects.",
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--list-phases", action="store_true",
        help="list the canonical phases (+ preflight) with owning role and description",
    )
    g.add_argument(
        "--check-phase", metavar="CHECK_NAME",
        help="print the phase (and owning role) for one check name",
    )
    g.add_argument(
        "--list-choices", action="store_true",
        help="list every value the --phase flag accepts (canonical + preflight)",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    if args.list_choices:
        if args.json:
            print(json.dumps(list(PHASE_CHOICES)))
        else:
            print(" ".join(PHASE_CHOICES))
        return 0

    if args.check_phase:
        phase = phase_of(args.check_phase)
        role = role_of(args.check_phase)
        if args.json:
            print(json.dumps({"check": args.check_phase, "phase": phase, "owning_role": role}))
        else:
            print(f"{args.check_phase}\t{phase}\t{role or '(last writer)'}")
        return 0

    # --list-phases
    ordered = ("preflight",) + PHASES
    if args.json:
        print(json.dumps([
            {"phase": p, "owning_role": PHASE_ROLE.get(p), "validates": PHASE_DESC.get(p)}
            for p in ordered
        ]))
    else:
        for p in ordered:
            role = PHASE_ROLE.get(p)
            owner = "always-on" if p == "preflight" else f"owned by: {role}"
            print(f"  {p:<9} {owner:<18} {PHASE_DESC.get(p, '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
