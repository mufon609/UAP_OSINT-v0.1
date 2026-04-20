# Verify transcript prompt

Paste into a Claude Code session to verify quotes on a transcript node
against the archived primary source (PDF, transcript file, or video
caption).

---

The target transcript node is: **{PATH}**  (ask the user if not specified)

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
4. Report findings by category:
   - ✅ **Verbatim match** — quote is exact; mark `✅ Confirmed — verified
     verbatim against archived PDF`
   - ✏️ **Punctuation / hyphenation drift** — substantive text matches
     but punctuation or hyphenation differs; update the node to the
     source's version and note the correction
   - ❌ **Paraphrase or composite** — quote is not verbatim; propose a
     replacement using the closest verbatim passage from the source
5. For any replacement, preserve the original quote in the node's Node
   Versioning subsection (or Key Passages with a `Supersedes` note),
   never silently overwrite.
6. If the `Verified` field was `⏳ Pending`, upgrade to `✅ Confirmed`
   once verbatim is established. If the quote doesn't exist in the
   source at all, flag the node for a deeper review and surface to user.

**Rules:**
- Do not modify the source file
- Do not upgrade `Verified` without actually checking against source
- For hearing transcripts, cite by line number in the `Location` field
- For broadcast transcripts, cite by timestamp
- For print, cite by page

**Output:**
- Before-and-after diff for each quote
- Summary count: verbatim / drift-corrected / paraphrase-replaced / missing
- Commit with a message like "Verify /transcripts/{slug} quotes against archived PDF"
