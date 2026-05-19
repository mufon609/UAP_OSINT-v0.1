# Video pipeline — speaker disambiguation workflow

This pipeline supports **transcript verification on multi-speaker video sources**.
Whisper and YouTube auto-caption transcripts don't preserve speaker identity.
When a source has multiple people on camera — panel discussion, moderated
interview, documentary with intercut interviews — a single transcript line may
belong to any of them. This pipeline lets a contributor visually confirm
who-is-who before quoting material in entity-node Statements / Key Passages.

Where the pipeline fits in the repo: contributor diagnostic tooling, not part
of the build pipeline. It gates the discipline of "every quote attributed to
a person actually came from that person" — same evidentiary discipline that
the verbatim-quote check enforces mechanically, but for sources where the
speaker isn't stamped in the transcript itself.

## Companion workflow — caption-only archival

For YouTube sources you also want the auto-caption transcript registered as
a primary source for the verbatim-quote check. That's a separate, lighter
workflow covered in `meta/sources-access.md` "YouTube (youtube.com)" —
cookies-authenticated `transcribe.py` → `manifest.py add ... --format
transcript --transcript-provenance auto-caption`. Run it BEFORE step 1
below so the caption file is already in place when `stitch-transcript.py`
runs at step 5.

**Slug discipline.** Use the same `--slug` for `transcribe.py` and
`download-video.py` on a single source. `stitch-transcript.py`'s
auto-discovery looks for the caption file at
`sources/transcripts/{slug}-downloaded.md` and the diarize segments at
`/tmp/diarize-{slug}/segments.csv` — slugs that drift across tools break
the auto-discovery silently.

---

## One-time setup

```
bash scripts/tools/setup-photo-identity.sh
bash scripts/tools/setup-diarize-audio.sh    # only if using diarize-audio.py
```

`setup-photo-identity.sh` installs and verifies the visual-side pipeline:

| Dependency | Purpose | Install path |
|---|---|---|
| `python3-opencv` | Haar cascade face detection | apt |
| `opencv-data` | Cascade XML files | apt |
| `yt-dlp` | Video download | pip / apt |
| `ffmpeg`, `ffprobe` | Frame extraction, merge, duration probe | apt |
| JS runtime (`deno` / `node` / `bun`) | yt-dlp's EJS challenge solver | varies |

`setup-diarize-audio.sh` covers the audio-side optional step:

| Dependency | Purpose | Install path |
|---|---|---|
| `pyannote.audio` + `torch` + `torchaudio` | Speaker diarization model | pip |
| Hugging Face user-conditions (manual) | pyannote/speaker-diarization-3.1 + pyannote/segmentation-3.0 are gated | hf.co browser click |
| `HF_TOKEN` env var | Auth for the pipeline download | shell export |

Both scripts report missing pieces and exit non-zero if any apt / pip step
fails. Re-runnable.

---

## Five-step pipeline

Each step is one command. Defaults are tuned for the common case; flags exist
for tuning when needed.

Steps 1–4 produce three independent artifacts (video, diarize segments,
identity baselines). Step 5 merges them into a single speaker-labeled
transcript the contributor uses when populating `speaker_id` on transcript-
artifact quotes.

### 1. Download the source video

```
python3 scripts/tools/download-video.py URL --slug NAME
```

Example:

```
python3 scripts/tools/download-video.py \
    "https://www.youtube.com/watch?v=dnnpyNuPdXs" \
    --slug american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs
```

Output:

- `sources/video/{slug}.mp4` — the downloaded file (~300-500 MB for 1-3 hour
  videos at 480p)
- `sources/manifest.yaml` — new entry registered via `manifest.py add` with
  format: video, sha256, archive bits

Idempotent. Re-running with the same `--slug` skips the download if the file
already exists; still re-runs the manifest registration (which is itself
idempotent).

Common tunables:

- `--quality 720` for higher facial detail (file size scales ~2-3×)
- `--note "STR"` to attach contributor context to the manifest entry
- `--dry-run` to inspect the yt-dlp invocation without running

### 1.5. (Optional) Diarize the audio — discover speaker turns

