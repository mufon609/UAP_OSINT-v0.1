---
name: prepare-ocr-sibling
description: Produce a clean-text .txt sibling for an OCR-scanned primary source via a VLM page-image read, then confirm it against PaddleOCR (a different tool). An OCR-scan source's pdftotext layer is corrupt, so verbatim quotes cannot be derived from it until a trustworthy sibling exists. Use before building or quoting a source flagged extraction_type ocr-scan / extraction-lossy that has no sibling; /build step 4b directs here.
argument-hint: {category}/{filename}.pdf
allowed-tools:
  - Agent(ocr-page-producer, ocr-page-verifier)
  - Read
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

**The lifecycle is four stages, two of them independent checks:**

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
   substitute for the page-image verification you do in stage 2: do not defer the
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

**Production methods, pre-screen, and fallbacks.** The default path below is the
VLM page-image read confirmed against PaddleOCR. Two things can select against it
or replace it:

- **CBRN pre-screen — do this first.** The VLM runs through the model provider's
  *generative* content-safety filter — a platform guardrail, separate from this
  repo's topic scope. It fires unpredictably (it has blocked one source while
  cleanly transcribing another of comparable subject) and is never a signal about
  a source's relevance. Its one *predictable* trip is content the model's policy
  treats as sensitive to **reproduce**: plainly CBRN / weapons-design-sensitive
  material hard-terminates the VLM mid-transcription. Judge from the title / table
  of contents; if the source is plainly CBRN, **skip the VLM step and start at a
  dedicated OCR engine** — a recognition model, not generative, so it is
  filter-immune.
- **Production-method ladder.** A *read* (a token-recognition pass) can come from
  any of four passes; a single pass — however careful — is exactly what failed, so
  whichever you use, confirm it against a read by a *different tool* before it
  becomes canonical:
  1. **Text-layer pull** — `pdftotext -layout`; only when the buried layer happens
     to be clean (diff against the rendered page first).
  2. **VLM page-image read** (default) — highest fidelity on degraded scans
     (contextual glyph restoration, equation/table handling); the
     producer → PaddleOCR flow below. Use whenever it completes.
  3. **Dedicated OCR engine** (filter fallback, filter-immune) — **Tesseract 5**
     (`sudo apt install tesseract-ocr`; rasterize with `pdftoppm`) as the
     free/local default, or a cloud Document-OCR API (Google Document AI / Azure
     Document Intelligence) for math / Greek / layout. Output requires
     page-by-page contributor review against the source PDF — the contributor is
     the independent verifier here.
  4. **Manual transcription** — last resort for short documents an engine mangles
     (the visual read that produces the text is its own verification).
- **Record the method** (VLM / Tesseract / cloud-OCR / manual) in the sibling's
  manifest note (step 4), so per-sibling fidelity stays transparent and the method
  can improve over time without re-litigation.

---

