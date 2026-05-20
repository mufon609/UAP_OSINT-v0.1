---
id: meta/roadmap
type: meta
schema_version: 1
created: 2026-04-17
---

# Roadmap

Active work on the toolkit. Git log + the code itself is the
authoritative record of what shipped.

---

## Active work

### Step G — Content population  🟡 IN PROGRESS

Ongoing entity-node builds driven by the priority queue. Cluster
status, build candidates, and per-node rationale live in
`meta/topic/research-queue.md` (canonical); the auto-generated
build-state block in `CLAUDE.md` is the authoritative count of what
shipped.

### C35 — Retire page-anchored quote locations (Full Retire)  ⏳ PENDING

Promoted from `meta/BACKLOG.md` C35 on 2026-05-19. Full analysis,
corpus census (507 page-anchored locations, 388 confirmed via census
walker), candidate comparison, and reader-experience evaluation live
in the BACKLOG entry — do not duplicate that work here. This roadmap
block is the **execution plan**.

**Direction (approved 2026-05-19):** Full Retire. Drop `p. N` /
`p. N, ¶M` / `pp. N-M` forms entirely for paginated text sources.
`source.location` becomes optional. Timestamps (`[MM:SS]`), Doc-N
markers, content-pointers, and spatial anchors all survive (they
are content-anchored, not page-anchored). Retires
`scripts/tools/normalize-locations.py` as dead code on completion.

**Phase ordering (each phase = one fresh session, validator clean at
every boundary):**

- **C35.1 — Governance.** Update `meta/conventions.md` "Quote location
  refs" section: remove page-anchored canonical forms for paginated
  text; keep timestamp / Doc-N / content-pointer / paragraph-anchored
  forms. Update `meta/schema-research-artifact.yaml` —
  `quote_source.location` field becomes optional. No corpus changes
  yet. Validator must pass (existing entries' page-anchored forms
  remain valid — schema relax is permissive, not breaking).
  **Rollback:** revert the two files.

- **C35.2 — Migration script (dry-run).** Write
  `scripts/build/migrate-c35.py`: walks all `meta/research/*.yaml`
  quotes, classifies each page-anchored `source.location` into one
  of three buckets — `bare-p-N` (drop location), `p-N-¶M` (keep
  `¶M`), `p-N-content-pointer` (strip `p. N,` prefix). Emits a
  per-artifact proposed-diff report to `/tmp/c35-migration-plan/`.
  **Does not write to corpus.** Contributor reviews the diff plan
  artifact-by-artifact before C35.3. **Rollback:** delete the script.

- **C35.3 — Corpus migration.** Run the migration script with
  `--apply`. Validator must pass on the migrated corpus. Spot-check
  10 random affected quotes against their source files to confirm
  verbatim-quote check still resolves. **Rollback:** `git restore
  meta/research/`.

- **C35.4 — Renderer update.** Update
  `scripts/build/renderers/document.py:109`,
  `scripts/build/renderers/finding.py:104`, and
  `scripts/build/renderers/_common.py:266`: emit Location row only
  when `loc` is non-empty. Rebuild all affected node types
  (document / finding / person / event / transcript). Validator
  must pass. **Rollback:** revert renderers + rebuild.

- **C35.5 — Retire `normalize-locations.py`.** Delete the tool.
  Run `bash scripts/tests/help-check.sh` to confirm no other scripts
  reference it. Update `REFACTOR/CLAUDE.md` core-scripts table
  (remove the row). Retire the BACKLOG C35 entry in the same commit
  per `meta/conventions.md` "BACKLOG lifecycle discipline."
  **Rollback:** restore the tool from git.

**Cross-references:**
- Blocks: C33 (BACKLOG) — page-footer normalization narrows once
  C35.3 lands; C33 should pick up after C35.5.
- Touches: `meta/conventions.md`, `meta/schema-research-artifact.yaml`,
  3 renderers, ~507 quote entries across 58 research artifacts,
  `scripts/tools/normalize-locations.py`, `REFACTOR/CLAUDE.md`.

### A1 — Retire mandatory `entities_referenced[]` registration  ⏳ PENDING

