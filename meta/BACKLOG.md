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

### B1 — Magic-number empty-state sentinel in three renderers

`scripts/build/renderers/event.py:107`, `transcript.py:96`, and
`media.py:103` each emit an empty placeholder row via
`if len(lines) == 4:` — coupled to the exact header-line count (the
`| Field | Value |` header + separator + first two rows). Any change
to header structure silently breaks the empty-state placeholder.
Replace with a positive "no rows emitted" flag tracked during row
construction.

Surfaced: 2026-05-17 repo audit (renderer dead-code + bandaid sweep).

### B2 — `person.py:182-202` Claim Inventory Status column is hardcoded

`render_claim_inventory` writes `✅ Sworn / documented` into every
Status cell regardless of artifact data. No quote field drives this,
so the column is decorative — either source from a per-quote field
(schema extension) or drop the column.

Surfaced: 2026-05-17 repo audit.

### B3 — `person.py:67-70` Identity Source column ships empty unconditionally

Renderer-side counterpart to the schema-gap analysis already tracked
in `meta/topic/research-queue.md` "Person Identity table — Source
column has no schema backing". When that decision lands (drop the
column / add per-field sources / single collective Source row), the
renderer-side change is the implementation half.

Surfaced: 2026-05-17 repo audit.

### B4 — `media.py:122-134` empty `## Media Versioning` row when artifact has none

When `derivation_of` is set but `media_versioning[]` is empty, the
renderer emits the required section with an empty-cell placeholder
row to satisfy the section-presence gate. The blank row reads as
missing data rather than "no versioning aspects documented." Either
emit a TODO-comment-only section, or auto-suppress and let
`conditionally_required` drive the presence check.

Surfaced: 2026-05-17 repo audit.

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

C1 retired 2026-05-17 — shipped as `scripts/tools/extract-firefox-cookies.py`;
ID held open per the gap-stable retirement rule.

### C3 — `scripts/tools/archive.py:99-102, 133` — Wayback submit records unconfirmed snapshots as archived

[BUG] `submit_wayback` returns `(True, "Submitted — check …")` when
the SPN response URL doesn't contain `web.archive.org`;
`cmd_submit_one` then calls `wayback_url_date(result)` (returns None
on the non-URL fallback string), falls through to
`datetime.now().strftime("%Y-%m-%d")`, and stamps the manifest with
`wayback_date = <today>` plus `archive_status |= 2`. The manifest
records "Wayback archived" for snapshots that may not exist. Either
treat the non-URL response as failure, or store a distinct
`pending-confirmation` state that a follow-up sweep can resolve.

Surfaced: 2026-05-17 repo audit.

### C5 — `scripts/checks/section_rules.py:88` — `requires_quote_attribution` check is all-or-nothing

[BUG] `if quotes > 0 and attributions == 0:` only fires when no
attribution rows exist. A section with 3 block-quotes and 1
attribution passes silently — the rule's intent is "each block-quote
is paired with an attribution," so the condition is missing a
`quotes > attributions` branch.

Surfaced: 2026-05-17 repo audit.

### C6 — `scripts/checks/{contradictions,investigation_hypothesis_citation}.py` — silent skip when target list is empty

[BUG] `contradictions.py:84` and
`investigation_hypothesis_citation.py:166, 245` use the pattern
`elif quote_ids and eid not in quote_ids:` (and analog for
`hypothesis_ids`). When the target list is empty, dangling-reference
validation is skipped silently — which is exactly the case the check
should catch (contributor forgot to populate the referenced
structure). Drop the truthiness guard or emit a distinct "cannot
resolve, target list empty" error.

Surfaced: 2026-05-17 repo audit.

### C7 — `scripts/build/renderers/transcript.py:88-91` — `derived_from` silently dropped for non-`/media/`, non-`/documents/` paths

[BUG] The `derived_from` row in the Publication Record table only
renders when the path starts with `/media/` or `/documents/`. Any
other valid node-path target disappears from rendered output with no
fallback row and no validator complaint. Either widen the prefix
match to all node-type roots, or emit a generic "Underlying Source"
row.

Surfaced: 2026-05-17 repo audit.

### C8 — `scripts/build/new.py:185-188` — raw `KeyError` on `--archival-status` for non-document types

