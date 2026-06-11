---
id: meta/BACKLOG
type: meta
---

# BACKLOG

Deferred work — real, concrete, and would be lost otherwise; not on the
active roadmap. An item leaves when promoted to a roadmap phase, addressed,
or superseded.

## How this file works

**This file is self-governing** — it is the root authority for how the
BACKLOG is written, identified, and closed. Nothing outside it governs it.

**Sections.** Open items are partitioned by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
**C — Anytime** (no upstream blockers). **Default focus is C:** no
dependencies, finishable in one pass. Reserve A and B for sessions scoped
to them — starting a constrained item out of order half-bakes it and
clutters the file. Cross-reference entries with `**Blocks:**` /
`**Blocked by:**` lines so the dependency graph stays inline.

**Identifiers** (A1, B1, C1…) are positional working labels, not stable
IDs. A new entry takes the lowest unused number in its section, so numbers
**recycle**; once a section — and ultimately the whole BACKLOG — is cleared,
numbering restarts from 1. Because an ID is transient, **never reference it
outside this file** — not in code, docs, prompts, commit messages, or
`git log` searches. Describe the work; the commit diff + message are the
record.

**Opening an entry.** Write it forward-looking and prescriptive: the work
and why it matters. No "Surfaced from", audit/session label, or commit hash
pinning when the need arose — that history lives in `git log`.

**Closing an entry.** The goal is to REMOVE items, not annotate them.
Delete the block in full — no retirement marker, no placeholder; the
shipping commit's diff + message is the canonical record. Then sweep any
code comments that cited the closed ID (delete them, or rewrite to describe
current behavior) — that sweep is part of closing, not follow-up.

**Externally-blocked items** waiting on an event the repo can't drive (FOIA
resolution, registry access, third-party publication) live, when
topic-specific, in `meta/topic/research-queue.md` "Externally blocked". If a
genuinely toolkit-neutral one ever surfaces (rare), reinstate an "Externally
blocked" heading at the foot of this file.

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Exercise the pipeline paths the first whole run didn't hit

The six-role pipeline (the `/build` skill + `.claude/agents/`) has been run *whole* on one
real node build — a user-directed, all-internal institutional-actor build:
Internal Investigator → Worker (×N) → Build → Audit, with handoff stubs
captured and friction tightened in place. The **External Investigator
(role 2) and Archive (role 3)** roles have since been exercised standalone on
an existing node — a source-recovery that re-pulled a dead JavaScript-shell
capture from a Wayback snapshot (External Investigator confirmed the snapshot
and captured verbatim spans; Archive re-pulled the file and refreshed the
manifest). Both behaved per contract. Paths still unverified end-to-end:

- **role 2 + role 3 integrated inside a full `/build`** with a genuine
  external-source gap — so far they have run standalone, not as the
  external-gap branch of a fresh orchestration.
- the **`foia` worker kind** — `caption` is now exercised (the all-internal
  `jre-2194-elizondo-2024` transcript build hit it end-to-end: internal-survey →
  caption worker → builder → audit). `pdf` + `html` + `caption` done; only `foia`
  remains, and no load-bearing *unarchived* FOIA source currently exists to build
  (every referenced FOIA doc is already archived) — wait for a genuine FOIA gap
  rather than manufacturing one.
- **error routing** (`route_failure.py`) — no validator failure has needed
  routing on a clean run (the caption build was clean; its audit findings were
  applied via builder re-entry, not a routed check failure; the dird-32 build
  repeated that shape — clean run, one recommend-only locator fix via builder
  re-entry). The dird-32 build did newly exercise the **OCR sibling gate (4b)
  inside a full `/build`** end-to-end (producers → consensus → verifiers →
  registration), so that path no longer needs a dedicated run.

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — Backfill the four sibling-less weaponized attribution siblings, then promote transcript_sibling_presence to error

