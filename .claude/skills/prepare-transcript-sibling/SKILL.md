---
name: prepare-transcript-sibling
description: Produce, independently verify, and register a speaker-attribution sibling for a label-less primary-source transcript (auto-caption — incl. Whisper-class machine output — or human-corrected-caption without speaker labels). The caption file carries verbatim text but no speaker labels; speaker_id on transcript-artifact quotes cannot be derived from it until a verified attribution sibling exists. Uses the agent-based attribution pipeline (semantic parse → structural validate → independent verify → mandatory active-speaker fold gate at finalize for video sources). The photo-identity-log baselines decide WHO each face is; mouth-motion decides who is SPEAKING where the face is large enough to carry that signal, presence/dominance decides elsewhere. Use before building or quoting a transcript flagged transcript_provenance auto-caption / human-corrected-caption that has no sibling; /build step 4c directs here.
argument-hint: {transcript-slug}
allowed-tools:
  - Agent(attribution-producer, attribution-verifier)
  - Read
  - Bash(python3 scripts/build/validate-speaker-attribution.py *)
  - Bash(python3 scripts/build/finalize-attribution.py *)
  - Bash(python3 scripts/tools/render-speaker-transcript.py *)
  - Bash(python3 scripts/tools/manifest.py *)
  - Bash(python3 scripts/tools/extract-frames.py *)
  - Bash(python3 scripts/tools/detect-faces.py *)
  - Bash(python3 scripts/tools/download-video.py *)
  - Bash(wc -l *)
---

# Prepare speaker-attribution sibling (agent-based)

Target transcript: **$ARGUMENTS** — the slug used by the existing auto-caption
file at `sources/transcripts/{slug}*.{txt,md}`. Ask the user if empty.

**Source timestamp format — check before parsing.** The source transcript's
inline `[…]` timestamps must be the corpus-canonical grammar:
**un-padded leading field**, `[M:SS]` under an hour, `[H:MM:SS]` at/over an
hour (`scripts/tools/transcribe.py::format_timestamp` is the reference) —
never zero-padded `[MM:SS]` / `[HH:MM:SS]`. YouTube captions via
`transcribe.py` already conform; a transcript produced by another path (an
external **Whisper** run for a non-YouTube source — the common case here —
or a different downloader) must be normalized to this format *before* it
lands in `sources/transcripts/`, because the producer's `line_range` parse
and every downstream quote `[MM:SS]` anchor mirror the source verbatim.
Three legacy files (`lucistrust-rending-veils-ryder-2017`, `nell-salt-2024`,
`nell-sol-foundation-2023`) predate this convention and zero-pad; they are
grandfathered — do not retro-edit them (their timestamps are baked into
machine-computed `source_content_hash` + research-artifact anchors).

A label-less transcript (manifest `transcript_provenance: auto-caption` /
`human-corrected-caption` without inline speaker labels) carries the verbatim
text but **no built-in speaker attribution**: `speaker_id` on transcript-
artifact quotes cannot be derived from the caption file alone. The canonical
attribution is a **same-stem sibling YAML** indexing into the source file by
1-indexed line range — see `meta/schema-speaker-attribution.yaml`. Produced
by a semantic-parse agent, validated by a structural gate script,
independently verified by a separate agent session, and — for a video source —
**gated at finalize by a systematic active-speaker spot-check across every
turn** (§5; a `contested-fold` blocks finalize). The agent does the patient
text-parsing; the image gate mechanically catches the boundary call that is
confidently wrong and slips past the text verifier.

**Why agent-based, not a mechanical audio pipeline:** a 2026-05-28 corpus
test (recorded in git history) showed
agents catch failure modes a mechanical turn-finder cannot — document
recitation mid-conversation, prepared-statement reading, narrator vs
in-room-speaker distinction. The agent
pass is the attribution *spine*. The Yes Theory / Grusch documentary scan made
the failure mode concrete: a naive mechanical face-vote across that transcript
would have silently misattributed ~22 minutes of host narration to the
whistleblower as first-person experiential claims — which is why the image gate
(§5) decides who is SPEAKING (mouth-motion), not who is on camera. For a video
source that gate is a mandatory finalize step, so the dlib engine + the source
recording are prerequisites at finalize (not at draft time). (The earlier
diarize+stitch pipeline this replaced was removed once the agent pass proved
out.)

