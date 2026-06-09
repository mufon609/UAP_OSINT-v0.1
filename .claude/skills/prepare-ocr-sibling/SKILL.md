---
name: prepare-ocr-sibling
description: Produce a clean-text .txt sibling for an OCR-scanned primary source via a VLM page-image read, then confirm it against PaddleOCR (a different tool). An OCR-scan source's pdftotext layer is corrupt, so verbatim quotes cannot be derived from it until a trustworthy sibling exists. Use before building or quoting a source flagged extraction_type ocr-scan / extraction-lossy that has no sibling; /build step 4b directs here.
argument-hint: {category}/{filename}.pdf
allowed-tools:
  - Agent(ocr-page-producer, ocr-page-verifier)
  - Read
  - Edit
  - Bash(python3 scripts/tools/ocr-consensus.py *)
  - Bash(python3 scripts/tools/manifest.py *)
  - Bash(cat *)
  - Bash(pdfinfo *)
---

# Prepare an OCR-scan clean-text sibling, then confirm it

Target source: **$ARGUMENTS** — a path under `sources/` (e.g.
`government/foo.pdf`). Ask the user if empty.

An OCR-scanned source (manifest `extraction_type: ocr-scan` / `extraction-lossy`)
has a corrupt text layer: quotes pulled from it are garbage or trip the
verbatim-quote gate. Its canonical text is a same-stem `.txt` **sibling** — and
because future quotes and research derive from that sibling, it has to be
accurate.

**The process is four steps, two of them independent checks:**

1. **Transcribe** the page images to a `.txt` sibling (a VLM page-image read).
2. **Confirm the sibling with a different tool** — PaddleOCR re-reads the pages
   and is diffed against the sibling on the **words and numbers**. The report
   splits into a small **HIGH-SIGNAL** set (both OCR engines agree against the
   sibling) and a skim-only **weak** set; you settle every high-signal
   divergence **against the page image** and correct the sibling where the VLM
   misread. *(This is this skill.)*
3. **Build the node**, pulling quotes from the confirmed sibling (`/build`).
4. **Audit** — the auditor verifies the built node's quotes against the **source
   PDF page images**, not the sibling — the final, independent backstop.
   *(That check lives in `/audit`, not here.)* It is a backstop, **not** a
   substitute for the page-image verification you do in step 2: do not defer the
   image check to the audit.

Why two different tools? A single read can't be trusted on itself: the VLM
content filter blocks some pages, and one vision pass can misread silently
(DIRD-16's first single-pass sibling carried `III→ITT`, `81→82`,
`Klyshko→Kiyshko`, all "PASS"). PaddleOCR is a *different modality* (deep-learning
OCR, not content-blocked), so it catches the VLM's misreads instead of sharing
them. This is source **prep**, not node building — it produces a faithful
transcription of a primary source, never node content.

**Prerequisite:** PaddleOCR lives in `.venv-ocr/` — run
`scripts/tools/setup-ocr-consensus.sh` once (the user runs it; it `sudo apt`s a
few libs). `ocr-consensus.py run` / `verify` auto-relaunch under that venv.

---