Four transcript nodes carry hand-attributed `speaker_id` quotes on
auto-caption sources with no verified attribution sibling — built before
the sibling gate existed, so the one mechanical attribution check
(`speaker_attribution_consistency`) silently skips them:

- `transcripts/weaponized-038-lacatski-kelleher-2023`
- `transcripts/weaponized-096-lacatski-part1-2025`
- `transcripts/weaponized-097-lacatski-part2-2025`
- `transcripts/weaponized-114-lacatski-future-visions-2026`

For each: run `/prepare-transcript-sibling {slug}` (video download →
producer → structural validator → independent verifier → mandatory
active-speaker fold gate), then confirm each node's existing `speaker_id`
values against the verified sibling (`stamp-speaker-id.py` dry run) and
correct any divergence — hand-keyed attribution is exactly the divergence
hazard the sibling exists to remove.

When all four are verified, promote `scripts/checks/
transcript_sibling_presence.py` from `warn` to `error` (its documented
end state) and update its docstring's severity paragraph.

**Blocks:** none.
**Blocked by:** none.

### C2 — Investigate whether the Description "no-duplication" convention should relax

The maintainer wants `## Description` to read as a well-defined summary that may
surface select salient items also living in a structured section (a key
relationship, timeline event, contract, finding). The current convention pushes
the other way — the builder's date-grade discipline (`.claude/agents/builder.md`,
"Date grade + period fields") states *don't restate in prose a field-precise date
the table already carries* because *that duplication is a drift surface*. That
anti-drift rationale is load-bearing, so a relaxation could easily go bad; it is
deferred for investigation, not changed in place.

Avenues to weigh before any edit: (a) survey how built nodes actually use
Description today — is the overlap pressure real or rare?; (b) whether the
carve-out should stay field-precise-only (exact dates / dollar amounts / control
numbers single-sourced in their table; orientation-grade overlap allowed); (c)
whether the `description_token_drift` check needs any change (it checks grounding,
not overlap, so likely none). Produce a recommended wording, then edit the
convention and record the rationale.

**Blocks:** none.
**Blocked by:** none.

### C3 — Correct the Kress-footnote date (OCR misread "June 17" → "June 27, 1972")

A cold-context audit of `organizations/stanford-research-institute` rendered the
Kress source PDF **page image** (the source is `extraction_type: ocr-scan` with
**no verified `.txt` sibling** — the `pdftotext` layer is corrupt) and read the
footnote date unambiguously as **"June 27, 1972"**. The quote was extracted from
the corrupt text layer as "June '1:7," and carried as **"June 17"**, then
propagated. A zero-tolerance verbatim defect, deferred here per the maintainer
for a clean session (needs the OCR-sibling workflow, not a quick edit).

Source: `sources/government/cia-kress-parapsychology-in-intelligence-studies-intelligence-1977-declassified-1996.pdf`
(PDF page 7 / printed page 8, footnote 6).

Steps:
1. Produce + confirm the verified `.txt` sibling via `/prepare-ocr-sibling`
   (this source feeds multiple quotes, so the sibling is owed regardless).
2. Re-extract the footnote quote text — `stanford-research-institute` q36 and
   `kit-green` q1 — from the verified sibling / page image: `…June 27, 1972.`
3. Drop the now-pointless naming_quirks — SRI `nq14` and kit-green `nq1` (they
   "preserve" a garble that lived only in the discarded text layer, never on the
   page → correction-to-nothing).
4. Retarget every derived `1972-06-17` field in `kit-green` (q1 `statement_date`,
   `background`, `top_relevance`, timeline entry, affiliation `period_start`) to
   `1972-06-27`.
5. Rebuild both nodes; re-audit.

Also verify while there: `uaptf` q22 shares the exact location string that q18
carried ("UAPTF Charter, p.4, UAP Task Force Director responsibilities section");
q18 was corrected to p.7 this session after a page-image check, but q22 was left
unverified — confirm q22's page ref against the charter PDF (likely also p.7,
same section) and correct if needed.

