---
name: prepare-transcript-sibling
description: Produce, independently verify, and register a speaker-attribution sibling for a label-less primary-source transcript (auto-caption — incl. Whisper-class machine output — or human-corrected-caption without speaker labels). The caption file carries verbatim text but no speaker labels; speaker_id on transcript-artifact quotes cannot be derived from it until a verified attribution sibling exists. Uses the agent-based attribution pipeline (semantic parse → structural validate → independent verify → mandatory active-speaker fold gate at finalize for video sources). The photo-identity-log baselines + mouth-motion engine decide who is SPEAKING, not who is on camera. Use before building or quoting a transcript flagged transcript_provenance auto-caption / human-corrected-caption that has no sibling; /build step 4c directs here.
argument-hint: {transcript-slug}
allowed-tools:
  - Agent(general-purpose)
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

A label-less transcript (manifest `transcript_provenance: auto-caption` /
`human-corrected-caption` without inline speaker labels) carries the verbatim
text but **no built-in speaker attribution**: `speaker_id` on transcript-
artifact quotes cannot be derived from the caption file alone. The canonical
attribution is a **same-stem sibling YAML** indexing into the source file by
1-indexed line range — see `meta/schema-speaker-attribution.yaml`. Produced
by a semantic-parse agent, validated by a structural gate script,
independently verified by a separate agent session, and — for a video source —
**gated at finalize by a systematic active-speaker spot-check across every
turn** (§4b; a `contested-fold` blocks finalize). The agent does the patient
text-parsing; the image gate mechanically catches the boundary call that is
confidently wrong and slips past the text verifier.

**Why agent-based, not a mechanical audio pipeline:** corpus test
(2026-05-28, see `meta/BACKLOG.md` A2 "Test-evidence accumulated") showed
agents catch failure modes a mechanical turn-finder cannot — document
recitation mid-conversation, prepared-statement reading, narrator vs
in-room-speaker distinction — that a mechanical turn-finder cannot. The agent
pass is the attribution *spine*. The Yes Theory / Grusch documentary scan made
the failure mode concrete: a naive mechanical face-vote across that transcript
would have silently misattributed ~22 minutes of host narration to the
whistleblower as first-person experiential claims — which is why the image gate
(§4b) decides who is SPEAKING (mouth-motion), not who is on camera. For a video
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

- `transcript_provenance ∈ {auto-caption, human-corrected-caption}` — the
  label-less classes. **Skip entirely** for `stenographic` /
  `published-transcript` sources; their bytes carry speaker labels and
  only the verbatim-quote check applies. Skip also if a same-stem
  `{slug}-attribution.yaml` is already registered (the sibling exists).
- The source file is on disk at `sources/transcripts/{stem}*.{md,txt}`.
- `wc -l` the source file to capture its line count — the producer needs
  it for `source_line_count` and the validator uses it for the coverage
  check. Drift = source changed underneath the sibling = re-run.

Note the parent manifest URL (the registration step needs it).

## 2. Producer — `Agent(general-purpose)`.

Dispatch a producer agent to read the source transcript and emit a draft
attribution YAML at `/tmp/attribution-{slug}/{stem}-attribution.yaml`.

The producer's brief includes:

- Path to the source transcript and the exact `source_line_count`.
- Path to `meta/schema-speaker-attribution.yaml` (the contract).
- The single hard rule: **emit line ranges only, never quote source
  text in turn entries**. The schema has no `text` field on `turn_entry`;
  the validator will fail if the agent invents one or tries to inline
  text. The output is references, not transcript.
- **`line_range` values MUST be quoted YAML strings.** Write `"82"` for
  a single line and `"82-99"` for a range — both with surrounding double
  quotes. YAML otherwise parses bare `82` as an integer, which the
  validator rejects with `malformed; expected 'N' or 'N-M'`. This is
  the easiest single mistake to make and the most common producer-side
  validator failure.
- For each turn entry, produce: `speaker_id` (defined-id `s1`/`s2`/...,
  a `foreign-*` kind, or a 2+-element mixed-exchange list), `line_range`
  (`N` or `N-M`), `confidence` (high/medium/low), and `rationale` (the
  textual cue the boundary rests on; required when confidence < high,
  or when speaker_id is foreign-* or mixed-exchange).
- For `foreign-recitation` / `foreign-archival` turns: add
  `referenced_source` (free-text identifier of the recited document or
  the embedded archival source).
- For any turn whose boundary the producer flags as genuinely
  unresolvable from text alone *AND* where the audio anchor would add
  evidence (alternating dialogue with face on camera at the contested
  moment): set `needs_image_verification: true` and use `low`
  confidence. **DO NOT** flag topic-shift boundaries that careful reread
  settles — image verification is for audio-anchor-dependent turns, not
  for "I'm not sure" turns where the textual cue is actually present.
  Default-to-medium-with-rationale beats default-to-low-plus-flag.
