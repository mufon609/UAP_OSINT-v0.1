---
name: verify-transcript
description: Verify the quotes on a transcript node against the archived primary source (PDF, transcript file, or video caption) word-for-word, fix or remove any that don't match, and confirm speaker attribution. Use to verify a transcript or quote-heavy node.
argument-hint: {type}/{slug}
allowed-tools:
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
5. When replacing an entry that differs substantively, preserve the original
   via `superseded_by` / `contradicted_by` pointers; typo fixes edit in place.
6. **Speaker attribution.** Each transcript quote carries a structural
   `speaker_id` → `speakers[*].id` (a single id, or a list of 2+ ids for a
   mixed exchange). The method follows the source format — see
   `meta/conventions.md` "Speaker attribution: source format selects the
   method":
   - **Labeled source** (`stenographic` / `published-transcript`): take the
     speaker from the source's own labels and confirm the match.
   - **Label-less source** (`auto-caption` / Whisper): do **not** infer the
     speaker from surrounding text — that guesswork is what produces
     misattributions. Confirm against the recording per
     `scripts/tools/VIDEO-PIPELINE.md` Step 0: the image path (frames at the
     quote's timestamp matched to a face baseline, human-verified) where video
     exists, else the audio path (diarize + anchor). Where a boundary genuinely
     can't be settled, use the mixed-exchange list form rather than fabricating
     a split.
   Fix a wrong `speaker_id` — adding a `speakers[]` entry, or registering a face
   baseline (`detect-faces.py register`), first when needed — and regenerate.

**Output:** a before/after diff per changed quote; a summary count (verbatim /
drift-corrected / replaced / removed + speaker_id fixes); then re-run
`validate.py {path}` + `validate-research.py meta/research/{slug}.yaml` to
confirm both the verbatim and speaker_id checks pass. Do not modify the source
file. The user commits.
