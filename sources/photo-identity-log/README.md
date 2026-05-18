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

All paths tracked in git. `crops/` is a working area but its crops are still
committed — perceptual-hash dedup at `detect` time prevents duplicate
accumulation; `prune` is available when contributors want to remove
unidentified crops they've decided not to keep.

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