```
python3 scripts/tools/diarize-audio.py sources/video/{slug}.mp4
python3 scripts/tools/diarize-audio.py sources/video/{slug}.mp4 --start 19:00 --end 22:00
```

Identity-blind speaker diarization via `pyannote/speaker-diarization-3.1`.
Output is two files in `/tmp/diarize-{slug}/` (or `--out DIR`):

- `segments.csv` — `start_seconds, end_seconds, duration_seconds, speaker`
  one row per detected turn. Speaker labels are anonymous
  (`SPEAKER_00`, `SPEAKER_01`, ...) — pyannote answers "this voice is
  different from that voice," not "this is X."
- `segments.md` — human-readable summary: per-speaker total speech time +
  percentage, chronological segment list with `[HH:MM:SS]` anchors, and a
  per-speaker view for jumping to a specific speaker's appearances.

When to run it:

- **Unfamiliar source**: you don't know how many people speak or when they
  trade off. Diarize first to see "3 speakers, SPEAKER_01 dominates
  18:00–32:00, SPEAKER_02 enters at 47:00" — then targeted extract-frames
  at those handoffs.
- **Narration vs. on-camera speech**: a video-only frame at a contested
  timestamp can't tell you whether a voice belongs to someone on camera
  or to off-frame narration. Diarization + frames together resolve this:
  if SPEAKER_NN persists across cuts where the on-camera person changes,
  it's narration.
- **Skip it** for short, two-speaker, well-known sources where you can
  identify speakers from the frames directly.

Slow on CPU — diarization runs at roughly real-time, so a 3-hour video
takes ~3 hours. Use `--start` / `--end` to slice the analyzed range to
the contested passage.

### 2. Extract frames at contested timestamps

```
# Anchor frames — 8 timestamps spread across the video's duration
# (5%, 15%, 25%, 35%, 50%, 65%, 80%, 95%) to establish each speaker's
# visual identity. Override with --timestamps "MM:SS,MM:SS,..." when you
# know where the body interview is.
python3 scripts/tools/extract-frames.py anchor --video sources/video/{slug}.mp4

# Burst at specific timestamps — 5 frames over 2 seconds per timestamp, tiled
# into a single contact-sheet jpg. Mouth motion across the burst distinguishes
# active speech from listening from B-roll narration.
python3 scripts/tools/extract-frames.py burst \
    --video sources/video/{slug}.mp4 \
    --timestamps "44:53,45:00,45:09,45:20"
```

Output lands at `/tmp/frames-{slug}/` with an `index.md` listing every
extraction by timestamp + path. Other modes:

- `sweep --from MM:SS --to MM:SS --every N` — periodic burst across a range
- `transcript --transcript PATH --every N` — burst at each `[MM:SS]` caption
  tick (or every Nth)

### 3. Detect faces in the extracted frames

```
# Process every contact sheet listed in the index
python3 scripts/tools/detect-faces.py detect \
    --index /tmp/frames-{slug}/index.md

# Or process a single directory of images
python3 scripts/tools/detect-faces.py detect \
    --input /tmp/frames-{slug}/anchor/
```

For each detected face, the tool saves a 256×256 jpg crop to
`sources/photo-identity-log/crops/` (skipping near-duplicates via perceptual
hash). Summary reports counts: faces detected, deduplicated, identified
(meaning: pHash matched against an existing baseline crop).

### 4. Register clear baselines

After visually reviewing crops in `sources/photo-identity-log/crops/`, register
the ones that are unambiguous identifications:

```
python3 scripts/tools/detect-faces.py register \
    --crop sources/photo-identity-log/crops/{file}.jpg \
    --identity {kebab-slug} \
    --source-video sources/video/{slug}.mp4 \
    --source-timestamp MM:SS \
    --bbox X,Y,W,H \
    --note "context"
```

The bbox values come from `sources/photo-identity-log/index.csv` (which the
`detect` step populates). Identity slugs are kebab-case (e.g.,
`jake-barber`, `jesse-michels`); multiple baselines per identity are
encouraged — register different poses/angles as `ref_01.jpg`, `ref_02.jpg`,
etc.

The `register` command:

