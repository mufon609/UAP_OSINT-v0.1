---
name: prepare-transcript-sibling
description: Produce, independently verify, and register a speaker-attributed transcript sibling for a label-less primary source (auto-caption / Whisper / human-corrected-caption without speaker labels). The auto-caption file carries the verbatim text but no speaker labels, so speaker_id on quotes cannot be derived from it until a verified attribution sibling exists. Use before building or quoting a transcript flagged transcript_provenance auto-caption / human-corrected-caption that has no sibling; /build step 4c directs here.
argument-hint: {transcript-slug}
allowed-tools:
  - Agent(general-purpose)
  - Read
  - Bash(python3 scripts/tools/manifest.py *)
  - Bash(python3 scripts/tools/download-video.py *)
  - Bash(python3 scripts/tools/diarize-audio.py *)
  - Bash(python3 scripts/tools/extract-frames.py *)
  - Bash(python3 scripts/tools/detect-faces.py *)
  - Bash(python3 scripts/tools/stitch-transcript.py *)
---

# Prepare speaker-attributed transcript sibling

Target transcript: **$ARGUMENTS** — the slug used by the existing auto-caption
file at `sources/transcripts/{slug}*.{txt,md}`. Ask the user if empty.

A label-less transcript (manifest `transcript_provenance: auto-caption` /
`human-corrected-caption` without inline speaker labels) carries the verbatim
text but **no built-in speaker attribution**: `speaker_id` on quotes cannot be
derived from the caption file alone — only by anchoring each segment against
the underlying recording (`meta/conventions.md` "Speaker attribution: source
format selects the method"). The canonical attribution is a same-stem
speaker-labeled sibling, produced by the 5-step video pipeline + **independently
verified by a different agent** — the producer cannot self-verify a
mis-registered baseline (the failure mode is invisible to its author; the same
shape as the OCR-sibling discipline, see `meta/conventions.md` "Auto-caption
transcripts ... mirrors `ocr-scan`"). This skill runs that producer →
independent-verifier → register loop. It owns the build pipeline's
transcript-sibling-readiness prerequisite; `/build` step 4c directs here, and a
contributor can run it standalone.

This is source **prep**, not node building — it produces a faithful
attribution overlay for an existing primary source, never node content. The
independent verification is the discipline gate, exactly as the verbatim-quote
check is for quotes. **One structural difference from the OCR sibling:** the
auto-caption file remains the verbatim source `validate.py` matches `quote.text`
against; the sibling adds the **speaker-attribution layer** that
`validate-research.py` matches `speaker_id` against. The two artifacts coexist
(OCR sibling, by contrast, replaces a corrupt text layer).

1. **Confirm the need + classify the source.** Read the transcript's manifest
   entry (`python3 scripts/tools/manifest.py status {url}`, or grep
   `sources/manifest.yaml`). Proceed only if `transcript_provenance ∈
   {auto-caption, human-corrected-caption}` (label-less classes) AND no
   same-stem `-stitched.md` sibling is already registered. **Skip the pipeline**
   if the source is `stenographic` / `published-transcript` — speakers are in
   the source's own labels and only the verbatim-quote check applies. Pick the
   method per `scripts/tools/VIDEO-PIPELINE.md` Step 0: **image path** for video
   with visible faces, **audio path** for audio-only. Note the parent URL (you
   need it to register the pairing).

2. **Produce the speaker-labeled stitched transcript — `Agent(general-purpose)`.**
   Walk the 5-step video pipeline (full procedure + dependency gating:
   `scripts/tools/VIDEO-PIPELINE.md`):
   - `download-video.py URL --slug {slug}` — ensure `sources/video/{slug}.mp4`
     exists (idempotent; skip-on-exists).
   - `diarize-audio.py sources/video/{slug}.mp4` (audio path / multi-speaker
     mystery) — identity-blind `SPEAKER_NN` segments at
     `/tmp/diarize-{slug}/segments.csv`.
   - `extract-frames.py anchor --video sources/video/{slug}.mp4` — 8 anchor
     frames to establish each speaker's visual identity; add `burst` at
     contested timestamps as needed.
   - `detect-faces.py detect --index /tmp/frames-{slug}/index.md` — surfaces
     crops at `sources/photo-identity-log/crops/`.
   - `detect-faces.py register --crop {file} --identity {kebab-slug}
     --source-video sources/video/{slug}.mp4 --source-timestamp MM:SS
     --bbox X,Y,W,H` — promote each unambiguous identification to a baseline.
     The producer is making identity judgments from visual evidence; this is
     exactly where the next step scrutinizes. **A flag records only what the
     evidence supports** (`[no clear match]`, `[split-screen ambiguity]`); never
     assert an identity not confirmed by the frames. When the producer cannot
     identify a face at all (obscure speaker, model unfamiliarity), flag for
     contributor input rather than guess.
   - `stitch-transcript.py sources/video/{slug}.mp4` — merges video + diarize
     segments + baselines, writes `/tmp/stitch-{slug}/stitched.md` with a
     speaker-resolution table (confidence per `SPEAKER_NN`: `high` / `medium` /
     `low` / `none`) + body labeled at every turn boundary. The producer reports
     the resolution table and lists every speaker that resolved below `high`
     (the script's `⚠ Manual review required` banner).

3. **Independently verify — `Agent(general-purpose)`, a DIFFERENT session.**
   Dispatch a SEPARATE agent (independence is the whole point) to re-check
   every below-`high` resolution + every turn boundary the producer flagged,
   against the source frames (image path) or the diarize anchor evidence
   (audio path). The producer cannot self-verify a mis-registered baseline.
   Return PASS, or a list of `[MM:SS] | stitched says SPEAKER_NN → identity-A |
   image/audio shows identity-B`. The verifier specifically scrutinizes: every
   `medium` (split-screen ambiguity), `low` (no single identity dominated), and
   `none` (no baseline match) resolution, plus any baseline whose `--identity`
   the producer assigned from visual judgment alone (a misregistration silently
   propagates to every quote whose timestamp falls in that speaker's
   segments). On FAIL, route the corrections back to a producer pass —
   re-register the corrected baseline (or unregister + supersede), re-stitch,
   re-verify; do NOT register until PASS.

4. **Register the paired manifest entry.** Once verified, promote the stitched
   output from `/tmp/stitch-{slug}/stitched.md` to
   `sources/transcripts/{stem}-stitched.md`, then:
   ```
   python3 scripts/tools/manifest.py add {parent_url}#speaker-attributed-transcript \
       --path transcripts/{stem}-stitched.md --format md --wayback-skip \
       --note "Speaker-attributed sibling of the label-less transcript at
       {original_path}. Produced <date> via the video pipeline
       (scripts/tools/VIDEO-PIPELINE.md): {image|audio} path, baselines
       registered: {identity-1, identity-2, ...}. Independently verified
       <date> by a separate agent session — PASS. Below-`high` resolutions
       reviewed against {frames|diarize anchors}."
   ```
   The `#speaker-attributed-transcript` URL suffix + `--wayback-skip` mark it
   as a derived, non-fetchable artifact paired to the parent auto-caption
   entry. Confirm with `python3 scripts/tools/manifest.py verify-paths`.

## Downstream

The sibling is now canonical for `speaker_id`: `validate-research.py` matches
each transcript-artifact quote's `speaker_id` against the sibling's attribution
at the quote's timestamp. The verbatim layer is unchanged — the auto-caption
file remains the source `validate.py` matches `quote.text` against, and
`extract-source.py --artifact` still pulls from it. Hand back to `/build` (or
the contributor) to run the Worker on the auto-caption file with confidence
that `speaker_id` is now grounded.
