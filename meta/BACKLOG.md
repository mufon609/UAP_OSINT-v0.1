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

### C1 — Ingest a book delivered as page images into a verified text transcription

A book (or any long document) delivered as a directory of page images — cover,
back, and each non-blank page — should become a single verified `.txt`
transcription that serves as the citeable primary source. This is far more
content than the repo ingests today (single sources, not multi-hundred-page
collections), so the route must be deliberate, not an afterthought.

The transcription machinery already exists and is reusable: the VLM page-image
read + dual-OCR consensus (`scripts/tools/ocr-consensus.py`) and the
`ocr-page-producer` / `ocr-page-verifier` agents, which already read page
IMAGES one at a time and settle divergences against them. What is missing is
image-directory input: `ocr-consensus.py` is bound to PDF (`pdfinfo` for page
count, `pdftoppm` to rasterize). Generalize it to accept a directory/list of
page images (skip rasterization; page count from the file list), and generalize
the `/prepare-ocr-sibling` skill (or add a sibling skill) to dispatch the
producers across image-file ranges the way it fans out over PDF page ranges.
`extract_source_text` already reads a committed `.txt` sibling for an image
source, and such a transcription earns real verification (a quote that does not
match the sibling errors), so the quote-citation rail is already in place.

Open design considerations to settle before building:
- **Assembly target.** After transcribing, consider combining the pages into a
  text-layer (searchable) PDF, which would then ingest through the existing
  text-native PDF route and sidestep any image-collection manifest schema.
  Weigh this against registering the `.txt` as the primary source with the
  page-image directory as archived provenance.
- **Manifest convention.** No "collection" entry exists today (the manifest
  registers single artifacts). Decide: txt-as-primary + image-dir provenance, a
  new image-collection entry, or the text-PDF above.
- **Scale.** OCR cost is per-page; a multi-hundred-page book is a long consensus
  run with content-filter blocks handled per page — confirm the scratch layout,
  caching, and single-sibling assumptions hold at that size before committing to
  a real book.
- **Location grammar.** The transcription is flat text (no synthetic page
  markers), so book quotes anchor via the `¶ "<leading phrase>"` descriptive
  form that resolves against the sibling.

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

### C3 — Purge internal entry-ID references from artifact prose, and gate against them

Artifact free-text fields cite internal entry IDs (`q39`, `cw2`, `nq4`,
`or10`, `t8`, `kp1`, cross-artifact forms like "aaro q13", "0446 q1") as if
they were stable pointers. They are not:

- IDs are positional and shift across merges and rebuilds.
- No gate checks that a prose reference resolves to the entry the author
  meant, so the references rot silently.
- They also render into node bodies (Key Passage headings, Location rows),
  where a reader cannot resolve them.

A confirmed instance: two aaro Key Passage significances cited `q39`/`q40`
as FOIA 24-F-0894 rollout emails, but those IDs are Shellenberger
testimony quotes. The intended passages carry other IDs.

The plain-reader rule: prose names the source (document, date, section),
never an entry ID. The structured lifecycle pointers (`superseded_by` /
`contradicted_by` / `corroborated_by`) are exempt; they are ID-typed fields
that `scripts/checks/cross_refs.py` resolves.

The ipmo, ousd-is and aaro `significance` and `description` fields are
already clean; the rest of the corpus has not been swept.

1. **Inventory.** Scan every free-text field in every `meta/research/*.yaml`
   for ID tokens, including cross-artifact forms: `description`, quote
   `significance` / `context` / `source.location`, `naming_quirks[].location`,
   timeline `event`, relationship `location`, and any other prose field.
   Also scan rendered node bodies, `meta/topic/working-notes/` and
   `meta/topic/research-queue.md`, and decide explicitly whether the
   working-note convention of citing quote IDs stays. Exclude the lifecycle
   pointer fields.
2. **Adjudicate each hit.** Read the surrounding prose and the entry the ID
   currently points at, and classify the reference as correct or stale.
   Replace it with the source's name. Where it was stale, identify the entry
   actually meant and check that the prose claim still holds against it.
   Stale hits are evidentiary defects, not wording fixes. Record each one in
   the commit message.
3. **Gate.** Add a check module under `scripts/checks/` that errors on ID
   tokens in prose fields. Dispatch it from `validate-research.py` at the
   phase that owns the field, register it with `route_failure.py` /
   phase-routing parity, and add a regression test under `scripts/tests/`.
   Drive the existing corpus to zero before enabling it as an error.
4. **Stop the source.** Worker and builder output introduces these
   references: a worker significance ending "(q6)", builder
   naming-quirk locations "(q52)" / "quoted in q40". Add the rule to the
   worker and builder contracts in `.claude/agents/` and to `build-protocol`
   so no role emits an ID into prose. Also check the templates and prompts
   under `prompts/` for examples that model the habit.

### C4 — Harden the Worker extraction step against large-source timeouts and over-exploration

The Worker role (one invocation per source, the verbatim-extraction boundary)
showed two robustness gaps on a large OCR-scan source (a 37-page DIRD yielding 38
quotes + 20 `cited_works`):

