---
name: prepare-ocr-sibling
description: Produce, independently verify, and register a clean-text .txt sibling for an OCR-scanned primary source. An OCR-scan source's pdftotext layer is corrupt, so verbatim quotes cannot be derived from it until a verified sibling exists. Use before building or quoting a source flagged extraction_type ocr-scan / extraction-lossy that has no sibling; /build step 4b directs here.
argument-hint: {category}/{filename}.pdf
allowed-tools:
  - Agent(general-purpose)
  - Read
  - Bash(python3 scripts/tools/manifest.py *)
---

# Prepare OCR-scan clean-text sibling

Target source: **$ARGUMENTS** — a path under `sources/` (e.g.
`government/foo.pdf`). Ask the user if empty.

An OCR-scanned source (manifest `extraction_type: ocr-scan` / `extraction-lossy`)
has a corrupt text layer: quotes pulled from it are garbage or trip the
verbatim-quote gate. Its canonical text is a same-stem `.txt` sibling, made
trustworthy by **independent verification** — the agent that produces it cannot
self-verify a hallucination (the failure mode is invisible to its author; see
`meta/conventions.md` "Producing the `.txt` sibling"). This skill runs that
producer → independent-verifier → register loop. It owns the build pipeline's
OCR-sibling-readiness prerequisite; `/build` step 4b directs here, and a
contributor can run it standalone.

This is source **prep**, not node building — it produces a faithful
transcription of a primary source, never node content. The independent
verification is the discipline gate, exactly as the verbatim-quote check is for
quotes.

1. **Confirm the need.** Read the source's manifest entry
   (`python3 scripts/tools/manifest.py status {url}`, or grep
   `sources/manifest.yaml` for the path). Proceed only if it is flagged
   `ocr-scan` / `extraction-lossy` AND no same-stem `.txt` sibling is already
   registered. If a verified sibling already exists, stop — there is nothing to
   do. Note the parent URL (you need it to register the pairing).

2. **Produce — `Agent(general-purpose)`.** Dispatch a producer to read the
   source's page IMAGES (the `Read` tool with `pages: "1-20"`, `"21-40"`, … —
   max 20 pages per request) and write the verbatim transcription to the
   same-stem `.txt` adjacent to the source. Per `meta/conventions.md`
   "Producing the `.txt` sibling": preserve redaction markers, the document's
   own typos, and source spellings exactly; render equations and figures as
   bracketed placeholders; transcribe the per-page classification banner and
   page numbers where they appear; EXCLUDE any third-party distribution / FOIA
   cover-insert page that is not part of the document itself (report which
   physical page was excluded). **Mark every document-page boundary with a line
   `----- PAGE BREAK -----`** (between pages — not before the first or after the
   last). Those markers delimit the sibling's pages: `extract_source_text`
   normalizes them to form feeds so `quote_location_page` can verify a quote's
   `p. N` against the Nth block (see `meta/conventions.md` "Quote location
   refs"). Without them, the sibling's `p. N` refs go unverified. The producer reports the load-bearing
   front-matter facts it captured and flags any faded / ambiguous / redacted
   spots where a vision model might hallucinate. **A flag records only what is
   legible** (`[unclear]`, `[illegible digit]`) — it must never assert an
   alternative reading, date, or name not actually visible in the image. A flag
   that invents specifics reintroduces the very hallucination it is meant to
   surface, and that error is invisible to its author — which is why the
   independent pass scrutinizes flagged spots, not just plain text.

3. **Independently verify — `Agent(general-purpose)`, a DIFFERENT session.**
   Dispatch a SEPARATE agent (independence is the whole point) to re-read the
   page images against the produced `.txt` and return either PASS or a list of
   `page N | .txt says "X" | image shows "Y"` discrepancies — scrutinizing the
   producer's flagged spots and the load-bearing front matter (title, dates,
   control numbers, author/redaction lines). The producer must not verify its
   own output. On FAIL, route the corrections back to a producer pass and
   re-verify; do NOT register until PASS.

4. **Register the paired manifest entry.** Once verified:
   ```
   python3 scripts/tools/manifest.py add {parent_url}#clean-text-transcription \
       --path {category}/{stem}.txt --format txt --wayback-skip \
       --note "Clean-text sibling of the OCR-scanned <source>. Produced <date>
       via multimodal page-image read; independently verified <date> by a
       separate agent session — PASS. <excluded insert page(s)>. Equations /
       figures bracketed; redactions + source spellings preserved verbatim."
   ```
   The `#clean-text-transcription` URL suffix + `--wayback-skip` mark it as a
   derived, non-fetchable artifact paired to the parent PDF entry. Confirm with
   `python3 scripts/tools/manifest.py verify-paths`.

The sibling is now canonical: `extract-source.py` and the verbatim-quote check
prefer it over the OCR-corrupted PDF text layer. Hand back to `/build` (or the
contributor) to extract the clean scratch and run the Worker.