**Structural verbatim guarantee.** Agents emit references to line ranges
in `source_path`; they never quote source text in their output. The
schema enforces this (no `text` field on `turn_entry`). The renderer
reads source bytes verbatim by line range. There is no code path from
agent output to the rendered sibling that could alter source text — the
verbatim-quote chain that `validate.py` defends is structurally intact.

**One structural difference from the OCR sibling:** the auto-caption file
remains the verbatim source `validate.py` matches `quote.text` against;
the sibling YAML adds the speaker-attribution overlay that
`validate-research.py` matches `speaker_id` against — the
`speaker_attribution_consistency` check (scripts/checks/) resolves each
quote's `[MM:SS]` anchor to the sibling's covering turn and confirms the
attributed speaker agrees. The two artifacts coexist; OCR sibling, by
contrast, replaces a corrupt text layer.

## 1. Confirm the need + classify the source.

Read the transcript's manifest entry (`python3 scripts/tools/manifest.py
status {url}`, or grep `sources/manifest.yaml`). Proceed only if:

- `transcript_provenance ∉ {stenographic, published-transcript}` — the
  label-less classes (`auto-caption` / `human-corrected-caption`), plus an
  explicit `unknown` or an absent flag: an unclassified transcript is
  treated as label-less. Determine and set its real provenance via
  `manifest.py edit` while here, then proceed unless it turned out to be
  one of the labeled classes. **Skip entirely** for `stenographic` /
  `published-transcript` sources; their bytes carry speaker labels and
  only the verbatim-quote check applies. Skip also if a same-stem
  `{slug}-attribution.yaml` is already registered (the sibling exists).
- The source file is on disk at `sources/transcripts/{stem}*.{md,txt}`.
- `wc -l` the source file to capture its line count — the producer needs
  it for `source_line_count` and the validator uses it for the coverage
  check. Drift = source changed underneath the sibling = re-run.

Note the parent manifest URL (the registration step needs it).

## 2. Producer — `Agent(attribution-producer)`.

Dispatch the producer with, and only: the source transcript path, the exact
`source_line_count`, the schema path (`meta/schema-speaker-attribution.yaml`),
and the output path `.scratch/drafts/attribution-{slug}/{stem}-attribution.yaml`. The
parse discipline (line-ranges-only, quoted `line_range` scalars, coverage,
reported speech, interjection confidence, `on_camera_role`, …) is the agent
contract's (`.claude/agents/attribution-producer.md`) — do not re-author it
into the dispatch (the relay/contract split; `/build` states the same rule
for this sub-skill's agents).

Read back: the producer's session id (for `producer_session` in the YAML) and
its end-of-run summary — total turns, kind breakdown, how many turns marked
`needs_image_verification`, structural notes (hybrid podcast/documentary
format, etc.).

## 3. Structural validator — `validate-speaker-attribution.py`.

Mechanical gate; no LLM. Runs the full structural check chain from
`scripts/build/validate-speaker-attribution.py` (the validator's own
docstring is the authoritative, numbered list of what it enforces):

```
python3 scripts/build/validate-speaker-attribution.py \
    .scratch/drafts/attribution-{slug}/{stem}-attribution.yaml