**Blocks:** none.
**Blocked by:** none.

### C4 — Review: dedicated attribution-producer / attribution-verifier agents

`/prepare-transcript-sibling` dispatches its producer and independent verifier
as the harness built-in `Agent(general-purpose)`, with their contracts written
inline in the SKILL.md — while the parallel OCR pipeline carries dedicated
agent files (`.claude/agents/ocr-page-producer.md` / `ocr-page-verifier.md`)
with per-role tool allowlists. The asymmetry is not a defect (the inline
contracts are detailed and the pipeline has passed three pilot runs), but
general-purpose dispatch means the attribution roles inherit the full tool
set instead of a restricted one.

Candidate change, for review before adopting: create
`.claude/agents/attribution-producer.md` and
`.claude/agents/attribution-verifier.md` mirroring the ocr-page-* pair — move
the producer/verifier discipline out of the skill into the agent contracts,
restrict the verifier to `Read` (it must check the producer's read of the same
evidence, never write), and scope the producer to `Read` + `Write` on its
`/tmp/attribution-{slug}/` draft. Weigh against the cost of a second contract
surface that must stay in sync with the skill's orchestration text.

**2026-06-10 skills/agents audit observation:** a contract-symmetry pass found
no instruction conflicts between the two sibling pipelines — the inline
attribution contracts do not contradict any pipeline-wide rule the dedicated
ocr-page-* agent files establish (producer-never-edits-the-sibling,
verifier-reports-corrections-only, disjoint-range parallelism all hold in
both), and the 4b/4c trigger conditions (`extraction_type` values,
`transcript_provenance` allowlist) are stated identically across both skills,
`build`/`build-protocol`, and `scripts/checks/transcript_sibling_presence.py`.
The asymmetry remains tool-scoping only, as described above.

**Blocks:** none.
**Blocked by:** none.

### C5 — Commit-gate timing redesign (option A) — needs the user in the loop

The commit gate (`.claude/hooks/block_commit_if_red.sh`) runs the entire
pre-commit chain at **PreToolUse time** — before the Bash command executes —
so a compound `fix && git commit` command is gated against its **pre-fix**
state and blocked even when the fix would have turned the chain green
(observed live on the 2026-06-10 dird-33 build:
`build-state.py --update && git commit` was blocked because the gate ran
before the `--update`). The gate content is correct; the evaluation moment is
wrong.

The approved approach (session "option A", 2026-06-10):
1. A repo-versioned `.githooks/pre-commit` that runs the chain **at commit
   execution time** — inside the `git commit` invocation, after any chained
   fix has run — activated via `git config core.hooksPath .githooks`. Compound
   fix-then-commit works; manual terminal commits gain a gate they currently
   lack.
2. `block_commit_if_red.sh` becomes an **anti-bypass guard only**:
   auto-installs `core.hooksPath` on the first commit attempt (fresh clones
   included), denies `--no-verify` / a short-flag cluster carrying `-n` / a
   `core.hooksPath` override, and falls back to running the chain in-place if
   `.githooks/pre-commit` is ever missing (the floor never drops). The
   bypass-flag scan must shlex-tokenize the command with **heredoc bodies
   stripped first**, because commit messages routinely discuss these flags
   ("un-bypassable by `--no-verify`") and message prose must never trip the
   scan.

