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

### C38 — Drop `entities_referenced[]`; relocate load-bearing context_summaries  ✅ SHIPPED 2026-05-20

Follow-on to A1: resolved the residual 655 optional, unrendered,
unconsumed entries. C38.1's triage found the relocatable set ≈ 0 (the
synthesis paraphrased facts the verbatim record already carries), so
the relocation phase collapsed and the field was dropped outright.
Full phase history in git log:

- **C38.1** — triage: 442/655 had no rendered home; the 213 with one
  were redundant paraphrases → relocation unwarranted.
- **C38.2** — RETIRED (collapsed): no paraphrase-relocation needed.
- **C38.3** — `entities_referenced` dropped from all 51 artifacts (655
  entries); deletion-only; broken-link registry unchanged (510).
- **C38.4** — machinery retired: deleted the `entities_referenced` +
  `stub_linking` checks + 4 spent migration scripts; dropped the
  name-grounding from `description_token_drift`; swept schema,
  conventions, build.md, tools, prompts, and all doc refs (-1,511 lines).
- **C38.5** — verified (gates green, registry unchanged at 510, zero
  references in code/corpus); BACKLOG C38 retired.

End state: cross-references are carried solely by `[`/path`]` body
wraps (broken-link registry + Associated Nodes); no contributor-prose
entity layer remains.

### C37 — Uniform error-level grounding gate for synthesis prose  ✅ SHIPPED 2026-05-20

Resolved the prose-drift severity asymmetry C37 flagged: person
synthesis prose (`background` / `top_relevance` / `credibility_notes`)
was checked only at WARN level, while document `## Description` prose
got `description_token_drift` at ERROR level — same grounding-drift
class, different severity by node type. Collapsed it to a single
severity — **Error** — per ungrounded token, uniform across all types:

- `prose_drift` flipped from warn-then-error-at-100% to **error per
  unmatched token** (`scripts/checks/prose_drift.py`); covers every
  scoped synthesis field on all eight content types.
- `description_token_drift` kept as a separate algorithm at the same
  severity — the two are deliberately distinct (all-content-words vs.
  proper-noun / designator / number extraction), per the docstring's
  no-merge caution.
- `meta/conventions.md` rewritten to match ("Prose-drift discipline" +
  "Validator design — impartial reporting"): a hard per-token error
  gate, no warn tier, no documented-residual exemption.
  `prompts/build.md` + `prompts/audit.md` swept.

End state: an ungrounded token in synthesis prose is a commit-blocking
defect on every node type. The corpus was at 0 prose-drift warnings at
flip time, so the change shipped with 0 new errors. BACKLOG C37 retired.

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
