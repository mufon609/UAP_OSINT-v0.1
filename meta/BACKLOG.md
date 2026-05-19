---
id: meta/BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

Open items are partitioned into three sections by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
and **C — Anytime** (no upstream blockers). Item identifiers are
A1, A2, ..., B1, B2, ..., C1, C2, ... — within each section,
retired items leave a gap rather than shifting remaining IDs, so
git-log and commit-message references stay valid. The same
gap-stable policy in `meta/conventions.md` applies to validator
check names.

**Default focus: Section C.** C items have no upstream dependencies
and can be picked up and finished in a single pass. A and B items
carry ordering or coupling constraints — starting one without its
dependencies risks half-baked implementations and leaves the BACKLOG
cluttered with partial work. For ad-hoc sessions, prefer C work.
Reserve A and B for sessions explicitly scoped to those tracks.

Items waiting on an external event the repo can't drive (FOIA
resolution, registry access, third-party publication) and that are
**topic-specific** to the current investigation live in
`meta/topic/research-queue.md` "Externally blocked" — that's the fork-
boundary-correct home for them. If a genuinely toolkit-neutral
externally-blocked item ever surfaces (rare), reinstate the
"Externally blocked" heading at the bottom of this file.

---

## A. Priority sequence

Items with ordering or coupling constraints.

*No priority-sequence items currently open.*

---

## B. Parallel batch (renderer pass)

Items that touch the renderer and naturally batch into a single
polish pass — bundling reduces churn vs. shipping each as a
separate touch.

*No parallel-batch items currently open.*

---

## C. Anytime (no dependencies)

Items with no upstream blockers; safe to pick up at any point in
any session. Per the preamble, this is the default-focus tier:
C work doesn't risk half-baked implementations.

### C2 — Decide whether to retain `meta/toolkit-notes/issue-log.yaml`

After the 2026-05-17 audit (1,470 entries over 11 days; 23 distinct
checks; mostly repeated fires of the same issue across runs), the log
was purged. Open question: does the auto-appended log earn its keep,
or should the mechanism be removed entirely (delete
`append_issue_log()` in `scripts/lib/_common.py`, drop all the
orchestrator call sites, retire the file)?

Arguments for keeping:
- Time-series visibility into which checks fire most + on which nodes
- Greppable history for forensic audits ("when did this fail first?")
- Already wired; cost of removal is non-zero

Arguments for removing:
- No de-duplication across runs — every warning re-fires its log
  entry every time the validator runs, so the log balloons on any
  branch where warnings exist (the audit found one node with the
  same 3 warnings re-appended on every commit cycle)
- Audit value is realized once in a while at most; the per-commit
  carrying cost (append I/O on every issue) is paid every time
- The validators' own output is already the source of truth at the
  moment a contributor cares; the log is an after-the-fact mirror

Surfaced: 2026-05-17 corpus check-script audit. Decision deferred —
purged for now; revisit when the log accumulates ≥ a week of new
entries and the audit value can be re-evaluated against the carrying
cost.

### C4 — Move verbatim-quote check from rendered Markdown to research artifact

The verbatim-quote check (`scripts/checks/verbatim_quotes.py`, dispatched
per-node by `validate.py` via `_NODE_CHECKS`) parses the rendered node
body to locate quotes: a blockquote regex finds `> ...` blocks, then a
2500-character window scan finds the following `| Source | ... |` row,
then a markdown-link regex extracts `(../sources/{path})`, then the
quote is substring-checked against the extracted source text.

The check then has a defensive `continue` branch for any Source row that
doesn't match the `(../sources/...)` pattern — a "soft case" silent-skip
on malformed Source rows. Across the current corpus this branch never
fires (1205 rendered Source rows + 2256 artifact `quotes[].source.path`
values all canonical), but a hand-edited node body or a renderer
regression would slip through silently — exactly the silent-drift class
of failure the check exists to catch.

The structural fix: dispatch the check from the artifact layer, not the
rendered layer. The artifact's `quotes[]` carry `text` + `source.path`
as structured fields; substring-check `text` against the source extracted
at `source.path`. Concrete changes:

- New per-artifact check, `scripts/checks/verbatim_quotes_artifact.py`
  (or rename the existing module and re-purpose it), dispatched from
  `validate-research.py::_ARTIFACT_CHECKS`.
- Retire the per-node markdown-parsing implementation in
  `scripts/build/validate.py::_NODE_CHECKS`.
- Drop the markdown-link regex, the blockquote regex, and the 2500-char
  search window — all artifacts of parsing rendered output that the
  artifact-side check doesn't need.
- Update `validate.py`'s `__doc__` block + `meta/conventions.md`
  "Statements as the universal evidentiary primitive" / "Confirmation
  is a precondition for inclusion" to reflect that verification is
  artifact-side, with the rendered node faithful to the artifact by
  construction.

Side benefits:
- Faster (no per-node markdown regex pass).
- The 2500-char magic number disappears with the markdown-side check.
- Architecturally consistent with the rest of the validator chain:
  drift / coverage / prose-drift checks all already run against the
  artifact, not the rendered node.

Surfaced: 2026-05-19 design-element audit. The current per-node check
gets the corpus to 0 errors because everything is renderer-emitted, but
the architecture inverts the source-of-truth direction (verifies
generated output, not the structured source). Moving to artifact-side
is the principled fix.

C1 retired 2026-05-17 — shipped as `scripts/tools/extract-firefox-cookies.py`;
ID held open per the gap-stable retirement rule.

C3 retired 2026-05-19 — WEAPONIZED-038 video pipeline registered baselines
for corbell / lacatski / kelleher / knapp, closing all 17 direction-1
warnings; ID held open per the gap-stable retirement rule.