1. **Confirm the need.** Read the source's manifest entry (`python3
   scripts/tools/manifest.py status {url}`, or grep `sources/manifest.yaml`).
   Proceed only if flagged `ocr-scan` / `extraction-lossy` AND no same-stem
   `.txt` sibling already exists. Note the parent URL (needed to register the
   pairing) and the page count (`pdfinfo`).
   - **Multi-document FOIA email releases** (a release bundling several
     enclosures — cover letter, memos, email/chat threads) get `DOCUMENT N`
     headers in the sibling delimiting each discrete enclosure, so quotes can
     anchor with the `Doc N` location form (see `meta/schema-research-artifact.yaml`
     quote `source.location`).

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

   Each verifier returns a `LINE … | FIND: … | REPLACE: …` correction list. Apply
   the lists **mechanically** — centrally, so parallel verifiers never race on the
   file — by feeding the correction lines (only those lines; never the verifier's
   prose or summary) to the tool, which enforces the each-`FIND`-matches-exactly-once
   rule and applies all-or-nothing (dry run first, then `--write`):
   ```
   python3 scripts/tools/ocr-consensus.py apply sources/{category}/{stem}.pdf --stdin --write <<'EOF'
   LINE 412 | FIND: cstimate of the | REPLACE: estimate of the
   EOF
   ```
   Never hand-edit the sibling — the corrections are agent judgment, the write is
   the tool's (agents judge; scripts mutate). Then re-run to confirm clean:
   ```
   python3 scripts/tools/ocr-consensus.py verify sources/{category}/{stem}.pdf [--blocked-pages 9-11,29-30]
   ```
   `verify` re-confirms the on-disk sibling without regenerating it. Repeat until
   the only remaining divergences are OCR errors on a correct sibling. The sibling
   is now confirmed and canonical.

4. **Register the paired manifest entry — mechanically.**
   ```
   python3 scripts/tools/manifest.py add-sibling clean-text \
       --parent-path {category}/{stem}.pdf \
       --method "VLM page-image read, confirmed against PaddleOCR + Tesseract" \
       [--blocked-pages "9-11, 29-30"] \
       --details "<the editorial remainder: FOIA/distribution insert preserved
       verbatim; equations/figures bracketed; redactions + source spellings
       preserved verbatim; source typos kept (list)>"
   ```
   The tool derives the anchor URL (`{parent_url}#clean-text-transcription`),
   `wayback_skip`, the sibling path from the parent stem, and the note skeleton
   (method + produced date + blocked-pages clause) — and **errors if the parent
   isn't registered**, so the pairing is checked, not remembered. `--method` is
   required (record VLM / Tesseract / cloud-OCR / manual deliberately); only the
   genuinely editorial remainder rides `--details`. Confirm with `manifest.py
   verify-paths`. **Register the sibling at the moment of creation** — a
   sibling-on-disk-but-not-in-manifest is a silent dependency: quote
   verification depends on a file the manifest doesn't record, and deleting it
   (e.g. as "orphan cleanup") silently reverts `extract-source.py` to the PDF's
   unusable text layer and breaks the build. Treat `manifest.py verify-paths`
   plus pre-commit as the only safe orphan-cleanup gate for sibling files;
   never delete an unregistered sibling on sight. **Do not list the sibling in any artifact's `primary_sources[]`**
   — the parent PDF is the primary source; the sibling is only the extraction
   surface. `extract-source.py` auto-prefers the sibling for OCR-scan sources, so
   quotes derive verbatim text from it but cite the PDF path in `source.path`.

5. **Record the `content_block` value — mechanically.** When the target's
   research artifact exists (the `/build` path: 4b runs after scaffold), pass
   `--stamp-artifact meta/research/{slug}.yaml` on the `run` (or the final
   `verify`) — the tool writes the value onto the matching `primary_sources[]`
   entry itself (surgical line edit; a vlm-skipped sentinel from the original
   `run` is never overwritten by `verify`). No artifact yet (standalone
   backfill)? The printed `content_block:` line is the canonical value; stamp
   it once the artifact exists via
   `ocr-consensus.py verify {pdf} --stamp-artifact {yaml}` (seconds on the
   engine cache). Never hand-type the value; that's the field's whole point.

6. **Corroborate already-extracted quotes — backfill case only.** If the
   target's artifact *already carries quotes* citing this source (this skill ran
   as a backfill on a built node, or the sibling was re-edited under existing
   quotes), follow the `content_block` stamp with
   `python3 scripts/tools/ocr-consensus.py corroborate-quotes {pdf} --artifact
   meta/research/{slug}.yaml` — it re-checks just the quoted spans against the
   engine reads and stamps `quote_corroboration` (the auditor's page-image
   target list; the `quote_ocr_corroboration` check is its commit-boundary
   backstop). On the normal `/build` path quotes don't exist yet — the
   orchestrator runs this at build step 6b instead.

The sibling is canonical once confirmed and registered; `extract-source.py` and
the verbatim-quote check prefer it. Hand back to `/build` (or the contributor) to
extract the clean scratch and run the Worker. **The final independent check is at
node audit:** `/audit` verifies the built node's quotes against the source PDF
page images — not the sibling — so a sibling error that reached a quote is caught
against the original; the `quote_corroboration` stamp enumerates the tokens that
read must settle first. After that passes, the node and sibling are good to go.