- **The monolithic fragment Write is stall-prone.** The Worker emits its entire
  fragment (all quotes + `cited_works`) in a single `Write` tool-call. On a large
  source that payload runs tens of KB, and generating it in one shot after a heavy
  read context can stall the model long enough to trip the stream-idle-timeout —
  losing the whole extraction, because no incremental progress is saved. The same
  source extracted cleanly on one Worker run and stalled mid-final-Write on a
  second (idle-aborted after the work was effectively done). Investigate an
  incremental / checkpointed fragment write (append per page or per section, so a
  stall costs one chunk, not the run), a larger agent timeout for large sources, or
  an explicit size threshold above which the source is chunked — weigh against the
  byte-exact `merge-fragments.py` transport contract, which assumes one fragment
  file per source.
- **The Worker over-explores beyond its assigned source.** Despite the
  build-protocol "No built node is an example" rule, a Worker read a sibling
  node's full research artifact (the Part I DIRD) unprompted, plus ran several
  greps/globs — inflating its context (worsening the stall above) and crossing the
  no-example boundary. The Worker's job is to extract from its ONE assigned source
  + scratch; the reuse/precedent survey is the internal-investigator's, threaded
  forward via `linked_nodes`. Decide whether to tighten the Worker contract and/or
  add a guard so it reads only its assigned source + scratch. (Per-command Bash /
  Read scoping is advisory — see `build-protocol` "Mechanical enforcement vs. role
  discipline" — so a hard guard may not be mechanizable; a contract tightening may
  be the realistic lever.)

**Related:** the two-scratch footgun — `extract-source.py --source`
(internal-investigator survey aid) and `--artifact` (Worker scratch) leave a
corrupt extract and the clean sibling-backed extract side-by-side in `/tmp`; the
orchestrator must relay the `--artifact` (`-0.txt`, sibling-backed) path, never the
corrupt survey aid.

**Blocks:** none.
**Blocked by:** none.

### C5 — Run one slow sweep of the existing `archive_status: 1` entries

The `/build` finalize step (step 8) now Wayback-submits any `archive_status: 1`
source the build touched, closing the all-internal branch's silent gap (the
Archive role — the only prior submitter — is skipped on that branch). What
remains is the one-time backlog predating that step: run one slow sweep
(`archive.py --submit-path` / `--submit`, strictly sequential, ≥20 s apart) of
the 166 manifest entries currently sitting at `archive_status: 1` (2026-09-26
count — recount before sweeping; the number drifts).

**Blocks:** none.
**Blocked by:** none.

### C8 — Close the `foia` node type's open ends before the first real FOIA nodes

The `foia` type is in the schema, renderer and validators and is covered by
smoke fixtures. One thing remains before real FOIA nodes can be built cleanly:

1. **Back-pointers on existing FOIA-derived documents.** When the first `foia`
   nodes are built for the third-party requests already behind corpus documents
   (e.g. FOIA 23-F-0906, 23-F-1114), add `released_via` to those `document` nodes
   and re-run `associate.py`.

Changing `request_state` after creation uses the same path as `status` today
(`new.py --force`, then re-render). No separate tool is needed unless that path
proves error-prone.

**Blocks:** none.
**Blocked by:** C9 (both released-document nodes need a verified OCR sibling first).

### C9 — Desktop OCR consensus pass: 23-F-1114 release PDF, the IPMO PWS sibling, a Grusch PPD-19 check, and the Tipton / IG-evaluation release files

`government/blackvault-sancorp-23-f-1114-aaro-pws.pdf` (117 pages) is an OCR scan
from p. 4 on, but it has no verified `.txt` sibling and is not flagged `ocr-scan`.
Its 20 existing quotes were therefore verified against unverified OCR text:

- `aaro` q12;
- `dod-23-f-1114` q1–q13;
- `sancorp-consulting` q1–q6.

The VLM page reads are **done and parked** at
`.scratch/drafts/ocr-blackvault-sancorp-23-f-1114-aaro-pws/` (115 of 117 pages).
Pages 25 and 89 were refused by the VLM content filter and need the OCR fill.

**Blocked on the PaddleOCR pass.** PaddleOCR inference segfaults on the ARM64
maintainer box under every package combination tried, including the
previously working pair. Run the consensus pass (PaddleOCR + Tesseract) on the
maintainer's desktop, where it has worked before, from the parked page reads:

    ocr-consensus.py run … --vlm-pages <parked dir> --blocked-pages 25,89

Then:

1. Run the verifier pass and registration per `/prepare-ocr-sibling`, and set
   `extraction_type: ocr-scan`. Do not set the flag before the sibling exists:
   on its own it makes `validate-research.py` fail.
2. Re-verify the 20 quotes via `/augment`. The VLM reads of pp. 5–9 suggest
   OCR-error fixes are due on `sancorp-consulting` q2–q6 and `aaro` q12. Settle
   them only against the confirmed sibling.
3. Re-examine `sancorp-consulting` naming quirks nq3–nq8. They may record
   OCR garbage as if it were the source's own spelling.

