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

**Field disposition — curated optional, attractors de-tuned (decided
2026-05-19 after content/clutter analysis).** A content analysis of the
1,254 entries found ~48% (599 entries with ≤1 `context_summary` token
absent from the rendered body) is clutter — empty stubs or
restatements of body content — while ~37% (464 at ≥3 tokens) carry
genuine but reader-invisible context (`context_summary` never renders).
The clutter is the predictable output of mandatory registration plus
five pipeline attractors that drive "register one entry per entity":
the `prompts/build.md` Step 7 / agent-task T3 stage, the
`research-scaffold.py` seed + build-step hint, the
`coverage-suggest.py` nudge, the `meta/conventions.md` "Cross-reference
contract" mandate, and the audit prompts. **Decision: keep
`entities_referenced` as a CURATED OPTIONAL synthesis surface** (entries
carrying substantive `context_summary` only) — delete the redundant
clutter (A1.4) and de-tune all five attractors (A1.5) so the field
stops re-accreting — **rather than dropping the field entirely.** Full
drop was scoped (≈15 code/doc touchpoints + relocating-or-losing the
~37% reader-invisible synthesis, which has no clean rendered home) and
set aside as the heavier, partly-irreversible alternative; it can be
revisited after A1.4 reveals the concrete residual. Making the field
merely schema-optional without de-tuning the attractors would be a
half-measure — the pipeline would keep generating clutter — which is
why A1.5 now covers all five attractors, not only the convention.

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
  ever added to the investigation, its Description already carries 49
  other ungrounded tokens (the 13 names ground 29 tokens; 49 more are
  ungrounded regardless), so preserving the names would not make it
  gate-clean.

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

- **A1.3 — Schema + check relax.** Make `entities_referenced`
  optional. The real enforcement is
  `scripts/checks/artifact_top_level.py::REQUIRED_TOP_LEVEL_KEYS`
  (a hardcoded list; the schema's `required_keys` is spec-only and
  not mechanically read) — remove the field from BOTH. The field
  stays valid when present (no unknown-key rejection); the per-entry
  `entities_referenced` check and the `entity_entry` shape are
  unchanged, so populated entries still validate. No corpus changes.
  Validator must pass (every artifact still populates the field; the
  relax is permissive). **Rollback:** revert the two files.

  **Landed.** `entities_referenced` removed from
  `artifact_top_level.py::REQUIRED_TOP_LEVEL_KEYS` (the real
  enforcement) and from the schema `required_keys` spec; both now
  document it as an optional, curated synthesis surface. Permissive
  relax verified: the full corpus (field present everywhere) passes
  `validate.py` + `validate-research.py` (3 pre-existing prose-drift
  warnings, unchanged); an in-memory spot-check on `david-fravor` with
  the field removed introduces 0 errors (no missing-key error). No
  corpus changes. Behavioral de-clutter (delete redundant entries +
  de-tune the five attractors) is A1.4 / A1.5.

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

- **A1.5 — De-tune population attractors + convention rewrite.**
  Re-tune every pipeline surface that drives "register one entry
  per entity" so the now-optional, clutter-pruned field stops
  re-accreting:
  (1) `meta/conventions.md` "Cross-reference contract for
  interview-derived testimony" — body wraps remain mandatory (the
  broken-link registry depends on them); registration becomes
  optional, only for entries carrying substantive `context_summary`;
  (2) `prompts/build.md` Step 7 / agent task T3 — reframe from
  "enumerate every referenced entity" to "register only
  substantive-synthesis entries";
  (3) `scripts/build/research-scaffold.py` build-step hint;
  (4) `scripts/tools/coverage-suggest.py` nudge;
  (5) `prompts/audit.md` + `prompts/quote-relevance-audit.md`
  registration reminders.
  Retire the BACKLOG A1 entry in the same commit. **Rollback:**
  revert the files.

- **A1.6 — Verification.** Confirm `stub_linking.py` scope correctly
  shrunk to the retained entries; confirm `coverage-suggest.py`
  output is noisier but still actionable; confirm
  `link_resolution.py` and the broken-link registry unchanged.
  No code changes expected; logs the post-migration baseline for
  future audits. **Rollback:** not applicable (no changes).

**Cross-references:**
- Blocks: none.
- Touches: `meta/schema-research-artifact.yaml`,
  `scripts/checks/artifact_top_level.py`, `meta/conventions.md`,
  `prompts/build.md`, `prompts/audit.md`,
  `prompts/quote-relevance-audit.md`,
  `scripts/build/research-scaffold.py`,
  `scripts/tools/coverage-suggest.py`, research artifacts (deletion
  count = contributor-chosen threshold; 369 at ≥1 token), **no**
  `naming_quirks` additions (A1.2 retired), no renderers
  (entities_referenced is artifact-only).
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
