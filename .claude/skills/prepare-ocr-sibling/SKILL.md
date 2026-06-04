---
name: prepare-ocr-sibling
description: Produce and register a clean-text .txt sibling (the "grab") for an OCR-scanned primary source via a VLM page-image read, then point to quote-scoped grounding. An OCR-scan source's pdftotext layer is corrupt, so verbatim quotes cannot be derived from it until a trustworthy sibling exists. Use before building or quoting a source flagged extraction_type ocr-scan / extraction-lossy that has no sibling; /build step 4b directs here.
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

# Prepare OCR-scan clean-text sibling (the grab) + quote-scoped grounding

Target source: **$ARGUMENTS** — a path under `sources/` (e.g.
`government/foo.pdf`). Ask the user if empty.

An OCR-scanned source (manifest `extraction_type: ocr-scan` / `extraction-lossy`)
has a corrupt text layer: quotes pulled from it are garbage or trip the
verbatim-quote gate. Its canonical text is a same-stem `.txt` **sibling**.

**The model (BACKLOG C1).** The sibling is the **primary grab** — a **VLM
page-image read**, a modality *uncorrelated* with OCR, so an OCR engine's
char-confusion cannot be silently reproduced by the grab. (The retired process
trusted one agent to produce the sibling and a second to "PASS" it — both read
the same image with the same kind of vision model and made the *same* misreads;
DIRD-16's sibling carried `III→ITT`, `communication→cammunication`, `81→82`,
`Klyshko→Kiyshko`, all certified PASS.)

Trust is **quote-scoped**, not whole-document: confirming every token of a
banner/figure-heavy PDF produces ~1000 CONTESTED spans, ~99% non-prose furniture
no quote ever draws from (DIRD-16: 1067 contested, 0 inside any of its 21 quotes).
So this skill *produces* the sibling; **grounding** confirms only the spans the
node quotes/cites — `ocr-consensus.py ground <artifact>` re-OCRs each cited source
with Tesseract + PaddleOCR, aligns to the sibling, and records per-span
confirmation in `{stem}-quote-grounding.yaml`, gated by
`scripts/checks/quote_source_grounding.py`. Grounding runs once the node has
quotes (step 5), not at prep time.

This is source **prep**, not node building — it produces a faithful transcription
of a primary source, never node content.

**Prerequisite:** PaddleOCR lives in `.venv-ocr/` — run
`scripts/tools/setup-ocr-consensus.sh` once (the user runs it; it `sudo apt`s a
few libs). `ocr-consensus.py run` / `ground` auto-relaunch under that venv.

---

