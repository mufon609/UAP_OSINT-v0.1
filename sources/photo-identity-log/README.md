# Photo identity log

Persistent visual-identity reference set for speaker disambiguation on
multi-speaker video sources. The accumulating baseline crops here make
who-is-who mechanically resolvable across the corpus.

This directory is populated by `scripts/tools/detect-faces.py`. The full
end-to-end pipeline (download → extract frames → detect faces → register
baselines) is documented in **`scripts/tools/VIDEO-PIPELINE.md`** — read
that for the workflow.

## Layout

```
sources/photo-identity-log/
├── crops/                          # working area — unlabeled face crops
│   └── {video-stem}_{ts}_face_NN.jpg          (gitignored)
├── baselines/                      # persistent — labeled identity references
│   ├── {identity-slug}/
│   │   ├── ref_01.jpg
│   │   └── ref_02.jpg
│   └── ...
├── manifest.yaml                   # baseline registry (sha256-tracked) — THE persistent record
├── index.csv                       # per-session detect log (gitignored)
└── README.md                       # this file
```

`baselines/` and `manifest.yaml` are the persistent record — they're the
permanent identity-reference set the whole pipeline depends on.
`manifest.yaml` carries everything that has to survive across machines and
contributors: sha256, source-video path, source timestamp, bbox,
added_date, and note for every registered baseline.

`crops/` is gitignored working state (see `.gitignore`). detect-faces.py
writes unlabeled face crops here for the contributor to review; once a
crop is `register`ed as a baseline it moves into `baselines/`. Unlabeled
crops that don't represent anyone worth a baseline can be deleted
freely — they're never the permanent record. The directory itself is
tracked via `.gitkeep` so the layout is reproducible on fresh clones.

`index.csv` is also gitignored — it's purely a per-session log of every
crop detect-faces.py encountered, useful within a session for reviewing
what came out of a run. detect-faces.py auto-prunes rows whose `crops/*`
paths no longer exist on disk, so the local file stays coherent across
runs. The authoritative cross-session record for baselines is
`manifest.yaml`.

## Manifest schema

See `meta/schema.yaml::photo_identity_manifest_entry`. Each entry registers
one baseline crop with:

- `identity`: kebab-case slug; matches `baselines/{identity}/` directory name
- `path`: relative to `sources/photo-identity-log/`
- `sha256`: integrity hash
- `source_video_path`: where the source frame came from
- `source_timestamp`: when in the source video
- `bbox`: `[x, y, w, h]` of the face within the source frame
- `added_date`: ISO `YYYY-MM-DD`
- `source_video_url`, `note`: optional

Distinct from `sources/manifest.yaml` (the URL-archived primary sources
manifest); this manifest tracks *derived* baseline crops with provenance back
to a source video + timestamp + bbox.