1. Moves the crop from `crops/` to `baselines/{identity}/ref_NN.jpg`
2. Computes sha256
3. Appends an entry to `sources/photo-identity-log/manifest.yaml` with full
   provenance (source video path, timestamp, bbox)

Future `detect` runs will identify new crops against the accumulating
baseline set — when an unambiguous baseline pHash-matches a freshly-detected
face in a new frame, the tool reports it as identified rather than queuing
it as an unlabeled crop.

### Maintenance: prune unidentified crops

```
python3 scripts/tools/detect-faces.py prune          # interactive
python3 scripts/tools/detect-faces.py prune --dry-run
python3 scripts/tools/detect-faces.py prune --force  # no prompt
```

Removes crops in `crops/` whose pHash matches no baseline — i.e., unlabeled
faces the contributor has decided not to keep. Removed crops leave git
history but no longer in HEAD.

### 5. Stitch the auto-caption transcript with speaker labels

```
python3 scripts/tools/stitch-transcript.py sources/video/{slug}.mp4
```

Prereqs: steps 1, 1.5, and 4 above must have completed (video file,
diarize `segments.csv`, and at least one identity baseline registered),
plus an auto-caption transcript downloaded via `transcribe.py` at
`sources/transcripts/{slug}-downloaded.md`. Auto-discovery looks for
the segments at `/tmp/diarize-{slug}/segments.csv` and the transcript at
the `-downloaded.md` (or equivalent) path; pass `--diarize-segments` /
`--transcript` to override.

For each diarize segment, extracts a frame at the segment's midpoint,
runs face detection, pHash-matches against `baselines/`. Aggregates the
matches per anonymous speaker label and writes:

- `/tmp/stitch-{slug}/stitched.md` — header carries the speaker-resolution
  table with confidence rating per speaker; transcript body has the
  speaker label rendered at every turn boundary (consecutive lines from
  the same speaker are not re-labeled). Unanalyzed regions (caption ticks
  outside the diarize range) and unresolved speakers (no baseline match)
  are marked explicitly so the contributor sees the coverage gaps.
- `/tmp/stitch-{slug}/speaker-map.csv` — machine-readable rollup of the
  same speaker resolutions.
- `/tmp/stitch-{slug}/frames/` — per-segment midpoint frames kept so the
  contributor can spot-check any speaker assignment that surfaced below
  `high` confidence.

Confidence ratings the script emits:

- `high`   — single identity dominates this speaker's segment-frame
             matches AND no other speaker also resolves to the same
             identity (single-camera coverage with clean switching).
- `medium` — single identity dominates but matches are partial, OR the
             same identity also dominates another speaker (split-screen
             ambiguity; visual baseline alone can't tell which face is
             actively speaking).
- `low`    — speaker had visual matches but no single identity dominated.
- `none`   — no baseline matches at all in this speaker's segments
             (frame was a graphic overlay, no face detected, or face
             pHash exceeded the threshold against every baseline).

A `⚠ Manual review required` banner fires whenever any speaker resolves
below `high`. The contributor uses the stitched output to populate the
`speaker_id` field on each transcript-artifact quote — and overrides any
medium / low / none speaker resolution before relying on it.

The output is contributor-diagnostic only; it lands in `/tmp/` and is
not manifest-registered. The downloaded transcript at
`sources/transcripts/{slug}-downloaded.md` remains the verbatim source
the validator's verbatim-quote check verifies against. The stitched
file is what a human reads to figure out who said what.

---

## Cookies — when, why, and the dangerous form

YouTube blocks unauthenticated downloads on many residential and VPN IPs.
`download-video.py` handles this via:

```
yt-dlp --cookies-from-browser firefox ...
```

yt-dlp reads cookies **directly from Firefox's profile in memory** — no
cookies file ever touches disk. This is the canonical and safe form.

**Do NOT use `--cookies -`** as the cookies flag value to yt-dlp. The `-`
gets interpreted as a literal filename, and yt-dlp writes refreshed cookies
*back* to that path after the run completes. We learned this the hard way
during the Michels-Barber download — a file named `-` containing live
session credentials was created in the working directory.

For tools without a `--cookies-from-browser` equivalent (e.g.,
`scripts/tools/transcribe.py` driving the YouTube captions API):

