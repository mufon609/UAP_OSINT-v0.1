# Archive sweep prompt

Paste into a Claude Code session to run an archival pass across the
repository — verify every cited URL is archived locally, submit missing
entries to the Wayback Machine, and report integrity issues.

---

Steps:

1. **Health check** the manifest integrity:
   ```
   python3 scripts/manifest.py verify-paths
   python3 scripts/manifest.py summary
   ```
   If `verify-paths` reports missing files, report to the user and stop
   before submitting anything — missing local copies must be fixed
   first.

2. **Detect orphans and missing entries:**
   ```
   python3 scripts/manifest.py missing     # URLs in nodes not in manifest
   python3 scripts/manifest.py orphans     # manifest entries no node cites
   ```
   - For `missing`: add each to the manifest:
     ```
     python3 scripts/manifest.py add URL --path PATH
     ```
     (download the source first if not already present; see
     `meta/sources-access.md` for site-specific workarounds)
   - For `orphans`: verify whether the citing node was removed and
     adjust. Do not auto-delete orphans — surface to user.

3. **Submit pending Wayback entries:**
   ```
   python3 scripts/archive.py
   ```
   This rate-limits per IA guidelines. Leave it running; report
   progress periodically.

4. **Report:**
   - Total manifest entries
   - Newly added (missing → archived)
   - Newly submitted to Wayback
   - Submission failures (and why — 403, 402, 523, etc.)
   - Any orphans that need user decision
   - Any `verify-paths` failures that need attention

5. If submissions failed for known-blocked sites, update
   `meta/sources-access.md` if a new workaround was discovered this
   pass.

**Rules:**
- Do not run `archive.py --recheck-all` unless the user explicitly asks
  — it re-queries every entry and blows through rate limits
- Do not remove manifest entries without user approval
- Do not modify source files on disk during this pass

**Cadence:** run at the end of any node-building session that added new
sources. Also run as a stand-alone health check monthly.