Promoted from `meta/BACKLOG.md` A1 on 2026-05-19. Full analysis,
corpus measurement (1,254 entries / 58 artifacts; ~16% substantive),
and per-consumer dependency walk live in the BACKLOG entry and the
2026-05-19 investigation report. This roadmap block is the
**execution plan**.

**Direction (approved 2026-05-19):** retire mandatory registration
with **vocab-preservation migration**. The naive "delete first"
path silently breaks `description_token_drift.py` on artifacts
where trivial entries carry unique entity names not present in body
prose or `naming_quirks[]` (sample: karl-nell loses 32 entity-name
tokens; corpus-wide estimate 300–400). The migration must preserve
those names in `naming_quirks` **before** any deletion.

**Phase ordering (each phase = one fresh session, validator clean at
every boundary):**

- **A1.1 — Vocab-audit script.** Write
  `scripts/build/audit-a1-vocab.py`: for each
  `meta/research/*.yaml`, classify each `entities_referenced[]`
  entry as "substantive" (non-trivial `context_summary` carrying
  synthesis not in body) vs. "redundant" (pure duplication). For
  each redundant entry, determine whether its `name` token is
  unique-to-that-entry (not covered by body prose tokens or
  existing `naming_quirks`). Emit per-artifact reports to
  `/tmp/a1-vocab-audit/` listing (a) entries to preserve, (b)
  entries to delete with no vocab risk, (c) entries to delete after
  migrating their `name` into `naming_quirks` first. Read-only;
  no corpus changes. **Rollback:** delete the script.

- **A1.2 — Vocab preservation.** Write
  `scripts/build/migrate-a1-vocab.py`: consumes the A1.1 report
  and adds `naming_quirks[]` entries for every unique-to-entry name
  in the "delete after vocab migration" bucket. Contributor reviews
  per-artifact diffs before applying. Validator must pass — the
  `description_token_drift` gate should now have equivalent
  vocabulary coverage as it does today, despite the entries not
  yet being deleted. **Rollback:** `git restore meta/research/`.

- **A1.3 — Schema relax.** Update
  `meta/schema-research-artifact.yaml`: move `entities_referenced`
  from required-keys to optional. No corpus changes. Validator must
  pass (existing artifacts still populate the field; the relax is
  permissive). **Rollback:** revert the schema file.

- **A1.4 — Corpus deletion.** Write
  `scripts/build/migrate-a1-delete.py`: consumes the A1.1 report
  and deletes redundant entries from each artifact. Preserves
  auto-populated `references[]` pointers on retained entries.
  Validator must pass — critically, `description_token_drift`
  must report zero new failures (the A1.2 preservation is what
  makes this safe). **Rollback:** `git restore meta/research/`.

- **A1.5 — Convention rewrite.** Update `meta/conventions.md`
  "Cross-reference contract for interview-derived testimony"
  section (lines 1241–1272): body wraps remain mandatory (the
  broken-link registry depends on them); registration becomes
  optional, used only when attaching a non-trivial
  `context_summary`. Retire the BACKLOG A1 entry in the same
  commit. **Rollback:** revert the file.

- **A1.6 — Verification.** Confirm `stub_linking.py` scope correctly
  shrunk to the retained ~173 entries; confirm `coverage-suggest.py`
  output is noisier but still actionable; confirm
  `link_resolution.py` and the broken-link registry unchanged.
  No code changes expected; logs the post-migration baseline for
  future audits. **Rollback:** not applicable (no changes).

**Cross-references:**
- Blocks: none.
- Touches: `meta/schema-research-artifact.yaml`, `meta/conventions.md`,
  58 research artifacts (~1,081 entry deletions, ~300–400
  `naming_quirks` additions), no renderers (entities_referenced
  is artifact-only).
- Orthogonal to C35 — different files, different decisions; can
  proceed in parallel sessions.

### E.3 — Cross-node update propagation  ⏸ DEFERRED

Blocked on: multiple artifacts with overlapping evidentiary claims.
Can't build propagation tooling without a propagation case. Likely
after ~10 nodes through the full pipeline.

When it ships: bidirectional `corroborated_by` / `superseded_by` /
`contradicted_by` pointers resolving across artifacts; validator
coverage for broken cross-artifact refs.

---

## Conventions

- 🟡 = in progress
- ⏳ = pending (next-up)
- ⏸ = deferred (not next-up)
- ❌ = removed / rejected
