---
name: verify-transcript
description: Verify the quotes on a transcript node against the archived primary source (PDF, transcript file, or video caption) word-for-word, fix or remove any that don't match, and confirm speaker attribution. Use to verify a transcript or quote-heavy node.
argument-hint: {type}/{slug}
allowed-tools:
  - Skill(prepare-transcript-sibling)
  - Read
  - Edit
  - Bash(python3 scripts/build/validate.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/build-from-research.py *)
---

# Verify transcript

Target: **$ARGUMENTS** (ask the user if empty).

Confirmation against the source is a precondition for a quote's inclusion, not
a rendered marker — the source link is the evidence, and `validate.py` enforces
the match mechanically. This skill is the verification *work*: re-reading
quotes against sources and fixing or removing any that don't match.

1. Identify every `> blockquote` in `## Key Passages`.
2. Open the archived source referenced in the node (hearing PDFs in
   `sources/government/`; broadcast captions in `sources/transcripts/`).
3. For each quote, locate the passage (line numbers for hearing PDFs;
   timestamps for broadcast; pages for print) and compare word-for-word.
4. Act per category:
   - **Verbatim match** — no action.
   - **Punctuation / hyphenation drift** — update `quote.text` in the artifact
     to the source's form; regenerate.
   - **Paraphrase or composite** — not a quote: replace with the closest
     verbatim passage, or remove the entry. Never leave a paraphrase.
   - **Not in the source at all** — investigate: wrong citation (repoint),
     wrong appearance (move to the right transcript node), or fabricated
     (remove + surface to the user). Don't keep an unconfirmable quote.
   - **Auto-caption source-level artifact** (`transcript_provenance:
     auto-caption`) — distinct from the above: a name the captioner
     mis-transcribed (`Halverson` for `Halvorsen`, `Petrakis` for `Petrakos`)
     sits identically in the quote *and* the caption file, so the word-for-word
     check passes on a wrong word — the auto-caption blind spot. Screen suspect
     tokens (proper nouns, uncommon names, OCR-style cluster swaps `rn`↔`m` /
     `cl`↔`d`, phoneme-substitution drift) and flag any anomaly for confirmation
     against the **audio** — the caption can't confirm itself — surfacing it to
     the user when the recording is the only arbiter. Preserve the source form
     verbatim and register a confirmed artifact as a `naming_quirks` entry. A
     source with a clean spot-checked track record needs no blanket audio pass —
     the caption substring-match suffices; note the verification approach in the
     manifest.
5. When replacing an entry that differs substantively, preserve the original
   via `superseded_by` / `contradicted_by` pointers; typo fixes edit in place.
6. **Speaker attribution.** Each transcript quote carries a structural
   `speaker_id` → `speakers[*].id` (a single id, or a list of 2+ ids for a
   mixed exchange). The method follows the source format:
   - **Labeled source** (`stenographic` / `published-transcript`): take the
     speaker from the source's own labels and confirm the match against the
     caption file.
   - **Label-less source** (`auto-caption` / `human-corrected-caption`): the
     canonical attribution is the `-attribution.yaml` sibling produced by
     `/prepare-transcript-sibling`. If the source lacks a verified
     `-attribution.yaml` sibling, **invoke `/prepare-transcript-sibling {slug}`
     via the Skill tool — you are the main thread, so you can.** Only if
     your environment cannot dispatch a skill, **HALT** and direct the user
     to run it. Once registered, confirm each quote's `speaker_id` matches
     the sibling's `turns[]` at the quote's line range in the source file.
     Do **not** infer the speaker from surrounding caption text — that
     guesswork is what produces misattributions. Where a boundary genuinely
     can't be settled, use the mixed-exchange list form rather than
     fabricating a split.
   Fix a wrong `speaker_id` by editing `speakers[]` or `speaker_id` in the
   artifact and regenerating. The attribution sibling itself, plus the
   photo-identity-log image-verification backstop, live in
   `/prepare-transcript-sibling`; verify-transcript does not invoke them
   directly.

**Output:** a before/after diff per changed quote; a summary count (verbatim /
drift-corrected / replaced / removed + speaker_id fixes); then re-run
`validate.py {path}` + `validate-research.py meta/research/{slug}.yaml` to
confirm both the verbatim and speaker_id checks pass. Do not modify the source
file. The user commits.
