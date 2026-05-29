---
name: prepare-transcript-sibling
description: Produce, independently verify, and register a speaker-attribution sibling for a label-less primary-source transcript (auto-caption / Whisper / human-corrected-caption without speaker labels). The caption file carries verbatim text but no speaker labels; speaker_id on transcript-artifact quotes cannot be derived from it until a verified attribution sibling exists. Uses the agent-based attribution pipeline (semantic parse → structural validate → independent verify → conditional image-verification backstop). Photo-identity-log stays the human-in-the-loop visual audit trail. Use before building or quoting a transcript flagged transcript_provenance auto-caption / human-corrected-caption that has no sibling; /build step 4c directs here.
argument-hint: {transcript-slug}
allowed-tools:
  - Agent(general-purpose)
  - Read
  - Bash(python3 scripts/build/validate-speaker-attribution.py *)
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
by a semantic-parse agent, validated by a structural gate script, and
independently verified by a separate agent session. **Photo-identity-log
visual baselines stay the conditional backstop** for turns the producer
can't resolve from text alone (and for any contributor who wants to spot-
check) — humans stay in the loop where they add value (visual identification),
agents do the patient text-parsing.

**Why agent-based, not the old diarize+stitch pipeline:** corpus test
(2026-05-28, see `meta/BACKLOG.md` A2 "Test-evidence accumulated") showed
agents catch failure modes the mechanical pipeline cannot — document
recitation mid-conversation, prepared-statement reading, narrator vs
in-room-speaker distinction — in minutes vs hours of CPU + zero
prerequisites (no HF_TOKEN, no `.venv-diarize`, no `setup-photo-identity.sh`
unless image-verification is actually invoked). The Yes Theory / Grusch
documentary scan made the failure mode concrete: a mechanical face-vote
across that transcript would have silently misattributed ~22 minutes of
host narration to the whistleblower as first-person experiential claims.
The mechanical scripts remain — see "Image verification" below — as a
targeted backstop, not the spine.

**Structural verbatim guarantee.** Agents emit references to line ranges
in `source_path`; they never quote source text in their output. The
schema enforces this (no `text` field on `turn_entry`). The renderer
reads source bytes verbatim by line range. There is no code path from
agent output to the rendered sibling that could alter source text — the
verbatim-quote chain that `validate.py` defends is structurally intact.

**One structural difference from the OCR sibling:** the auto-caption file
remains the verbatim source `validate.py` matches `quote.text` against;
the sibling YAML adds the speaker-attribution overlay that
`validate-research.py` matches `speaker_id` against (cross-validator is a
future scripts/checks/ module per schema-speaker-attribution.yaml::"Cross-
schema integration points"). The two artifacts coexist; OCR sibling, by
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
- **PASS** — sets `verification_status: verified`, adds
  `verifier_session: {id}` to the YAML.
- **REJECT** — sets `verification_status: rejected` with
  `verifier_notes: |\n  <correction list>` enumerating each turn
  that needs revision and why. Route back to producer; do NOT
  register a rejected sibling.

The verifier never asserts speaker identities from outside the source
text — they're checking the producer's read of the same evidence, not
introducing new evidence.

## 4b. Image verification (CONDITIONAL — only for `needs_image_verification: true`).

For any turn the producer marked `needs_image_verification: true`, the
photo-identity-log machinery resolves the ambiguity against actual
frames. **This step is optional and gated by the producer's flagging
discipline** — most transcripts won't trigger it. When triggered:

1. Ensure the source video is on disk:
   `python3 scripts/tools/download-video.py {parent_url} --slug {slug}`
   (idempotent; skip-on-exists). Skip if the source is audio-only.
2. For each flagged turn's first line, derive the `[MM:SS]` timestamp
   from the source line, then `python3 scripts/tools/extract-frames.py
   burst --video sources/video/{slug}.mp4 --timestamps MM:SS`.
3. `python3 scripts/tools/detect-faces.py detect --index
   /tmp/frames-{slug}/burst-MM-SS/index.md` — matches against
   `sources/photo-identity-log/baselines/`.
4. Outcomes:
   - **Clean baseline match:** agent verifier records an
     `image_verification[]` entry with `resolution: confirmed` (or
     `corrected` if the image evidence overrides the producer's
     attribution) and updates the corresponding turn's `speaker_id`
     and confidence.
   - **No clear match, or multiple plausible matches:** **prompt the
     contributor**. Surface the extracted crops + the producer's
     attribution. Contributor makes the call; record as
     `resolution: ambiguous` with `resolved_by: contributor` and
     `contributor_notes`. This is the human-in-the-loop path.
5. After all flagged turns are resolved, re-run the structural
   validator (the YAML now has updated turns + an `image_verification[]`
   list).

If `setup-photo-identity.sh` hasn't run (system OpenCV missing),
`detect-faces.py` errors with the install pointer. The skill does NOT
treat that as a blocker — it routes the affected turns to manual
contributor review instead. The image path is the backstop, not the
prerequisite.

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
sibling YAML at the quote's line range.

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
