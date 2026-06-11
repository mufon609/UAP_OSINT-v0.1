# Video pipeline — speaker disambiguation workflow

This pipeline supports **transcript verification on multi-speaker video sources**.
Whisper and YouTube auto-caption transcripts don't preserve speaker identity.
When a source has multiple people on camera — panel discussion, moderated
interview, documentary with intercut interviews — a single transcript line may
belong to any of them. This pipeline lets a contributor visually confirm
who-is-who before quoting material in entity-node Statements / Key Passages.

Where the pipeline fits in the repo: it is the canonical procedure the
`/prepare-transcript-sibling` skill invokes — the orchestrator's
sibling-readiness gate at `/build` step 4c for any label-less transcript
primary source. The steps below are also runnable manually as a contributor
diagnostic. The pipeline gates the discipline of "every quote attributed to
a person actually came from that person" — same evidentiary discipline that
the verbatim-quote check enforces mechanically, but for sources where the
speaker isn't stamped in the transcript itself.

## Companion workflow — caption-only archival

For YouTube sources you also want the auto-caption transcript registered as
a primary source for the verbatim-quote check. That's a separate, lighter
workflow covered in `meta/sources-access.md` "YouTube (youtube.com)" —
cookies-authenticated `transcribe.py` → `manifest.py add ... --format
transcript --transcript-provenance auto-caption`. The caption file is the
verbatim source the attribution sibling labels; register it before attributing
speakers.

**Slug discipline.** Use the same `--slug` for `transcribe.py` and
`download-video.py` on a single source, so the caption file at
`sources/transcripts/{slug}-downloaded.md` and the video at
`sources/video/{slug}.mp4` line up by name.

---

## One-time setup

This tooling is **optional** — a fresh contributor needs it only when
attributing speakers on a *label-less* multi-speaker source (see Step 0).
Normal build/audit work doesn't require it. Two idempotent installers cover
it — `setup-photo-identity.sh` (frame handling) and `setup-face-embeddings.sh`
(the dlib matching engine). Both report what's missing and exit non-zero on
failure — re-run them any time.

```
bash scripts/tools/setup-photo-identity.sh   # frame side: ffmpeg + Pillow + yt-dlp + JS runtime
bash scripts/tools/setup-face-embeddings.sh  # matching engine: cmake + dlib + face_recognition (.venv-face)
```

`setup-photo-identity.sh` installs and verifies the frame-handling side:

| Dependency | Purpose | Install path |
|---|---|---|
| `yt-dlp` | Video download | pip / apt |
| `ffmpeg`, `ffprobe` | Frame extraction, merge, duration probe | apt |
| `python3-pil` (Pillow) | Face crop resize/save | apt |
| JS runtime (`deno` / `node` / `bun`) | yt-dlp's EJS challenge solver | varies |

`setup-face-embeddings.sh` installs the dlib matching engine (separate venv —
PEP 668 + heavy C++ build):

| Dependency | Purpose | Install path |
|---|---|---|
| `cmake` + `build-essential` | Compile dlib from source | apt |
| `.venv-face/` (`--system-site-packages`) | Isolate dlib/face_recognition; reuse system Pillow/yaml | `python3 -m venv` |
| `dlib` + `face_recognition` + `numpy` | HOG detector + ResNet face embeddings | pip (in venv) |

Both scripts report missing pieces and exit non-zero if any apt / pip step
fails. Re-runnable.

---

## Step 0 — classify the source, pick the method

Run this *before* any step below. The source's `transcript_provenance` (in
`sources/manifest.yaml`) tells you whether speakers are already known or must
be reconstructed against the recording:

| Source | Speakers in source? | Method |
|---|---|---|
| `stenographic`, `published-transcript`, label-preserving `human-corrected-caption` | yes | **none** — take speakers from the source's own labels; only the verbatim-quote check applies. Skip this pipeline. |
| `auto-caption` / Whisper, **video with visible faces** | no | **image path** — steps 1 → 2 → 3 → 4, then human frame-verify each quote timestamp against the baseline. |
| `auto-caption` / Whisper, **audio-only** (no usable faces) | no | **agent text-pass + manual anchoring** — `/prepare-transcript-sibling` resolves speakers from content (self-intro, one speaker naming another, dominant monologue); the contributor anchors any turn the text can't settle. No on-disk faces to match, so this pipeline doesn't apply. |
| genuinely unresolvable boundary (overlap / rapid crosstalk) | n/a | `speaker_id: [s1, s2]` **mixed-exchange** — never fabricate a split. |

Faces do the naming on the image path; the discipline is
confirm-against-source — the speaker is reconstructed against the recording,
never inferred from text-cue guesswork (register, who-addresses-whom), which is
the misattribution failure mode.

