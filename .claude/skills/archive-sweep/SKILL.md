---
name: archive-sweep
description: Run an archival health pass — verify every cited URL is archived locally, recover dead URLs from Wayback, and submit missing entries to the Wayback Machine. Use at the end of a session that added sources, or as a periodic standalone health check.
allowed-tools: Read, Bash(python3 scripts/tools/manifest.py *), Bash(python3 scripts/tools/archive.py *), Bash(curl *)
---

# Archive sweep

1. **Manifest integrity:** `manifest.py verify-paths` + `manifest.py summary`.
   If `verify-paths` reports missing files, report and STOP — missing local
   copies must be fixed before submitting anything.
2. **Orphans + missing:** `manifest.py missing` (cited URLs not in manifest) and
   `manifest.py orphans` (entries no node cites). For `missing`, download then
   `manifest.py add URL --path PATH` (see `meta/sources-access.md` for blocked
   sites). For `orphans`, surface to the user — do not auto-delete.
3. **Recover `status: pending` entries from Wayback** (live URL dead, snapshot
   exists): pull via the fuzzy-timestamp workflow in `meta/sources-access.md`
   ("Wayback Machine fetch — fuzzy-timestamp URLs bypass anti-bot challenge"),
   then promote the entry to `status: archived` with path. Don't call a pending
   entry unrecoverable before trying the fuzzy-timestamp pull.
4. **Submit unarchived entries to Wayback:** `python3 scripts/tools/archive.py`
   (rate-limited; leave running, report progress). Distinct from step 3 — this
   SUBMITS (insurance); step 3 PULLS a dead URL.
5. **Report:** total entries, newly added, newly submitted, submission failures
   (with code — 403/402/523), orphans needing a decision, `verify-paths`
   failures.
6. If a new workaround for a blocked site was found, update
   `meta/sources-access.md`.

**Rules:** do not run `archive.py --recheck-all` unless the user explicitly
asks (it re-queries every entry and blows through rate limits); do not remove
manifest entries without approval; do not modify source files on disk.