Every existing doc claim ("a `git commit` runs the full pre-commit chain,
un-bypassable by `--no-verify`") stays literally true — only the mechanism and
timing move. The doc surfaces that describe the current hook
(`CLAUDE.md` §2 + §6, `build-protocol` SKILL.md "How the block actually holds")
must be updated in lockstep.

The 2026-06-10 auto-mode classifier **correctly blocked** the session from
rewriting its own enforcement hook without explicit authorization — that is
the right boundary, do not work around it. Implementing this needs the user
present to approve the enforcement-hook edit. No partial state exists on disk
(the draft `.githooks/pre-commit` was removed after the classifier block).

**2026-06-10 skills/agents audit observation:** the lockstep-update list above
is confirmed complete — a governing-doc sweep found exactly three surfaces
describing the current hook mechanism (`CLAUDE.md` §2 line ~40, `CLAUDE.md` §6,
`build-protocol` SKILL.md "How the block actually holds"); no other skill,
agent, or script doc states the PreToolUse timing, so no additional surface
needs touching when this lands.

**Blocks:** none.
**Blocked by:** explicit user authorization of the enforcement-hook edit.

### C6 — Investigate thoroughly: did the OCR sibling-confirmation process change in a way that weakens the multi-engine cross-check?

Investigation entry — **settle this by reading the current
`scripts/tools/ocr-consensus.py` and re-running it, not from prior session
claims.** State findings with evidence; do not assume the change was safe
because a commit message said so.

What changed on 2026-06-10 (two commits to `ocr-consensus.py`): `verify`
gained derived `~p.N` page tags, and an **engine-read cache** was added —
keyed on `sha256(PDF bytes) + dpi + tesseract_version + paddleocr_version`,
storing the Tesseract and PaddleOCR text under the system temp dir; on a cache
hit `_ocr_pages` loads the stored text instead of rasterizing and re-running
the engines (measured `verify` 8m25s → ~3s on the dird-33 source).

The multi-engine design exists for one reason: PaddleOCR and Tesseract were
chosen as **uncorrelated** readers so each engine's errors — and the VLM
sibling's — are caught by being diffed against the others. A cache that serves
stored engine output changes *when* the engines run, and possibly *whether*
they run on a given invocation.

Questions the next session must answer, each with evidence from the code and a
live re-run:
- Are **both** OCR engines still actually executing and being compared against
  the sibling on the path that matters — the `run` that produces a sibling,
  and the `verify` that re-confirms it after corrections? Or does a cache hit
  substitute stored bytes for one or both engine reads?
- The cache key includes the PDF, dpi, and engine versions but **not** the
  sibling. The sibling is edited between `run` and `verify`. Confirm from the
  code that the sibling-vs-engine comparison is genuinely recomputed against
  the *current* sibling on every `verify`, and that the cache only ever short-
  circuits the engine reads, never the diff. Prove it (e.g. edit a sibling
  token, re-run `verify`, confirm the divergence set reflects the edit).
- Could a stale or colliding cache entry ever feed the comparison engine text
  that does not correspond to the PDF actually on disk? Examine the key's
  collision resistance and what happens on an engine upgrade mid-corpus.
- Does the cache change the **independence** guarantee in any way — i.e., is
  there any path where the sibling is now confirmed against bytes derived from
  the sibling itself, rather than two independent engine reads of the page
  images?
- Re-derive the timing claim and the "byte-identical report" claim
  independently; do not trust the prior session's numbers.

If any answer shows the cross-check is weakened, the cache must be fixed or
reverted — fidelity over speed (the multi-engine design is load-bearing; it
caught the DIRD-16 silent misreads and the dird-32 equation placeholders).

**2026-06-10 skills/agents audit observation (code-read only — the live re-run
above is still required):** reading `ocr-consensus.py` as committed found no
weakening on paper. `_engine_cache_dir` keys on the full PDF bytes + dpi + both
engine versions and its docstring states the sibling is deliberately excluded
because engine output is a pure function of the page images; the cache stores
engine text only (`tess.txt`, `paddle.txt`, `starts.json`); on `verify` the
sibling is re-read from disk (`sibling.read_text`) and `confirm_report(sib_text,
tess_text, paddle_text)` recomputes the comparison on every call, so a cache hit
short-circuits the engine *reads*, not the diff, and no code path feeds the
sibling back as engine input. This answers the code-evidence half of the
questions above; the live-edit re-run, collision/engine-upgrade probing, and
independent timing re-derivation remain open.

**Blocks:** none.
**Blocked by:** none.