1. **Confirm the need.** Read the source's manifest entry (`python3
   scripts/tools/manifest.py status {url}`, or grep `sources/manifest.yaml`).
   Proceed only if flagged `ocr-scan` / `extraction-lossy` AND no same-stem
   `.txt` sibling already exists as a trustworthy VLM grab. Note the parent URL
   (needed to register the pairing) and the page count (`pdfinfo`).

2. **Produce the VLM page-image read — per-page chunked.** This is the grab.
   Dispatch `Agent(general-purpose)` producers that read the source's page
   IMAGES (`Read` with `pages: "N"` — **one page at a time**) and **write each
   page to its own scratch file before reading the next** (e.g.
   `/tmp/{stem}/pNN.txt`, zero-padded). Per-page writes are load-bearing: the
   content filter blocks model *output* (reproducing a passage), and a block
   kills the agent turn — per-page isolation means a block costs one page, not
   the whole run, and the set of written files is a blocked-page ledger. Parallel
   producers can split disjoint page ranges; for ranges that die mid-block,
   dispatch one producer **per missing page** to find which pages block *in
   isolation*.

   Transcription discipline (per `meta/conventions.md` "Producing the `.txt`
   sibling"): reproduce body prose character-for-character including the
   document's own typos and spellings (do NOT correct); preserve redaction
   markers and banners verbatim; render equations/figures/diagram interiors as
   bracketed placeholders (`[Figure N: …]`); transcribe every physical page
   including any third-party FOIA / distribution cover-insert (e.g. a Black Vault
   page); reproduce TOC entries without dot-leader runs; no synthetic page-break
   markers.

   **Genuinely-blocked pages → Tesseract-fill.** For each page that blocks in
   isolation, rasterize that one page and fill its slice from Tesseract
   (`pdftoppm -png -r 300 -f N -l N … && tesseract page.png stdout --psm 1 -l
   eng > /tmp/{stem}/pNN.txt`). That degrades *those pages only* to the 2-engine
   regime (Tesseract grab + PaddleOCR cross-check at ground time) — confined and
   disclosed, not a whole-document fallback.

3. **Assemble the base + write the sibling.** Concatenate the per-page files in
   order (`cat /tmp/{stem}/p*.txt > /tmp/{stem}-vlm.txt`; zero-padding sorts
   correctly). Then:
   ```
   python3 scripts/tools/ocr-consensus.py run sources/{category}/{stem}.pdf \
       --vlm /tmp/{stem}-vlm.txt --date <YYYY-MM-DD> [--force]
   ```
   `run` writes the VLM base as the sibling `.txt`. (`--force` regenerates an
   existing sibling — backfill. Heed any `⚠ COVERAGE WARNING`: a large contiguous
   run of OCR-corroborated tokens missing from the base means the VLM dropped a
   paragraph/page — recover it before proceeding.)

4. **Register the paired manifest entry.**
   ```
   python3 scripts/tools/manifest.py add {parent_url}#clean-text-transcription \
       --path {category}/{stem}.txt --format txt --wayback-skip \
       --note "Clean-text sibling (VLM page-image grab) of the OCR-scanned
       <source>. Produced <date>; pages it blocked on the content filter
       Tesseract-filled (<list>). <FOIA/distribution insert preserved verbatim>.
       Equations/figures bracketed; redactions + source spellings preserved
       verbatim."
   ```
   `#clean-text-transcription` + `--wayback-skip` mark it derived and
   non-fetchable, paired to the parent PDF entry. Confirm with `manifest.py
   verify-paths`. **Do not list the sibling in any artifact's `primary_sources[]`**
   — the parent PDF is the primary source; the sibling is only the extraction
   surface. `extract-source.py` auto-prefers the sibling for OCR-scan sources, so
   quotes derive verbatim text from it but cite the PDF path in `source.path`.

5. **Ground the node's quotes (after the node has quotes).** Once the node is
   built, confirm what it draws from this source:
   ```
   python3 scripts/tools/ocr-consensus.py ground meta/research/{node}.yaml --date <YYYY-MM-DD>
   ```
   This re-OCRs the source (Tesseract + PaddleOCR), aligns to the sibling, locates
   each quote/cited_work span, and writes `{stem}-quote-grounding.yaml` — every
   span token confirmed by ≥1 OCR engine, or flagged CONTESTED. For each contested
   token (bounded to exactly the tokens an OCR engine disputed in a *quoted* span —
   typically a handful), an `Agent(general-purpose)` reads the page image at its
   `line`/`context` and fills `resolution` = **what the image shows** +
   `resolution_method: image-adjudication` + `adjudicator_session`, then re-run
   `ground` (it carries resolutions over). A resolution that *equals* the sibling
   token confirms the grab; one that *differs* means the grab is wrong — fix the
   sibling + the quote, then re-run. `quote_source_grounding.py` then passes:
   every quoted/cited span rests on two uncorrelated reads or a recorded image
   adjudication.

The sibling is canonical once registered; `extract-source.py` and the
verbatim-quote check prefer it. Hand back to `/build` (or the contributor) to
extract the clean scratch and run the Worker; grounding (step 5) gates the result.

## Note — the trust prerequisite

Quote-scoped grounding confirms the sibling's quoted spans against the OCR
engines. That guarantee holds only if the **grab (sibling) is uncorrelated with
the confirming OCR engines** — i.e. the sibling is a VLM read. A sibling produced
by the retired OCR-then-correct process shares Tesseract's failure mode, so an OCR
engine would rubber-stamp its errors; **regenerate such a sibling as a VLM read
(steps 2–3) before grounding.**