```

Exit 0 = structural pass; the verifier sees a well-formed file. Any
FATAL routes back to the producer with the specific error (e.g.,
`turns[12].line_range: gap before line 478`) — producer fixes,
re-runs validator, iterates until clean. Common producer-side fixes
the validator catches: coverage gaps/overlaps, unknown speaker ids,
mixed-exchange list with foreign-*, missing rationale on low-conf
turns. Do NOT proceed to verification until the validator returns
clean.

## 4. Independent verifier — `Agent(attribution-verifier)`, DIFFERENT session.

Dispatch a SEPARATE agent (independence is the discipline) with, and only:
the source transcript path, the draft YAML path, and the schema path — never
the producer's internal reasoning. The scrutiny discipline (per-confidence
targets, foreign-* re-checks, the both-sides boundary content-check, the
line-number cross-check) is the agent contract's
(`.claude/agents/attribution-verifier.md`); the verifier is Read-only and
reports a verdict — it edits nothing.

The verifier returns:
- **PASS** — the orchestrator finalizes **through the active-speaker fold gate**:
  `python3 scripts/build/finalize-attribution.py {draft}.yaml
  --verifier-session {id} --video sources/video/{recording}` (or `--no-video`
  ONLY for a genuinely audio-only source). Finalize first runs the
  active-speaker spot-check across EVERY turn (§5); any `contested-fold`
  BLOCKS finalize and routes back to producer/verifier — no graceful skip. On a
  clean gate it sets `verification_status:
  verified` + `verifier_session` AND **strips the verification scaffolding**:
  every turn's `rationale` + `verifier_notes` + `needs_image_verification`, and
  the top-level `verifier_notes`. The committed sibling is structured-only —
  `rationale` did its job (gave the verifier a cue to check) and
  `needs_image_verification` did its (routed the turn to §5); on a verified
  sibling they're dead scaffolding that renders into / clutters the `.md`, so
  they're removed. The
  structural validator then FATALs if any scaffolding remains, so the strip is
  enforced, not optional. (`confidence: low|medium` stays as the durable
  uncertainty marker — alongside any `image_verification[]` resolution; an
  investigator reads the source lines to judge a boundary.) Do NOT hand-edit the YAML to strip — use the tool (no 40-field
  agent edit → no mangling).
- **REJECT** — the verifier reports a correction list enumerating each
  turn that needs revision and why (the verifier is Read-only; it sets
  nothing). Relay the list verbatim to a re-dispatched producer, which
  revises the draft — recording the list as `verifier_notes: |` and
  `verification_status: rejected` on the draft while it iterates — then
  re-run the validator and a fresh verification. Do NOT register a
  rejected sibling. (rationale/verifier_notes are kept while rejected —
  the producer needs them to fix.)

The verifier never asserts speaker identities from outside the source
text — they're checking the producer's read of the same evidence, not
introducing new evidence.

## 5. Image verification — the MANDATORY pre-finalize active-speaker fold gate.

**Not optional, not gated by the producer's self-doubt.** `finalize-attribution.py
--video` runs `spot-check-attribution.py` across EVERY turn of a video-source
sibling; a `contested-fold` verdict BLOCKS finalize and routes back. **No
graceful skip:** a sibling whose source has a recording cannot be finalized
unless the spot-check actually runs (video + `.venv-face` present). `--no-video`
is the explicit, honest opt-out for a genuinely audio-only source — not a way
to skip a check that could have run.

Why systematic, not flag-gated: the failure mode is a producer boundary call
that is *confidently wrong* and passes the independent verifier — exactly the
call that never raises a self-doubt flag. So the image check must run on ALL
turns, not only the ones the producer flagged. (`needs_image_verification` is
now draft-only scaffolding, stripped on finalize; the systematic spot-check is
the gate.)

What the gate decides — **who is SPEAKING where the footage can show it, who
is consistently on camera elsewhere.** It samples a per-turn frame burst and
resolves WHO each on-screen face is (dlib embeddings via `detect-faces.py`).
Mouth-motion (`active-speaker.py` MAR) decides the verdict only where it is
*admissible* — faces of at least `MAR_MIN_FACE` px, because measured at
podcast resolutions a listener's landmark jitter is indistinguishable from
speech; below that floor the verdict is the presence/dominance test (a fold =
the assigned speaker NEVER seen while exactly one other transcript speaker is
seen consistently over a long-enough, non-silent window). Framing
false-positives (two-shots, reaction cutaways, voiceover, brief turns) are
absorbed by the dominance + duration + audio guards — but the engine can
still mis-fire, so a `contested-fold` means *either a wrong label or an
engine miss*; a frame read settles which. The honest limitation below the
admissibility floor: a wrong label with both speakers continuously on camera
(grid layout) is invisible to this gate — the independent text-side verifier
carries that case. Verdicts that
do NOT block — recorded honestly, never a pass-by-omission: `confirmed` /
`confirmed-with-footnote`, `honestly-unverified` (off-camera/voiceover speaker,
or no on-camera speaker), `inconclusive`, `no-baseline` (e.g. a moderator with
no baseline), `contested-other` (b-roll/archival identity).

On a `contested-fold` (gate blocked):
1. Settle the turn **from the frames** (`extract-frames.py` at the turn's
   timestamps + `detect-faces.py` against the photo-identity-log baselines),
   reading the turn's source lines + the spot-check note (which identity the
   engine says is the active speaker). The judgment of who is speaking is
   yours/the contributor's; the write is the tool's:
2. Apply the adjudication **mechanically** — records the structured
   `image_verification[]` entry (the schema's durable fold-settlement record)
   and, for `corrected`/`ambiguous`, relabels the turn's `speaker_id`, in one
   validated write (dry run first, then `--write`; `--resolution confirmed`
   when the frames show the existing label is right and the engine mis-fired;
   a mixed exchange takes `--speaker s1,s2`; use `--resolution ambiguous
   --resolved-by contributor` when a human must adjudicate):
   ```
   python3 scripts/build/finalize-attribution.py {draft}.yaml \
       --resolve-turn {line_range} --speaker s2 \
       --resolution corrected --resolved-by agent-verifier --write
   ```
   Never hand-edit the draft YAML for this — the tool validates the turn
   exists, the ids are in `speakers[]`, and the resolution agrees with the
   relabel (agents judge; scripts mutate).
3. Re-run `validate-speaker-attribution.py`, then re-run finalize. The gate
   honors the recorded adjudication: a contested-fold turn whose
   `image_verification[]` entry still matches the turn's `speaker_id` is
   reported as *settled* (resolution + resolver printed, never silent) and
   does not block; the gate blocks only on unadjudicated folds and on stale
   entries (turn relabeled after adjudication — re-adjudicate). A frame-level
   adjudication outranks the engine heuristic; the engine is the systematic
   screen, the recorded frame read is the settlement.

Setup the gate needs: the source recording on disk
(`download-video.py {parent_url} --slug {slug}`) and the dlib engine
(`.venv-face/`, via `setup-face-embeddings.sh`). If either is missing the gate
cannot run and finalize refuses — that IS the no-graceful-skip rule, not a bug.

**Residual — sub-line transitions.** When a turn-end and the next turn-start
are packed onto one `[MM:SS]` line, the line-range schema cannot split them;
assign the line to the speaker who dominates its content (`confidence: medium`)
and rely on this gate to catch the worst cases. A turn that is genuinely a fast
two-speaker exchange takes a mixed-exchange `[s1, s2]` label, which the gate
treats as crosstalk (not a fold).

## 6. Register + render.

Once `verification_status: verified`, two artifacts land in the repo:

1. **Render the human-readable view first** at `sources/transcripts/{stem}-
   attributed.md`, generated deterministically by the renderer:
   ```
   python3 scripts/tools/render-speaker-transcript.py \
       sources/transcripts/{stem}-attribution.yaml \
       --output sources/transcripts/{stem}-attributed.md
   ```
   The rendered .md is a derived view; the YAML is the source-of-truth.
2. **Register both on the manifest in one call — mechanically:**
   ```
   python3 scripts/tools/manifest.py add-sibling speaker-attribution \
       --parent-path transcripts/{original_stem}.md \
       --verified YYYY-MM-DD --verify-session {verifier_session_id} \
       --image-verification "none (mandatory active-speaker fold gate clean
       — 0 contested-fold across N turns) | N turns resolved against
       photo-identity-log baselines" \
       [--details "<iteration specifics, e.g. draft r3>"]
   ```
   The tool derives the anchor URL (`{parent_url}#speaker-attribution`),
   `wayback_skip`, both sibling paths from the parent stem (the `.yaml`
   source-of-truth AND the rendered `.md` — the pair is registered atomically,
   never one forgotten), and both note skeletons — and **errors if the parent
   isn't registered or either file is missing on disk**, so the pairing is
   checked, not remembered.

Confirm with `python3 scripts/tools/manifest.py verify-paths`.

**Do not list either sibling's path in any artifact's
`primary_sources[]`** — the parent caption file is the primary source;
the YAML adds the speaker-attribution overlay, the .md is a rendering
of that overlay over source bytes. `validate.py` continues matching
`quote.text` against the parent (unchanged verbatim layer);
`validate-research.py` matches each quote's `speaker_id` against the
sibling YAML (the `speaker_attribution_consistency` check, resolving the
quote's `[MM:SS]` anchor to the sibling's covering turn).

## Downstream

The sibling is now canonical for `speaker_id` on transcript-artifact
quotes. The verbatim layer is unchanged — the auto-caption file
remains the source `validate.py` matches `quote.text` against, and
`extract-source.py --artifact` still pulls from it. Hand back to
`/build` (or the contributor) to run the Worker on the auto-caption
file with confidence that `speaker_id` is now grounded against the
sibling.

The photo-identity-log baselines accumulated through any
image-verification turns remain useful corpus-wide — every registered
identity makes future transcripts' image-verification paths cheaper.
That asset is preserved across the pipeline switch; agent-based
attribution doesn't deprecate it, it just stops requiring it as a
hard prerequisite on every transcript.