1. **Confirm the need.** Read the source's manifest entry (`python3
   scripts/tools/manifest.py status {url}`, or grep `sources/manifest.yaml`).
   Proceed only if flagged `ocr-scan` / `extraction-lossy` AND no same-stem
   `.txt` sibling already exists. Note the parent URL (needed to register the
   pairing) and the page count (`pdfinfo`).

2. **Produce the VLM page-image read.** Dispatch **`Agent(ocr-page-producer)`**,
   one per disjoint page range, in a single message so they run concurrently. Pass
   each, and only: the **source PDF path**, its **page range** `A–B`, and the
   **output directory** (`/tmp/{stem}/`). The producer contract owns the rest —
   the per-page-write-before-next isolation, the verbatim transcription discipline,
   and the skip-a-blocked-page rule. Do **not** restate that discipline in the
   dispatch (the contract is the source of truth; an improvised instruction would
   override it).

   Read each producer's returned report (pages written vs. pages skipped). A
   skipped page is content-blocked; **for ranges that died mid-block, re-dispatch
   `Agent(ocr-page-producer)` one page per range** to find which pages block *in
   isolation* (a producer turn ends when the content filter blocks its output, so a
   range agent can't continue past a blocked page on its own). The set of written
   `pNN.txt` files is the blocked-page ledger; collect the still-missing page
   numbers — those are the `--blocked-pages` argument the tool fills in step 3. You
   never `pdftoppm`/PaddleOCR-fill by hand: that is now the tool's job (step 3).

3. **Write the sibling + confirm it against PaddleOCR.** Pass the **per-page
   directory** so the tool concatenates it and can tag every divergence with its
   page number — do **not** hand-`cat` the pages into one file (that throws away
   the page boundaries the verification step needs). Redirect the report to a file
   (it can be thousands of lines on a figure-heavy PDF) — **never pipe it through
   `tail`/`head`**, which silently drops the bulk of the report:
   ```
   python3 scripts/tools/ocr-consensus.py run sources/{category}/{stem}.pdf \
       --vlm-pages /tmp/{stem} --blocked-pages 9-11,29-30 --two-column-pages 30 [--force] \
       > /tmp/{stem}-confirm.txt 2>&1
   ```
   Pass `--blocked-pages` the ledger of pages the producers skipped (step 2; accepts
   ranges, e.g. `5-7,10,14-15`), and `--two-column-pages` the subset of those that
   are two-column. The tool **PaddleOCR-fills** each blocked page into the
   `--vlm-pages` dir before assembling the sibling — column-splitting the two-column
   ones (left half then right) so they don't interleave into scrambled text — so a
   blocked page is **never silently dropped** (it hard-errors if a declared blocked
   page would still be empty). It then writes the sibling, re-reads every page with
   PaddleOCR + Tesseract, and prints the **load-bearing divergence report**: every
   word/number where the sibling and the OCR engines disagree (document structure —
   punctuation, bullets, banners, figure labels — is never compared). `--force`
   regenerates an existing sibling (backfill). `Read` `/tmp/{stem}-confirm.txt`. A
   `⚠ COVERAGE WARNING` now means the VLM dropped a region the tool did **not** fill
   (a page missing from `--blocked-pages`, or a mid-page omission) — recover it
   before proceeding.

   **Settle the flagged divergences against the page images.** Dispatch
   **`Agent(ocr-page-verifier)`**, one per disjoint page range that carries flagged
   rows (HIGH-SIGNAL or blocked-page), in a single message so they run concurrently.
   Pass each, and only: its **page range**, the **sibling path**, the **report
   path** (`/tmp/{stem}-confirm.txt`), and the **source PDF path**. The verifier
   contract owns the rest — the leave/fix decision (decide each token from the page
   image, never from surrounding text), the blocked-page handling, and the
   content-filter-safe posture (token-level only; a blocked page blocks the
   verifier's output too if it reproduces a passage). Do **not** restate that
   discipline in the dispatch.

   Each verifier returns a `LINE … | FIND: … | REPLACE: …` correction list. **You**
   apply each with `Edit` on the sibling — centrally, so parallel verifiers never
   race on the file — confirming each `FIND` matches exactly once first. Then re-run
   to confirm clean:
   ```
   python3 scripts/tools/ocr-consensus.py verify sources/{category}/{stem}.pdf [--blocked-pages 9-11,29-30]
   ```
   `verify` re-confirms the on-disk sibling without regenerating it. Repeat until
   the only remaining divergences are OCR errors on a correct sibling. The sibling
   is now confirmed and canonical.

4. **Register the paired manifest entry.**
   ```
   python3 scripts/tools/manifest.py add {parent_url}#clean-text-transcription \
       --path {category}/{stem}.txt --format txt --wayback-skip \
       --note "Clean-text sibling (VLM page-image read, confirmed against PaddleOCR)
       of the OCR-scanned <source>. Produced <date>; pages it blocked on the content
       filter PaddleOCR-filled (<list>). <FOIA/distribution insert preserved verbatim>.
       Equations/figures bracketed; redactions + source spellings preserved verbatim."
   ```
   `#clean-text-transcription` + `--wayback-skip` mark it derived and
   non-fetchable, paired to the parent PDF entry. Confirm with `manifest.py
   verify-paths`. **Do not list the sibling in any artifact's `primary_sources[]`**
   — the parent PDF is the primary source; the sibling is only the extraction
   surface. `extract-source.py` auto-prefers the sibling for OCR-scan sources, so
   quotes derive verbatim text from it but cite the PDF path in `source.path`.

5. **Record the `content_block` value.** `run`/`verify` print a `content_block:`
   line at the end — paste it verbatim onto the source's `primary_sources[]` entry.
   Don't hand-write it; that's the field's whole point.

The sibling is canonical once confirmed and registered; `extract-source.py` and
the verbatim-quote check prefer it. Hand back to `/build` (or the contributor) to
extract the clean scratch and run the Worker. **The final independent check is at
node audit:** `/audit` verifies the built node's quotes against the source PDF
page images — not the sibling — so a sibling error that reached a quote is caught
against the original. After that passes, the node and sibling are good to go.