- **Coverage discipline:** every line in `[1, source_line_count]`
  covered by exactly one turn entry, no gaps, no overlaps. The
  validator enforces.
- **Each line is an atomic unit assigned wholly to one turn.** Auto-
  caption transcripts frequently pack a turn-end + turn-start onto
  the same `[MM:SS]` line (sub-line speaker transitions). The line-
  range schema cannot represent this — every line goes to exactly one
  turn. When a sub-line transition is the dominant content boundary,
  assign the contested line to the speaker who *dominates* its content
  and document the choice in `rationale`. **Do not emit overlapping
  ranges and clean them up after** — the validator will catch overlaps,
  but cleaning them costs ~3× the emission cost. Decide the
  attribution at emission time.
- **Reported speech belongs to the reporting speaker.** When speaker A
  says "they told me 'we'd like to consider you...'", the quoted
  recruiter's words are part of speaker A's turn, not a separate turn
  for the recruiter. The recruiter is not a live in-room participant;
  their quoted speech is *narrated* by A. Same rule applies to
  recounting prior conversations, citing what someone said in a
  meeting, etc. Do NOT split a monologue into "speaker A" + "quoted
  party" + "speaker A continues"; it's one continuous A turn.
- **Multiple substantive other-speaker interjections downgrade
  confidence to medium.** A 50-line Elizondo monologue with 3 brief
  Rogan questions embedded is `s2` by dominant attribution, but
  confidence should be `medium`, not `high` — the boundary cleanliness
  is overstated by `high`. Single-line "yeah" / "right" acks don't
  trigger this rule (they're conversational glue); substantive
  questions that materially shape the response do.
- Speakers in `speakers[]`: all live in-room participants, with
  `on_camera_role` ∈ {primary, voiceover, mixed, off-camera}. **A
  documentary host who narrates over interview footage is a speaker
  with `on_camera_role: voiceover`, NOT foreign-narration** — the
  foreign-* prefix is reserved for content whose AUTHOR is outside
  the live participant set (jingles, archival third-party clips,
  recited documents from non-present authors).
- Output goes to `/tmp/attribution-{slug}/{stem}-attribution.yaml`.
  Producer never writes to `sources/`.

The producer reports the agent session id (for `producer_session` in
the YAML) and an end-of-run summary: total turns, kind breakdown,
how many turns marked `needs_image_verification`, and any structural
notes (transcript is a hybrid podcast/documentary format, etc.).

## 3. Structural validator — `validate-speaker-attribution.py`.

Mechanical gate; no LLM. Runs the 13-check chain from
`scripts/build/validate-speaker-attribution.py`:

```
python3 scripts/build/validate-speaker-attribution.py \
    /tmp/attribution-{slug}/{stem}-attribution.yaml
```

Exit 0 = structural pass; the verifier sees a well-formed file. Any
FATAL routes back to the producer with the specific error (e.g.,
`turns[12].line_range: gap before line 478`) — producer fixes,
re-runs validator, iterates until clean. Common producer-side fixes
the validator catches: coverage gaps/overlaps, unknown speaker ids,
mixed-exchange list with foreign-*, missing rationale on low-conf
turns. Do NOT proceed to verification until the validator returns
clean.

## 4. Independent verifier — `Agent(general-purpose)`, DIFFERENT session.

Dispatch a SEPARATE agent (independence is the discipline) to re-check
the producer's YAML against the source transcript. The verifier sees
the source file + the YAML + the schema; they do NOT see the producer's
internal reasoning.

The verifier's specific scrutiny targets:

- Every `confidence: low` turn — does the rationale hold up? Is there
  a better attribution from textual cues the producer missed?
- Every `confidence: medium` turn — could the boundary be high-
  confidence with a sharper rationale, OR was it actually low?
- Every `foreign-*` turn — is the kind correct? (foreign-narration
  on a documentary host is the classic miscall — the host IS a
  speaker; the verifier should re-label as a `voiceover`-role
  speaker entry.)
- Every mixed-exchange turn — is it really unresolvable, or is the
  producer being lazy? (mixed-exchange is the honest marker, not a
  license to skip work where turns are cleanly separable.)
- A sample of `confidence: high` turns — spot-check that the
  producer's high-confidence calls hold up against actual reading.

**Hard rule: content-check on BOTH sides of every turn boundary, not
just transition-cue confirmation.** When checking a boundary at line N,
the verifier must:

1. Read the actual content of the LAST few lines of the prior turn,
2. Read the actual content of the FIRST few lines of the new turn,
3. Confirm that the *content* on each side matches the assigned
   speaker_id — not just that some transition-cue word appears
   somewhere near line N.

The failure mode this rule blocks: the producer mis-places a boundary
(e.g., assigns lines 26-38 to s1 when those lines are actually s2's
answer); a verifier scanning for "the question-end cue" finds it at
line 38 and stamps PASS without reading the s1-labeled span. The
verifier's mind has the *correct content text* but reads the *wrong
line numbers* from the YAML, and the contradiction goes unflagged.
This bit the 2026-05-28 mysterywire run (see manifest note on
transcripts/mysterywire-lacatski-kelleher-knapp-2021-attribution.yaml).
**If you cite a verbatim text snippet from the source as evidence in
your verdict, the line number of that snippet must match the producer's
line_range for the turn you're confirming. Cross-check the line number
against the actual source file, not against the producer's rationale
prose.**

The verifier returns:
- **PASS** — the orchestrator finalizes **through the active-speaker fold gate**:
  `python3 scripts/build/finalize-attribution.py {draft}.yaml
  --verifier-session {id} --video sources/video/{recording}` (or `--no-video`
  ONLY for a genuinely audio-only source). Finalize first runs the
  active-speaker spot-check across EVERY turn (§4b); any `contested-fold`
  BLOCKS finalize and routes back to producer/verifier — no graceful skip. On a
  clean gate it sets `verification_status:
  verified` + `verifier_session` AND **strips the verification scaffolding**:
  every turn's `rationale` + `verifier_notes` + `needs_image_verification`, and
  the top-level `verifier_notes`. The committed sibling is structured-only —
  `rationale` did its job (gave the verifier a cue to check) and
  `needs_image_verification` did its (routed the turn to step 4b); on a verified
  sibling they're dead scaffolding that renders into / clutters the `.md`, so
  they're removed. The
  structural validator then FATALs if any scaffolding remains, so the strip is
  enforced, not optional. (`confidence: low|medium` stays as the durable
  uncertainty marker — alongside any `image_verification[]` resolution; an
  investigator reads the source lines to judge a boundary.) Do NOT hand-edit the YAML to strip — use the tool (no 40-field
  agent edit → no mangling).
- **REJECT** — sets `verification_status: rejected` with
  `verifier_notes: |\n  <correction list>` enumerating each turn
  that needs revision and why. Route back to producer; do NOT
  register a rejected sibling. (rationale/verifier_notes are kept while
  rejected — the producer needs them to fix.)

The verifier never asserts speaker identities from outside the source
text — they're checking the producer's read of the same evidence, not
introducing new evidence.

## 4b. Image verification — the MANDATORY pre-finalize active-speaker fold gate.

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

What the gate decides — **who is SPEAKING, not who is on camera.** It samples a
per-turn frame burst, resolves WHO each on-screen face is (dlib embeddings via
`detect-faces.py`) and WHICH face is talking (`active-speaker.py` mouth-motion),
and folds only when another identified speaker is the active speaker over a
long-enough window. Framing false-positives (two-shots, reaction cutaways,
voiceover, brief turns) are absorbed by the dominance + active-speaker +
duration guards, so a `contested-fold` is a *likely wrong label*. Verdicts that
do NOT block — recorded honestly, never a pass-by-omission: `confirmed` /
`confirmed-with-footnote`, `honestly-unverified` (off-camera/voiceover speaker,
or no on-camera speaker), `inconclusive`, `no-baseline` (e.g. a moderator with
no baseline), `contested-other` (b-roll/archival identity).

On a `contested-fold` (gate blocked):
1. Read the turn's source lines + the spot-check note (which identity is the
   active speaker) and confirm against the transcript text.
