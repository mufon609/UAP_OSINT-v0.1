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

### A1 — Retire mandatory `entities_referenced[]` registration  ✅ SHIPPED 2026-05-20

`entities_referenced[]` was a mandatory per-entity registry that
duplicated body `[`/path`]` wraps — 1,254 entries across 58 artifacts,
~half pure restatement of the rendered body. A1 made the field
optional, deleted the redundant entries, and de-tuned the pipeline so
it stops re-accreting. Full phase history is in git log:

- **A1.1** — gate-accurate audit: deleting every entry corpus-wide adds
  **0** new `description_token_drift` errors (active gate risk = 0).
- **A1.2** — RETIRED: the vocab-preservation premise was contradicted
  by A1.1 (no `naming_quirks` pass needed).
- **A1.3** — field made optional (removed from
  `artifact_top_level.py::REQUIRED_TOP_LEVEL_KEYS` + the schema spec).
- **A1.4** — 599 redundant entries deleted at the contributor-chosen
  ≥2 threshold; 655 kept (surgical removal; `references[]` preserved).
- **A1.5** — five population attractors de-tuned (conventions contract,
  build.md T3, scaffold seed/hint, coverage-suggest nudge,
  quote-relevance-audit); BACKLOG A1 retired.
- **A1.6** — verified: `stub_linking` scope 655/51; broken-link
  registry unchanged (510); `review-coverage.py` 0 errors.

**Residual open question → `meta/BACKLOG.md` C38.** The 655 kept entries
carry unrendered, currently-unconsumed `context_summary` synthesis in
an optional, inconsistently-populated field (51/58 artifacts). Its
permanent disposition — render / relocate / bless as agent metadata /
drop — is unresolved.

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
- ✅ = shipped (kept as a design-decision record; git log is the full history)
- ❌ = removed / rejected
