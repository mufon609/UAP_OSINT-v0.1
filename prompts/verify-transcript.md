# Verify transcript prompt

Paste into a Claude Code session to verify quotes on a transcript node
against the archived primary source (PDF, transcript file, or video
caption).

---

The target transcript node is: **{PATH}**  (ask the user if not specified)

Confirmation against the underlying primary source is a precondition
for a quote's inclusion in a node body, not a rendered marker. The
rendered output carries no Verified row; the source link IS the
evidence. The verbatim-quote check in `validate.py` enforces the
match mechanically. This prompt is for the verification work itself —
re-reading quotes against sources, fixing or removing any that
don't match. See `meta/conventions.md` for the principle.

Steps:

1. Open the node at `{PATH}`. Identify every `> blockquote` in
   `## Key Passages`.
2. Open the archived primary source file referenced in the node's
   `## Publication Record` table (field `Transcript URL` →
   `Transcript Verified` local path). Most hearing transcripts live in
   `sources/government/` as PDFs; broadcast transcripts live in
   `sources/transcripts/` as YouTube-caption markdown.
3. For each quote:
   - Extract the quote text from the node
   - Locate the passage in the archived source (use line numbers for
     hearing PDFs; timestamps for broadcast; pages for print)
   - Compare word-for-word
4. Categorize each finding and act:
   - **Verbatim match** — quote is exact. No action needed.
   - **Punctuation / hyphenation drift** — substantive text matches
     but punctuation or hyphenation differs. Update the quote in the
     research artifact (`research/{slug}.yaml`) to match the source's
     form; regenerate the node.
   - **Paraphrase or composite** — quote is not verbatim. Two options:
     replace with the closest verbatim passage from the source (edit
     `quote.text` in the artifact + regenerate), or remove the quote
     entirely (delete the entry from the artifact + regenerate). Do
     not leave a paraphrase in place — it would fail the verbatim-quote
     check and is in any case not a quote.
   - **Quote doesn't appear in source at all** — investigate. The
     source citation may be wrong (point at the right one), the quote
     may be from a different appearance (move it to the right
     transcript node), or the quote may be fabricated (remove it and
     surface to user). Don't silently keep an unconfirmable quote.
5. For any replacement of an existing quote, preserve the original
   via `superseded_by` / `contradicted_by` pointers (see
   `meta/conventions.md` Versioning) when the new entry differs
   substantively. Typo fixes and clarifications edit in place.

**Rules:**
- Do not modify the source file
- Do not let an unconfirmed quote ship — fix the artifact or remove
  the entry
- For hearing transcripts, cite by line number in the `Location` field
- For broadcast transcripts, cite by timestamp
- For print, cite by page

**Output:**
- Before-and-after diff for each quote that changed
- Summary count: verbatim / drift-corrected / replaced / removed
- Re-run `python3 scripts/validate.py {path}` to confirm the
  verbatim-quote check passes on every retained quote
- Commit with a message naming the transcript and the categories of
  change applied
