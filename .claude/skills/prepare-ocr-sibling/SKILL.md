---
name: prepare-ocr-sibling
description: Produce a clean-text .txt sibling for an OCR-scanned primary source via a VLM page-image read, then confirm it against PaddleOCR (a different tool). An OCR-scan source's pdftotext layer is corrupt, so verbatim quotes cannot be derived from it until a trustworthy sibling exists. Use before building or quoting a source flagged extraction_type ocr-scan / extraction-lossy that has no sibling; /build step 4b directs here.
argument-hint: {category}/{filename}.pdf
allowed-tools:
  - Agent(general-purpose)
  - Read
  - Edit
  - Bash(python3 scripts/tools/ocr-consensus.py *)
  - Bash(python3 scripts/tools/manifest.py *)
  - Bash(cat *)
  - Bash(pdfinfo *)
  - Bash(pdftoppm *)
  - Bash(tesseract *)
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

2. **Produce the VLM page-image read — per-page chunked.** Dispatch
   `Agent(general-purpose)` producers that read the source's page IMAGES (`Read`
   with `pages: "N"` — **one page at a time**) and **write each page to its own
   scratch file before reading the next** (e.g. `/tmp/{stem}/pNN.txt`,
   zero-padded). Per-page writes are load-bearing: the content filter blocks model
   *output* (reproducing a passage), and a block kills the agent turn — per-page
   isolation means a block costs one page, not the whole run, and the set of
   written files is a blocked-page ledger. Parallel producers can split disjoint
   page ranges; for ranges that die mid-block, dispatch one producer **per missing
   page** to find which pages block *in isolation*.

   Transcription discipline (per `meta/conventions.md` "Producing the `.txt`
   sibling"): reproduce body prose character-for-character including the
   document's own typos and spellings (do NOT correct); preserve redaction
   markers and banners verbatim; render equations/figures/diagram interiors as
   bracketed placeholders (`[Figure N: …]`); transcribe every physical page
   including any third-party FOIA / distribution cover-insert (e.g. a Black Vault
   page); reproduce TOC entries without dot-leader runs; no synthetic page-break
   markers.

   **Genuinely-blocked pages → PaddleOCR-fill (produce ≠ verify).** The content
   filter blocks model *output* — *reproducing* a passage — so the VLM cannot
   **produce** a blocked page. PaddleOCR can: rasterize that one page and fill its
   slice from **PaddleOCR** (the better OCR engine, not content-blocked: `pdftoppm
   -png -r 300 -f N -l N …`, then run that page through `ocr-consensus.py`'s
   PaddleOCR path). **Keep the page numbers** — they are the blocked-page ledger,
   needed for `--blocked-pages` in step 3 and the `Content Block` field in step 5.
   The VLM still **verifies** these pages in step 3: judging PaddleOCR's pull
   against the image (or pinpointing a wrong token) is a tiny output, not
   reproduction, so it is not blocked — the high-fidelity check survives even
   though the high-fidelity *transcription* didn't.

3. **Write the sibling + confirm it against PaddleOCR.** Pass the **per-page
   directory** so the tool concatenates it and can tag every divergence with its
   page number — do **not** hand-`cat` the pages into one file (that throws away
   the page boundaries the verification step needs). Redirect the report to a file
   (it can be thousands of lines on a figure-heavy PDF) — **never pipe it through
   `tail`/`head`**, which silently drops the bulk of the report:
   ```
   python3 scripts/tools/ocr-consensus.py run sources/{category}/{stem}.pdf \
       --vlm-pages /tmp/{stem} [--blocked-pages 12,31] [--force] \
       > /tmp/{stem}-confirm.txt 2>&1
   ```
   `run` writes the VLM text as the sibling `.txt`, then re-reads the pages with
   PaddleOCR + Tesseract and prints the **load-bearing divergence report**: every
   word/number where the sibling and the OCR engines disagree (document structure
   — punctuation, bullets, banners, figure labels — is never compared). `Read`
   `/tmp/{stem}-confirm.txt`. Pass `--blocked-pages` the ledger from step 2
   (accepts ranges, e.g. `5-7,10,14-15`). `--force` regenerates an existing sibling
   (backfill). Heed any `⚠ COVERAGE WARNING`: a large contiguous run of
   OCR-corroborated tokens missing from the base means the VLM dropped a
   paragraph/page — recover it before proceeding.

   **The report is partitioned — verify the HIGH-SIGNAL set against the page
   images; skim the weak set.**
   - **HIGH-SIGNAL** (`both OCR engines read the same token, differing from the
     sibling`) is the set you MUST settle. Each row is **either** a VLM misread
     to fix **or** a shared OCR glyph-confusion where the sibling is right
     (`µm→um`, `SiO2→SiOz`, `λ_0→Ao`) — and **the page image is the only thing
     that tells them apart.** For **every** high-signal row: `Read` the PDF at its
     reported page (`pages: "N"` — the `p.N` in the row), find the token in the
     image, and decide the true reading **from the image**. Where the VLM
     misread, **correct the sibling** with `Edit` (it is the canonical text — fix
     it now, before any quote derives from it); where the OCR engines share a
     glyph error, leave the sibling as-is.
   - **Do NOT decide a high-signal row from the surrounding sibling text or
     grammatical plausibility.** That re-trusts the VLM against itself — exactly
     the silent-misread failure (`81→82`, `Klyshko→Kiyshko`) PaddleOCR exists to
     catch. "It reads fine in context" is not verification; opening the page
     image is. This image pass happens **here**, not deferred to the node audit.
   - **weak** (`no single OCR reading corroborated`) is dominated by
     struck-through banners, bracketed `[Figure N: …]`/`[Equation N: …]`
     placeholder text, and per-engine glyph noise. Skim it; open the page image
     only where a weak row lands on **body prose** (a real word the sibling may
     have dropped or mangled), not on banner/figure furniture.

   **VLM-verify each blocked page.** For a blocked page the sibling text *is* the
   PaddleOCR fill, so the sibling-vs-engines diff is silent there — `--blocked-pages`
   instead prints the **PaddleOCR-vs-Tesseract** disagreements (the two engines'
   highest-risk tokens). For each blocked page: read its page image and **verify**
   PaddleOCR's fill (the VLM can judge it even though it couldn't produce it),
   paying special attention to the flagged PaddleOCR-vs-Tesseract tokens; correct
   the sibling where PaddleOCR misread. Re-run to confirm clean:
   ```
   python3 scripts/tools/ocr-consensus.py verify sources/{category}/{stem}.pdf [--blocked-pages 12,31]
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

5. **Record the `Content Block` provenance.** The blocked-page outcome becomes a
   durable, greppable field on the node. Note the value for the source's
   `content_block` (on its `primary_sources[]` entry in the research artifact —
   `meta/schema-research-artifact.yaml`; renders as a `Content Block` row in the
   document node's Document Summary table):
   - every page VLM-read → `None`;
   - some pages PaddleOCR-filled → e.g. `Pages 12, 31 were content-blocked for the
     VLM; PaddleOCR-filled.`;
   - whole document content-blocked (`--vlm-skipped`) → `All pages — VLM
     page-image read was content-blocked; produced via OCR.`
   When the node is built (`/build`) this goes on the primary source; the build
   pipeline's `primary_sources` stub carries `content_block`. An investigator can
   then `grep -rn "Content Block" documents/ | grep -v None` to find every node
   with OCR-filled pages.

The sibling is canonical once confirmed and registered; `extract-source.py` and
the verbatim-quote check prefer it. Hand back to `/build` (or the contributor) to
extract the clean scratch and run the Worker. **The final independent check is at
node audit:** `/audit` verifies the built node's quotes against the source PDF
page images — not the sibling — so a sibling error that reached a quote is caught
against the original. After that passes, the node and sibling are good to go.
