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

**Direction (re-scoped 2026-05-19 after A1.1).** Retire mandatory
registration; redundant entries delete directly. The
vocab-preservation migration originally approved (preserve entity
names into `naming_quirks` before deletion) was **retired** — the
A1.1 audit verified end-to-end against the live gate that deleting
every `entities_referenced[]` entry corpus-wide adds **zero** new
`description_token_drift` errors (ACTIVE gate risk = 0). The
karl-nell "300–400 tokens lost" projection measured vocab-pool
shrinkage, not gate failures; the gate fires only on
`## Description` + `source_text` nodes, and no live Description
token grounds solely on an entity name. See the A1.1 landed-note
below for the full reasoning.

**Deletion count is a contributor-review dial, not a fixed number.**
The BACKLOG's "~173 preserve / ~1,081 delete" projection does not
match the audit: at substantive-threshold ≥1 token the split is
885 preserve / 369 delete. The threshold (how much unique
`context_summary` synthesis an entry must carry to be kept) is a
judgment A1.4 must settle with contributor review — `audit-a1-vocab.py
--substantive-threshold N` is the dial.

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

  **Landed.** `scripts/build/audit-a1-vocab.py` shipped (run
  `--all`; reports to `/tmp/a1-vocab-audit/`). Headline finding —
  **ACTIVE `description_token_drift` risk = 0.** Deleting every
  `entities_referenced[]` entry corpus-wide adds zero new gate errors,
  verified end-to-end against the live gate (pre-migration baseline:
  `review-coverage.py --all` = 0 errors). The gate grounds on entity
  names ONLY where a node renders `## Description` AND has extractable
  `source_text`: the 26 person artifacts render no Description; the 31
  other Description-bearing artifacts ground their Description
  proper-nouns in their own source text (0 name-grounded tokens); and
  the sole artifact whose names ground Description tokens
  (`lockheed-martin-uap-materials` investigation — 13 names) has empty
  `source_text`, so the gate `check()` early-returns and skips it
  (LATENT, not active). Conservative whole-corpus name-unique = 117
  (vs. the 300–400 projection). **Consequence: the vocab-preservation
  premise behind A1.2 is contradicted — A1.4 deletion is gate-safe
  without a preservation pass. Re-scope A1.2/A1.4 (A1.2 likely a no-op
  or fold into A1.4) before proceeding.** Latent caveat: if a source is
  ever added to the investigation, its Description already carries ~34
  other ungrounded tokens, so preserving the 13 names would not make it
  gate-clean regardless.

- **A1.2 — Vocab preservation.** **RETIRED 2026-05-19 after A1.1.**
  Premise contradicted: A1.1 verified ACTIVE `description_token_drift`
  risk = 0, so no `naming_quirks` preservation pass is needed before
  deletion. No `migrate-a1-vocab.py` will be written. The bucket-(c)
  "delete-migrate" worklist the audit produces is confirmed empty
  corpus-wide. (One LATENT case — 13 entity names in the
  `lockheed-martin-uap-materials` investigation — is moot: the gate
  is skipped there for empty `source_text`, and 49 other Description
  tokens are ungrounded anyway, so preserving the names wouldn't make
  the node gate-clean even if a source were later added. Left alone;
  it's a pre-existing investigation-node grounding gap, not an A1
  concern.)

- **A1.3 — Schema relax.** Update
  `meta/schema-research-artifact.yaml`: move `entities_referenced`
  from required-keys to optional. No corpus changes. Validator must
  pass (existing artifacts still populate the field; the relax is
  permissive). **Rollback:** revert the schema file.

- **A1.4 — Corpus deletion.** Write
  `scripts/build/migrate-a1-delete.py`: consumes the A1.1 audit
  (`audit-a1-vocab.py`) and deletes the redundant (delete-no-risk)
  entries from each artifact at the contributor-chosen substantive
  threshold. Preserves auto-populated `references[]` pointers on
  retained entries. Settle the threshold first (see Direction —
  885/369 at ≥1; review the per-artifact reports before committing
  to a count). Validator must pass; `description_token_drift` must
  report zero new failures — A1.1 already verified this holds for
  full deletion, so it's a regression guard, not a question.
  **Rollback:** `git restore meta/research/`.

- **A1.5 — Convention rewrite.** Update `meta/conventions.md`
  "Cross-reference contract for interview-derived testimony"
  section (lines 1241–1272): body wraps remain mandatory (the
  broken-link registry depends on them); registration becomes
  optional, used only when attaching a non-trivial
  `context_summary`. Retire the BACKLOG A1 entry in the same
  commit. **Rollback:** revert the file.

- **A1.6 — Verification.** Confirm `stub_linking.py` scope correctly
  shrunk to the retained entries; confirm `coverage-suggest.py`
  output is noisier but still actionable; confirm
  `link_resolution.py` and the broken-link registry unchanged.
  No code changes expected; logs the post-migration baseline for
  future audits. **Rollback:** not applicable (no changes).

**Cross-references:**
- Blocks: none.
- Touches: `meta/schema-research-artifact.yaml`, `meta/conventions.md`,
  research artifacts (deletion count = contributor-chosen threshold;
  369 at ≥1 token), **no** `naming_quirks` additions (A1.2 retired),
  no renderers (entities_referenced is artifact-only).
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
