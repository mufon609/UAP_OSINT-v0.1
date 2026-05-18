# Photo identity log

Persistent visual-identity reference set for speaker disambiguation on
multi-speaker video sources (panel discussions, interviews, documentaries).
Whisper and YouTube auto-caption transcripts don't preserve speaker identity;
this log accumulates contributor-curated face references so future analysis
can mechanically distinguish who-is-who across the corpus.

The log is populated by `scripts/tools/detect-faces.py`, downstream of
`scripts/tools/extract-frames.py`.

## Layout

```
sources/photo-identity-log/
├── crops/                          # working area — unlabeled face crops
│   └── {video-stem}_{ts}_face_NN.jpg
├── baselines/                      # persistent — labeled identity references
│   ├── {identity-slug}/
│   │   ├── ref_01.jpg
│   │   └── ref_02.jpg
│   └── ...
├── manifest.yaml                   # baseline registry (sha256-tracked)
├── index.csv                       # working state — every crop + identity match
└── README.md                       # this file
```

Everything in this tree is tracked in git. `crops/` is a working area but its
crops are still committed — perceptual-hash dedup at `detect` time prevents
duplicate accumulation; `prune` is available when contributors want to remove
unidentified crops they've decided not to keep.

## Workflow

1. Run `extract-frames` on a video to produce contact-sheet frames at
   contested timestamps:
   ```
   scripts/tools/extract-frames.py burst \
       --video sources/video/foo.mp4 \
       --timestamps "44:53,45:00,45:09"
   ```

2. Run `detect-faces detect` against the extract-frames index to detect every
   face in every contact sheet and crop them into `crops/`:
   ```
   scripts/tools/detect-faces.py detect \
       --index /tmp/frames-foo/index.md
   ```
   Summary reports faces detected, deduplicated, and identified (i.e., whose
   perceptual hash already matches a baseline crop).

3. Review the crops in `crops/`. For each clearly-labeled face you want to
   keep as a persistent identity reference, register it:
   ```
   scripts/tools/detect-faces.py register \
       --crop sources/photo-identity-log/crops/foo_face_03.jpg \
       --identity jake-barber \
       --source-video sources/video/foo.mp4 \
       --source-timestamp 0:15 \
       --bbox 480,120,180,180 \
       --note "anchor frame, two-shot at 0:15"
   ```
   This moves the crop to `baselines/jake-barber/ref_NN.jpg`, computes its
   sha256, and appends an entry to `manifest.yaml`.

4. Optionally prune crops you've reviewed and don't want to keep:
   ```
   scripts/tools/detect-faces.py prune          # interactive
   scripts/tools/detect-faces.py prune --dry-run
   ```

## Manifest schema

See `meta/schema.yaml::photo_identity_manifest_entry` for the canonical
schema. Each entry registers one baseline crop with:

- `identity`: kebab-case slug; matches the `baselines/{identity}/` directory
  name.
- `path`: relative to `sources/photo-identity-log/`.
- `sha256`: integrity hash of the baseline crop.
- `source_video_path`: where the source frame came from (repo-relative).
- `source_timestamp`: when in the source video the frame was extracted.
- `bbox`: `[x, y, w, h]` of the face within the source frame.
- `added_date`: ISO `YYYY-MM-DD` when registered.
- `source_video_url` (optional): source URL for cross-reference.
- `note` (optional): contributor context — pose, lighting, framing notes.

## Dependencies

`python3-opencv` + `opencv-data` (Haar cascade XMLs). One-time install:

```
scripts/tools/setup-photo-identity.sh
```

`detect-faces.py` checks for the cascade XML at runtime and reports a
contributor-friendly error if missing.