**Dependency gating.** The image path needs a subset of the tooling. Check
before you run: a *missing but needed* dependency must stop the run with its
remedy. The tools fail-fast on their own — `download-video.py` /
`extract-frames.py` preflight their binaries, `detect-faces.py` auto-relaunches
under `.venv-face` (and errors with the setup script if it's absent) — each
naming the setup script to run.

| Method | Needs | Remedy if missing |
|---|---|---|
| image path | ffmpeg/ffprobe + Pillow (`setup-photo-identity.sh`), the dlib engine in `.venv-face` (`setup-face-embeddings.sh`); the video file; a baseline per speaker | run both setup scripts; re-fetch video with `download-video.py`; register baselines with `detect-faces.py register` |
| video re-fetch | yt-dlp, ffmpeg, JS runtime; **cookies only for YouTube**, not Vimeo | `setup-photo-identity.sh`; cookies via `extract-firefox-cookies.py` (YouTube only) |

---

## Four-step pipeline

Each step is one command. Defaults are tuned for the common case; flags exist
for tuning when needed.

Steps 1–4 build the persistent identity-baseline set; with baselines in place,
`detect-faces.py` (and `spot-check-attribution.py`, for a turn-by-turn check of
an attribution sibling) resolves who-is-who in any new frame. The contributor
uses that to populate `speaker_id` on transcript-artifact quotes.

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
  format: video, archive bits

Idempotent. Re-running with the same `--slug` skips the download if the file
already exists; still re-runs the manifest registration (which is itself
idempotent).

Common tunables:

- `--quality 720` for higher facial detail (file size scales ~2-3×)
- `--note "STR"` to attach contributor context to the manifest entry
- `--dry-run` to inspect the yt-dlp invocation without running

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

For each detected face (dlib HOG), the tool saves a 256×256 jpg crop to
`sources/photo-identity-log/crops/` (skipping near-identical frames via face
embedding distance) and records a best-guess identity hint where the embedding
matches a baseline. Summary reports counts: faces detected, deduplicated,
identified (embedding-matched against an existing baseline).

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
baseline set — when a freshly-detected face embedding-matches a baseline
within the match threshold, the tool tags the crop with that identity hint
(and dedups it if it's a near-identical repeat). More references per identity
(5–10 spanning angle/lighting/year) raise match accuracy; the embedding cache
(`baseline-encodings.npz`) rebuilds automatically when baselines change.

### Maintenance: prune unidentified crops

```
python3 scripts/tools/detect-faces.py prune          # interactive
python3 scripts/tools/detect-faces.py prune --dry-run
python3 scripts/tools/detect-faces.py prune --force  # no prompt
```

Removes crops in `crops/` whose face embedding matches no baseline identity
— i.e., unlabeled faces the contributor has decided not to keep. Removed
crops leave git history but no longer in HEAD.

### Using the baselines to attribute speakers

With baselines registered, two tools resolve who-is-who:

- `detect-faces.py detect` on frames at any contested timestamp tags each
  detected face with its embedding-matched identity — ad-hoc inspection when
  resolving a single contested turn.
- `spot-check-attribution.py SIBLING.yaml --video VIDEO.mp4` is the
  **active-speaker fold gate**: a per-turn frame burst across every turn,
  deciding who is SPEAKING (mouth-motion via `active-speaker.py`) not just who
  is on camera. `contested-fold` (another identified speaker is the active
  speaker) BLOCKS finalize. It runs automatically inside
  `finalize-attribution.py --video`; run it standalone to preview before
  finalizing.

Both feed attribution; neither is manifest-registered. The downloaded transcript at
`sources/transcripts/{slug}-downloaded.md` remains the verbatim source the
validator's verbatim-quote check verifies against.

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
bash scripts/tools/setup-face-embeddings.sh

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
| `setup-photo-identity.sh` | First time on a machine, or when adding the video pipeline to an existing checkout (frame handling) |
| `setup-face-embeddings.sh` | First time on a machine — installs the dlib face-embedding matcher (`.venv-face`) that `detect-faces.py` / `spot-check-attribution.py` need |
| `download-video.py` | Archiving a new video source that needs face detection |
| `extract-frames.py anchor` | First-time on a video — establish visual identity of each on-camera speaker |
| `extract-frames.py burst` | Speaker disambiguation at a specific contested transcript timestamp |
| `extract-frames.py sweep` | Visual map of an unfamiliar source |
| `extract-frames.py transcript` | Exhaustive frame coverage matching every caption tick |
| `detect-faces.py detect` | After any extract-frames run, to find faces in the extracted frames |
| `detect-faces.py register` | After reviewing a crop, to promote it to a persistent baseline |
| `detect-faces.py prune` | Periodic cleanup of unidentified crops |
| `spot-check-attribution.py` | The active-speaker fold gate — per-turn frame burst + active-speaker (mouth-motion) deciding who is SPEAKING; `contested-fold` blocks finalize. Runs inside `finalize-attribution.py --video`; standalone for preview |
| `active-speaker.py` | Mouth-aspect-ratio (MAR) active-speaker detection (WHICH on-screen face is talking); library for the spot-check gate, plus a calibration CLI |
| `extract-firefox-cookies.py` | Only when piping cookies into a tool that doesn't support `--cookies-from-browser` (e.g., `transcribe.py`) |
