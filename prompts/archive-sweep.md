# Archive sweep prompt

Paste into a Claude Code session to run an archival pass across the
repository — verify every cited URL is archived locally, submit missing
entries to the Wayback Machine, and report integrity issues.

---

Steps:

1. **Health check** the manifest integrity:
   ```
   python3 scripts/tools/manifest.py verify-paths
   python3 scripts/tools/manifest.py summary
   ```
   If `verify-paths` reports missing files, report to the user and stop
   before submitting anything — missing local copies must be fixed
   first.

2. **Detect orphans and missing entries:**
   ```
   python3 scripts/tools/manifest.py missing     # URLs in nodes not in manifest
   python3 scripts/tools/manifest.py orphans     # manifest entries no node cites
   ```
   - For `missing`: add each to the manifest:
     ```
     python3 scripts/tools/manifest.py add URL --path PATH
     ```
     (download the source first if not already present; see
     `meta/sources-access.md` for site-specific workarounds)
   - For `orphans`: verify whether the citing node was removed and
     adjust. Do not auto-delete orphans — surface to user.

3. **Recover `status: pending` entries from Wayback:**
   Entries with `status: pending` plus `wayback_date` set indicate
   the original URL is unreachable (typically HTTP 404) but the
   Internet Archive Wayback Machine retains a snapshot. Pull each
   via the fuzzy-timestamp workflow documented in
   `meta/sources-access.md` "Wayback Machine fetch — fuzzy-timestamp
   URLs bypass anti-bot challenge":
   ```
   curl -sSL --compressed -A "Mozilla/5.0 Firefox/120.0" \
        -o sources/news/{slug}-wayback-{YYYYMMDD}.html \
        "https://web.archive.org/web/{year}/{original_url}"
   ```
   Then promote the manifest entry to `status: archived` with path +
   sha256 + `archive_status: 3` (both local and Wayback). Don't skip
   pending entries as "unrecoverable" before trying the
   fuzzy-timestamp pull — exact-timestamp URLs trigger an anti-bot
   challenge that fuzzy-timestamp URLs bypass.

4. **Submit pending Wayback entries (entries not yet on Wayback):**
   ```
   python3 scripts/tools/archive.py
   ```
   This rate-limits per IA guidelines. Leave it running; report
   progress periodically. Distinct from step 3 — `archive.py` SUBMITS
   URLs to Wayback (insurance for the local archive); step 3 PULLS
   from Wayback when the live URL is dead.

5. **Report:**
   - Total manifest entries
   - Newly added (missing → archived)
   - Newly submitted to Wayback
   - Submission failures (and why — 403, 402, 523, etc.)
   - Any orphans that need user decision
   - Any `verify-paths` failures that need attention

6. If submissions failed for known-blocked sites, update
   `meta/sources-access.md` if a new workaround was discovered this
   pass.

**Rules:**
- Do not run `archive.py --recheck-all` unless the user explicitly asks
  — it re-queries every entry and blows through rate limits
- Do not remove manifest entries without user approval
- Do not modify source files on disk during this pass

**Cadence:** run at the end of any node-building session that added new
sources. Also run as a stand-alone health check monthly.