[BUG] `type_spec["archival_status_values"]` raises an unhandled
`KeyError` when `--archival-status` is passed for any type whose spec
doesn't carry the key (everything except `document`). argparse
doesn't gate the flag by type. Either gate the flag's acceptance, or
controlled-`sys.exit` on the missing key.

Surfaced: 2026-05-17 repo audit.

### C9 — `scripts/checks/_research_utils.py:180` — empty-string path falls through validation

[BUG] `require_source_dict` checks `if src.get("path") and src["path"]
not in manifest_paths:`. A `path: ""` entry passes both the "path is
missing" branch above and the manifest-membership branch — silently
treated as valid. Fix the truthiness guard so empty strings hit the
"missing path" error path.

Surfaced: 2026-05-17 repo audit.

### C10 — `scripts/tools/transcribe.py:111-113` — hangs forever on interactive `--cookies -` misuse

[BUG] `sys.stdin.read()` blocks until EOF; the empty-stdin guard at
L113 fires only after the read returns. A contributor running
`transcribe.py URL --cookies -` interactively without piping hangs
with no prompt. Detect TTY on stdin and abort with a usage hint
before the blocking read.

Surfaced: 2026-05-17 repo audit.

### C11 — `scripts/lib/_common.py:660` — PDF line-wrap hyphen merge applied to all extracted text

[BUG] `re.sub(r"-\s+", "-", result)` unconditionally collapses
`"-<whitespace>"` sequences across the entire extracted-text path,
including HTML and plaintext. A legitimate plaintext
`"well-known phrase\nmore text"` collapses across the linebreak,
mismatching the source form for verbatim-quote checks against
non-PDF sources. Gate the substitution on the source format being a
PDF whose extraction shape is known to line-wrap.

Surfaced: 2026-05-17 repo audit.

### C12 — Silent `except` swallow at four parser/IO sites

[BANDAID] `scripts/build/validate.py:287-288`,
`scripts/build/validate-research.py:298-299`,
`scripts/build/research-scaffold.py:160-172`, and
`scripts/tools/normalize-locations.py:246` swallow YAML or IO errors
and rely on a downstream check (or contributor judgment) to
re-detect. Permission errors, encoding errors, and partial parses
silently become "empty" rather than surfacing. Audit each site:
either narrow the exception class to the documented expected mode,
or surface the error with context.

Surfaced: 2026-05-17 repo audit.

### C13 — `scripts/lib/_common.py` `save_manifest` is non-atomic — concurrent writers race

[BANDAID] `save_manifest` does a whole-file rewrite without flock or
temp+rename. Two concurrent `scripts/tools/manifest.py add`
invocations race; the second overwrites the first. Switch to
write-temp + atomic rename, or wrap in `fcntl.flock`. Low likelihood
in current single-contributor workflow, but the failure mode is
silent data loss.

Surfaced: 2026-05-17 repo audit.

### C14 — `BINARY_FORMATS` triplet hardcoded at three sites

[BANDAID] `("image", "video", "audio")` is repeated as a literal in
`scripts/build/extract-source.py:164`,
`scripts/checks/phase_iii_inputs.py:52`, and
`scripts/checks/verbatim_quotes.py:111`. Adding a new binary format
to the manifest schema requires updates in three places. Promote to
a shared constant in `scripts/lib/_common.py` and have all three
sites import it.

Surfaced: 2026-05-17 repo audit.

### C15 — `scripts/tools/archive.py:73` — retry has no backoff and no jitter

[BANDAID] Single retry on `URLError`/`TimeoutError` with a hardcoded
5-second sleep. Treats DNS failure, connection reset, and timeout
identically. Switch to a small exponential backoff with jitter, or
classify the error and retry only on transient categories.

Surfaced: 2026-05-17 repo audit.

### C16 — Gate `.sh` scripts use newline-unsafe `git ls-files` reads

[BANDAID] `scripts/tests/cookies-check.sh:43` and
`scripts/tests/file-size-check.sh:31` both iterate via
`while IFS= read -r path; do … done < <(git ls-files)` — filenames
containing newlines split across iterations. Switch to
`git ls-files -z | while IFS= read -r -d '' path` for null-delimited
safety. Repo policy makes the failure mode unlikely, but the gate
should not rely on policy.

Surfaced: 2026-05-17 repo audit.