The AARO PWS document node (`documents/blackvault-sancorp-23-f-1114-aaro-pws`)
quotes this PDF, so it waits on this item.

**Also in this pass: redo the IPMO PWS sibling.**
`government/foia-23-f-0906-sancorp-ipmo-pws.txt` (the separate
`…23-F-0906_Performance_Work_Statement.pdf#clean-text-transcription` entry) is
effectively the raw `pdftotext -layout` output: similarity ≈ 1.0, with only a
few heading fixes. It still carries OCR errors, e.g. line 2 "April 25,2022",
line 119 "(T&M)feentrnet.", line 241 "Active IS". The PDF artifact is
correctly flagged `ocr-scan`, but the sibling was never consensus-verified.
Its manifest note has been corrected to say so.

- Run `/prepare-ocr-sibling` on `government/foia-23-f-0906-sancorp-ipmo-pws.pdf`,
  then set the flag.
- Re-verify the quotes that cite it. `sancorp-consulting` q35 reproduces the
  "April 25,2022" OCR error; check `ipmo` and `sancorp-consulting` for the rest.
- The PWS names no issuing office and shows no FOIA case number. Re-check two
  things against the verified sibling: `ipmo` q6's context naming WHS
  Acquisition Directorate as the issuer (the PDF's own manifest note says the
  same), and the "released via FOIA 23-F-0906" wording that `ipmo` t2 and
  `sancorp-consulting` t31 attribute to the "PWS title block". Re-source them to
  the release index or the FOIA node where needed.

**Check `government/grusch-ppd-19-procedural-filing.txt`.** It is the only other
contributor-made (non-consensus) sibling that sits close to raw OCR
(similarity 0.991). Confirm it against page images, or redo it with consensus.
All other siblings with a PDF parent diverge from raw OCR the way corrected
siblings should.

**Also in this pass: the three Tipton / DoD IG UAP-evaluation release files.**
They were archived 2026-09-26 and flagged `ocr-scan` in the manifest. None has a
sibling, so none is cited as a primary source or quoted yet:

- `government/foia-23-f-0446-final-response-tipton-oig-email.pdf` (3 pp.).
  p. 1 is the FOID final response of June 22, 2023. It is text-native, but
  the file carries one flag. p. 2 is the released 2023-01-11 Tipton–OIG email.
  It is a scan, and its OCR layer is corrupt ("l&S", "Unclazifiod").
- `government/foia-23-f-0377-tipton-calendar-20211019-bv-excerpt.png`. The Black
  Vault's screenshot of the 23-F-0377 calendar entry for the 2021-10-19 meeting.
  It has no text layer.
- `government/foia-dodig-2023-000021-oig-email-20211104-bv-excerpt.jpg`. The
  Black Vault's screenshot of the 2021-11-04 DoD OIG email released under
  DODOIG-2023-000021. It has no text layer.

The two images are the first lossy-flagged non-PDF sources.
`ocr_sibling_presence.py` checks PDFs only, and its docstring says to decide the
sibling story before extending it. Decide whether `/prepare-ocr-sibling` takes
single-image sources first. After that:

1. Add the files to `foia/dod-23-f-0446` and `foia/dod-23-f-0377` via
   `/augment`: the 0446 letter (pages, exemption, IDAs, signer, the DODOIG
   referral) and the released records.
2. Reassess `people/neill-tipton`, left unbuilt because the only quotable
   content was the requester's own descriptions.
3. Settle the OIG project number. It is printed "D2021-DEV0SAN-0116" in the JPG
   (visual read), "D2021-DEVOSN-0116.000" in the 0446 OCR layer, and
   "D2021-DEV0SN-0116.000" in the FOIA log's request text.

**Blocks:** building `documents/blackvault-sancorp-23-f-1114-aaro-pws` and `documents/foia-23-f-0906-sancorp-ipmo-pws`; the release-record additions to `foia/dod-23-f-0377` / `foia/dod-23-f-0446` and the `people/neill-tipton` decision.
**Blocked by:** a working PaddleOCR environment (C10, or the maintainer's desktop).

### C10 — Make the OCR venv isolated and version-pinned

`scripts/tools/setup-ocr-consensus.sh` builds `.venv-ocr/` with
`--system-site-packages`. That only works while the venv's Python matches the
system Python. After a system Python upgrade, compiled system packages
(cryptography/cffi, Pillow, kiwisolver, ujson) fail to import under the venv's
older interpreter.

Rebuild the venv isolated (no `--system-site-packages`) and install everything
`ocr-consensus.py` needs inside it: `paddlepaddle paddleocr numpy pillow
pyyaml`. Then pin the versions from a `pip freeze` of an environment where
inference **actually runs** (import alone is not enough). Separately, find out
why PaddleOCR inference segfaults on aarch64 with PaddlePaddle 3.2.2 even with
isolated deps, oneDNN off and single-threaded. Pin a PaddlePaddle build known
to infer on aarch64, or document that the consensus pass runs off-box.

**Blocks:** C9 on the ARM64 box.
**Blocked by:** none.
