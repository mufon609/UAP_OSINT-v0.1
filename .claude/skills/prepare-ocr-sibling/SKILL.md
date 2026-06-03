---
name: prepare-ocr-sibling
description: Produce, cross-verify, and register a clean-text .txt sibling for an OCR-scanned primary source via uncorrelated multi-engine consensus. An OCR-scan source's pdftotext layer is corrupt, so verbatim quotes cannot be derived from it until a verified sibling exists. Use before building or quoting a source flagged extraction_type ocr-scan / extraction-lossy that has no sibling; /build step 4b directs here.
argument-hint: {category}/{filename}.pdf
allowed-tools:
  - Agent(general-purpose)
  - Read
  - Edit
  - Bash(python3 scripts/tools/ocr-consensus.py *)
  - Bash(python3 scripts/build/validate-ocr-sibling.py *)
  - Bash(python3 scripts/tools/manifest.py *)
---

# Prepare OCR-scan clean-text sibling (multi-engine consensus)

Target source: **$ARGUMENTS** — a path under `sources/` (e.g.
`government/foo.pdf`). Ask the user if empty.

An OCR-scanned source (manifest `extraction_type: ocr-scan` / `extraction-lossy`)
has a corrupt text layer: quotes pulled from it are garbage or trip the
verbatim-quote gate. Its canonical text is a same-stem `.txt` sibling.

**Why consensus, not a single verifier.** The old process trusted one agent to
produce the sibling and a second agent to "PASS" it. That failed silently — both
agents read the *same* page image with the *same* kind of vision model, so they
made the *same* misreads (DIRD-16's sibling carried `III→ITT`,
`communication→cammunication`, `81→82`, `Klyshko→Kiyshko`, all certified PASS).
The fix: **three votes with uncorrelated failure modes** —

  - **Tesseract** (LSTM OCR) — vote A,
  - **PaddleOCR** (deep-learning OCR, different architecture) — vote B,
  - **VLM page-image read** (an agent, different modality) — vote C.

A token is accepted (CONSENSUS) only when **≥2 of the 3 agree**. Anything the
votes disagree on is flagged CONTESTED and adjudicated against the page image,
and that adjudication is recorded in a durable
`{stem}-ocr-verification.yaml` (spec: `meta/schema-ocr-verification.yaml`; gated
by `scripts/build/validate-ocr-sibling.py`; bound per-quote by
`scripts/checks/quote_source_grounding.py`). A lone wrong read loses the vote
and is surfaced, never silently kept.

This is source **prep**, not node building — it produces a faithful
transcription of a primary source, never node content.

**Prerequisite:** PaddleOCR lives in `.venv-ocr/` — run
`scripts/tools/setup-ocr-consensus.sh` once (the user runs it; it `sudo apt`s a
few libs). `ocr-consensus.py run` auto-relaunches under that venv.

---

