"""manifest-archive-status check — global BaseContext check.

``archive_status`` is a 2-bit presence indicator on every manifest entry:

  - bit 0 (value 1) = locally archived (status == archived AND path set)
  - bit 1 (value 2) = archived on the Internet Archive Wayback Machine
                      (wayback_date set)

Combined values 0..3 record presence in {none, local-only, wayback-only,
both}. Auto-maintained by ``manifest.py add`` (sets bit 0 on local
archival) and ``archive.py`` (sets bit 1 on Wayback find or successful
SPN submit). This check enforces the declared bits match the rest of
each entry's state — drift between the composite indicator and the
underlying facts (status / path / wayback_date) fails loudly.

Catches manual edits or bugs that would leave the indicator stale.
Also catches contradictory ``wayback_skip: true`` + ``wayback_date``
combinations (a URL is either skippable from Wayback OR has a
snapshot, not both).

Consumes ``BaseContext.manifest_entries`` — the orchestrator loads
``sources/manifest.yaml`` once per invocation and shares it across
the three manifest checks (manifest_checksums, manifest_archive_status,
manifest_extraction_type) so the file isn't re-parsed per check.

Origin: commit ``7a01d8b`` introduced the ``archive_status`` field and
this integrity check together (Phase 1 of a 2-bit-indicator landing
that lets ``archive.py`` skip URLs already confirmed in Wayback rather
than re-checking the entire manifest every run). The check was
defensive from day one — created *with* the optimization, not in
reaction to a bug — to guarantee the composite indicator never
silently lies when underlying state drifts. The concrete adjacent
failure class is BACKLOG #30 (commit ``d6732e1``): at the time of
7a01d8b, ``archive.py`` was fire-and-forget — not updating the
manifest on successful Wayback submit, so bit 1 would have stayed 0
even after a snapshot existed. The #30 fix made ``archive.py`` update
the manifest; if that regressed, this check catches it. The migration
to per-module shape happened later (commit ``1c34081``, BACKLOG C14
session 2) without behavior changes; C18 confirmed byte-identity.
"""

from checks import Issue


CHECK_NAME = "manifest_archive_status"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield error-level Issue for any entry whose archive_status is
    missing, out-of-range, inconsistent with status / path / wayback_date,
    or contradicted by wayback_skip + wayback_date both being set."""
    # Schema-driven enum: ``archive_status_values`` declared on
    # ``manifest_entry`` per schema.yaml. Direct subscript per the C21
    # no-silent-fallbacks principle.
    valid_archive_status = ctx.schema["manifest_entry"]["archive_status_values"]

    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url", "(no url)")

        arch = entry.get("archive_status")
        if arch is None:
            yield Issue(
                MANIFEST_REL, "error",
                f"archive_status missing on entry (URL: {url}) — "
                f"required field per schema.yaml manifest_entry.required",
                check_name=CHECK_NAME,
            )
            continue
        if arch not in valid_archive_status:
            yield Issue(
                MANIFEST_REL, "error",
                f"archive_status must be one of {list(valid_archive_status)}; "
                f"got {arch!r} (URL: {url})",
                check_name=CHECK_NAME,
            )
            continue

        locally_archived = entry.get("status") == "archived" and bool(entry.get("path"))
        wayback_archived = bool(entry.get("wayback_date"))
        expected = (1 if locally_archived else 0) | (2 if wayback_archived else 0)

        if arch != expected:
            mismatches = []
            if (arch & 1) != (expected & 1):
                if expected & 1:
                    mismatches.append(
                        "bit 0 should be SET (status == archived AND path is set) "
                        "but archive_status indicates not-locally-archived"
                    )
                else:
                    mismatches.append(
                        "bit 0 is SET but the entry is not locally archived "
                        "(status != archived OR path missing)"
                    )
            if (arch & 2) != (expected & 2):
                if expected & 2:
                    mismatches.append(
                        "bit 1 should be SET (wayback_date is set) but "
                        "archive_status indicates not-in-Wayback"
                    )
                else:
                    mismatches.append(
                        "bit 1 is SET but wayback_date is not set"
                    )
            yield Issue(
                MANIFEST_REL, "error",
                f"archive_status={arch} inconsistent (URL: {url}) — "
                f"expected {expected}. " + "; ".join(mismatches),
                check_name=CHECK_NAME,
            )

        if entry.get("wayback_skip") and entry.get("wayback_date"):
            yield Issue(
                MANIFEST_REL, "error",
                f"entry has both wayback_skip: true and wayback_date set "
                f"(URL: {url}) — these are contradictory. Either the URL "
                f"is skippable (wayback_skip) or it has a Wayback snapshot "
                f"(wayback_date); not both.",
                check_name=CHECK_NAME,
            )