2. Relabel the turn's `speaker_id` to the correct speaker (or split it / mark a
   mixed exchange), and record an `image_verification[]` entry
   (`resolution: corrected`, `resolved_speaker_id`, `resolved_by: agent-verifier`;
   use `resolution: ambiguous` + `resolved_by: contributor` when a human must
   adjudicate).
3. Re-run `validate-speaker-attribution.py`, then re-run finalize — the gate
   must come back clean (0 `contested-fold`) before the sibling is verified.

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

## 5. Register + render.

Once `verification_status: verified`, two artifacts land in the repo:

1. **The YAML sibling** at `sources/transcripts/{stem}-attribution.yaml`
   via manifest:
   ```
   python3 scripts/tools/manifest.py add \
       {parent_url}#speaker-attribution \
       --path transcripts/{stem}-attribution.yaml --format yaml \
       --wayback-skip \
       --note "Speaker-attribution sibling of the label-less transcript
       at {original_path}. Produced YYYY-MM-DD via /prepare-transcript-
       sibling (agent-based). Verified YYYY-MM-DD by a separate agent
       session — PASS. Image-verification: {none | N turns resolved
       against photo-identity-log baselines}."
   ```
2. **The human-readable rendering** at `sources/transcripts/{stem}-
   attributed.md`, generated deterministically by the renderer:
   ```
   python3 scripts/tools/render-speaker-transcript.py \
       sources/transcripts/{stem}-attribution.yaml \
       --output sources/transcripts/{stem}-attributed.md
   ```
   Same `#speaker-attribution` parent + `--wayback-skip` on its
   manifest entry. The rendered .md is a derived view; the YAML is
   the source-of-truth.

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
