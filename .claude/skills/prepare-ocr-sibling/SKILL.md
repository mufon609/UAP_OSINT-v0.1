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
   and is diffed against the sibling on the **words and numbers**; an agent
   reconciles each divergence against the page image and corrects the sibling.
   *(This is this skill.)*
3. **Build the node**, pulling quotes from the confirmed sibling (`/build`).
4. **Audit** — the auditor verifies the built node's quotes against the **source
   PDF page images**, not the sibling. *(That final check lives in `/audit`, not
   here.)*

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

   **Genuinely-blocked pages → PaddleOCR-fill.** For each page that blocks in
   isolation, rasterize that one page and fill its slice from **PaddleOCR** — the
   better OCR engine and one the content filter does not block (`pdftoppm -png -r
   300 -f N -l N …`, then run that page through `ocr-consensus.py`'s PaddleOCR
   path). The PaddleOCR fill becomes the sibling text for those pages; note them
   so the step-2 confirmation treats them as already-OCR (a PaddleOCR-vs-PaddleOCR
   page won't surface VLM divergences — confirm those pages by eye against the
   image).

3. **Write the sibling + confirm it against PaddleOCR.** Concatenate the per-page
   files in order (`cat /tmp/{stem}/p*.txt > /tmp/{stem}-vlm.txt`; zero-padding
   sorts correctly). Then:
   ```
   python3 scripts/tools/ocr-consensus.py run sources/{category}/{stem}.pdf \
       --vlm /tmp/{stem}-vlm.txt [--force]
   ```
   `run` writes the VLM text as the sibling `.txt`, then re-reads the pages with
   PaddleOCR + Tesseract and prints the **load-bearing divergence report**: every
   word/number where the sibling and the OCR engines disagree (document structure
   — punctuation, bullets, banners, figure labels — is never compared, so the
   report is short and load-bearing). `--force` regenerates an existing sibling
   (backfill). Heed any `⚠ COVERAGE WARNING`: a large contiguous run of
   OCR-corroborated tokens missing from the base means the VLM dropped a
   paragraph/page — recover it before proceeding.

   **Reconcile each divergence against the page image.** For every reported token,
   open the page image at the given line and decide the true reading. Where the
   VLM misread, **correct the sibling** with `Edit` (the sibling is the canonical
   text — fix it now, before any quote derives from it). Where the VLM is right and
   the OCR engines are wrong (common — they share glyph-confusion failures like
   `SiO2→SiOz`, `Lím→Lim`), leave the sibling as-is. Re-run to confirm clean:
   ```
   python3 scripts/tools/ocr-consensus.py verify sources/{category}/{stem}.pdf
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

The sibling is canonical once confirmed and registered; `extract-source.py` and
the verbatim-quote check prefer it. Hand back to `/build` (or the contributor) to
extract the clean scratch and run the Worker. **The final independent check is at
node audit:** `/audit` verifies the built node's quotes against the source PDF
page images — not the sibling — so a sibling error that reached a quote is caught
against the original. After that passes, the node and sibling are good to go.