```
scripts/tools/extract-firefox-cookies.py --accept-risks | \
    scripts/tools/transcribe.py URL --cookies -
```

`transcribe.py` internally wires the stdin cookies through to yt-dlp via
`--cookies /dev/stdin` — a real filesystem path the kernel maps to file
descriptor 0, which yt-dlp opens read-only and can't write back to. The
bare `-` form would fail; `/dev/stdin` is the Linux-specific safe form.

`extract-firefox-cookies.py` itself keeps cookies in memory (stdout) and
never writes to disk. The danger is downstream tools that misinterpret
`-` as a file path.

**Strong recommendation:** use a burner Google account for YouTube cookies.
Live session credentials grant full access to whatever Google identity is
logged in.

### Pre-commit safety net

The `cookies-check` pre-commit gate scans staged content for Netscape
cookies / Google session credentials. `.gitignore` excludes common cookie
filenames including the bare `-` variant. Together they catch accidental
cookie file commits.

---

## End-to-end example

The Michels-Barber documentary, end to end:

```
# Setup (one time)
bash scripts/tools/setup-photo-identity.sh

# Download
python3 scripts/tools/download-video.py \
    "https://www.youtube.com/watch?v=dnnpyNuPdXs" \
    --slug american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs

# Anchor frames for speaker identity baselines
python3 scripts/tools/extract-frames.py anchor \
    --video sources/video/american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs.mp4 \
    --timestamps "0:15,1:00,5:00,10:00,20:00,45:00,1:30:00,2:30:00"

# Detect faces in anchors
python3 scripts/tools/detect-faces.py detect \
    --input /tmp/frames-american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs/anchor/

# Register two baselines (bbox values from sources/photo-identity-log/index.csv)
python3 scripts/tools/detect-faces.py register \
    --crop sources/photo-identity-log/crops/10-00_face_01.jpg \
    --identity jesse-michels \
    --source-video sources/video/american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs.mp4 \
    --source-timestamp 10:00 --bbox 296,63,156,156

python3 scripts/tools/detect-faces.py register \
    --crop sources/photo-identity-log/crops/1-30-00_face_01.jpg \
    --identity jake-barber \
    --source-video sources/video/american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs.mp4 \
    --source-timestamp 1:30:00 --bbox 386,51,159,159

# Re-detect — now identification fires on the baselines
python3 scripts/tools/detect-faces.py detect \
    --input /tmp/frames-american-alchemy-barber-ufo-helicopter-2026-dnnpyNuPdXs/anchor/

# Prune unlabeled crops (interactive)
python3 scripts/tools/detect-faces.py prune
```

---

## When to use which tool

| Tool | When |
|---|---|
| `setup-photo-identity.sh` | First time on a machine, or when adding the video pipeline to an existing checkout |
| `setup-diarize-audio.sh` | First time using the audio-side speaker-diarization step (separate from the visual-side setup) |
| `download-video.py` | Archiving a new video source that needs face detection |
| `diarize-audio.py` | Unfamiliar long source — discover how many speakers exist and when they trade off, before pointing extract-frames at handoff timestamps; also useful for distinguishing on-camera speech from off-frame narration |
| `extract-frames.py anchor` | First-time on a video — establish visual identity of each on-camera speaker |
| `extract-frames.py burst` | Speaker disambiguation at a specific contested transcript timestamp |
| `extract-frames.py sweep` | Visual map of an unfamiliar source |
| `extract-frames.py transcript` | Exhaustive frame coverage matching every caption tick |
| `detect-faces.py detect` | After any extract-frames run, to find faces in the extracted frames |
| `detect-faces.py register` | After reviewing a crop, to promote it to a persistent baseline |
| `detect-faces.py prune` | Periodic cleanup of unidentified crops |
| `stitch-transcript.py` | After steps 1, 1.5, 4, and a `transcribe.py` run on the video — bridges the three independent artifacts (video, diarize segments, baselines) into a speaker-labeled transcript for populating `speaker_id` on transcript-artifact quotes |
| `extract-firefox-cookies.py` | Only when piping cookies into a tool that doesn't support `--cookies-from-browser` (e.g., `transcribe.py`) |