1. **Confirm the need.** Read the source's manifest entry (`python3
   scripts/tools/manifest.py status {url}`, or grep `sources/manifest.yaml`).
   Proceed only if flagged `ocr-scan` / `extraction-lossy` AND no same-stem
   `.txt` sibling is already registered with a FINALIZED verification record
   (run `validate-ocr-sibling.py` to check). Note the parent URL (needed to
   register the pairing).

2. **Produce vote C — the VLM page-image read.** `Agent(general-purpose)`.
   **Route check first:** if the source is plainly CBRN / weapons-design-
   sensitive (judge from title / TOC), SKIP the VLM vote — a model reproducing
   such a passage as its own tokens hard-terminates on the content filter. With
   the VLM skipped the consensus runs on Tesseract + PaddleOCR + image
   adjudication (still two uncorrelated OCR engines plus the human/agent image
   check); note this in the verification record's engines list. Otherwise,
   dispatch a producer to read the source's page IMAGES (`Read` with
   `pages: "1-20"`, `"21-40"`, … — max 20/request) and write the verbatim
   transcription to a scratch file (e.g. `/tmp/{stem}-vlm.txt`). Per
   `meta/conventions.md` "Producing the `.txt` sibling": preserve redaction
   markers, the document's own typos, and source spellings exactly; render
   equations/figures as bracketed placeholders; transcribe every physical page
   verbatim INCLUDING any third-party FOIA / distribution cover-insert (e.g. a
   Black Vault page); no synthetic `--- PAGE BREAK ---` markers (clean
   transcription). The VLM vote is now ONE of three — it no longer has to be
   perfect on its own, because the OCR engines cross-check it.

3. **Run the consensus.** `ocr-consensus.py` rasterizes, runs Tesseract +
   PaddleOCR, ingests the VLM text, aligns the three votes, writes the draft
   sibling (the VLM read is the readable base) and the verification YAML listing
   every CONTESTED span:
   ```
   python3 scripts/tools/ocr-consensus.py run sources/{category}/{stem}.pdf \
       --vlm /tmp/{stem}-vlm.txt --date <YYYY-MM-DD>
   ```
   (Add `--force` when regenerating an existing sibling — backfill.) Report the
   consensus/contested counts.

4. **Adjudicate the CONTESTED spans against the page images.** This is the only
   non-mechanical step, and it is bounded to exactly the tokens the engines
   disagreed on (where errors live), not the whole document. For each contested
   entry in `{stem}-ocr-verification.yaml`, an `Agent(general-purpose)` (or the
   contributor) reads the page image at that span's `line` / `context`, decides
   the correct reading, and `Edit`s the entry: set `resolution` to the verbatim
   surface form, `status: adjudicated`, `resolution_method: image-adjudication`,
   `adjudicator_session: <id>`. **The resolution records only what the image
   actually shows** — if it matches the corrupt pdftotext layer where an OCR
   engine disagreed, note it under `contamination_flags` for a second look (the
   "seeded from corrupt OCR" smell). Genuine document typos (a real misprint on
   the page) are preserved verbatim as the resolution — flag them as the
   document's own, not corrected.

5. **Assemble + validate.**
   ```
   python3 scripts/tools/ocr-consensus.py assemble sources/{category}/{stem}-ocr-verification.yaml
   python3 scripts/build/validate-ocr-sibling.py --quiet
   ```
   `assemble` splices the resolutions into the sibling and stamps its sha256
   into the record; the validator confirms the record is FINALIZED (every
   contested span adjudicated, engines ≥2 OCR + VLM, sibling hash matches). On
   any failure, fix the data and re-run — do not hand-edit the sibling `.txt`
   (its bytes are bound to the record's hash).

6. **Register the paired manifest entries.** Once validated, register the
   sibling (and confirm the verification YAML is tracked):
   ```
   python3 scripts/tools/manifest.py add {parent_url}#clean-text-transcription \
       --path {category}/{stem}.txt --format txt --wayback-skip \
       --note "Clean-text sibling of the OCR-scanned <source>. Produced <date>
       via 3-engine consensus (Tesseract + PaddleOCR + VLM page-image read);
       N contested span(s) image-adjudicated; record:
       {stem}-ocr-verification.yaml. <FOIA/distribution insert preserved
       verbatim>. Equations/figures bracketed; redactions + source spellings
       preserved verbatim."
   ```
   The `#clean-text-transcription` URL suffix + `--wayback-skip` mark it as a
   derived, non-fetchable artifact paired to the parent PDF entry. Confirm with
   `python3 scripts/tools/manifest.py verify-paths`.

   **Do not list the sibling's path in any artifact's `primary_sources[]`** —
   the parent PDF is the primary source; the sibling is only the extraction
   surface. `extract-source.py` auto-prefers the sibling for OCR-scan sources,
   so quotes derive verbatim text from it but cite the PDF path in
   `source.path`.

The sibling is now canonical and trustworthy: `extract-source.py` and the
verbatim-quote check prefer it, and `quote_source_grounding` binds every quote
to the finalized, hash-matching record. Hand back to `/build` (or the
contributor) to extract the clean scratch and run the Worker.

## Fallback — when the VLM vote is blocked by the API content filter

If the VLM producer (step 2) trips the model provider's generative content
filter (`API Error: Output blocked by content filtering policy` — it blocks the
model *reproducing* a sensitive passage, not reading the page), skip vote C for
the affected source and run the consensus on Tesseract + PaddleOCR alone, with
image adjudication resolving their disagreements. Two uncorrelated OCR engines +
recorded image adjudication still satisfies the ≥2-OCR-engine floor; the
verification record's engines list omits `vlm` and the validator accepts it
(the `min_ocr_engines: 2` invariant is what guarantees no token rests on a
single read). Note the omission in the record and the manifest note. For a span
where even an adjudication note would force reproducing a long sensitive
passage, fall back to a human reading that one span.
