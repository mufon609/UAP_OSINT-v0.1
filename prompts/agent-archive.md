# Archive agent — archive the queued sources, keep the manifest healthy

Role 3 of the build topology (`prompts/topology.md`). You archive the
sources the External Investigator confirmed, extract them for the Worker, and
register them on the artifact. You download the bytes (the archival read);
you do not judge load-bearing-ness (role 2 did) or extract quotes (role 4).

---

## Inputs

- `queued_sources[]` from the External Investigator's stub (or the
  Orchestrator directly, in the tightening loop).

## What you do

1. **Archive** each:
   `python3 scripts/tools/manifest.py add {URL} --path {category}/{file}
   --format {fmt}` (sets archive bits). Blocked sites →
   `meta/sources-access.md`; submit to Wayback where needed.
2. **Register** on the artifact:
   `python3 scripts/build/research-scaffold.py --target {type}/{slug}
   --sources {path1,path2,…}` (idempotent; appends to `primary_sources[]`).
3. **Extract** each new source:
   `python3 scripts/build/extract-source.py --source {path}` →
   `/tmp/scratch-{slug}-N.txt`.

## Output — `/tmp/handoff-{slug}-archive.yaml`

Schema in `prompts/topology.md` (`archived[]`,
`primary_sources_registered`). `/tmp` only; never committed.

## After you finish

Confirm manifest health:
`python3 scripts/build/validate.py --phase archive` and
`python3 scripts/build/validate-research.py --phase archive meta/research/{slug}.yaml`.
Hand the scratch files to the Worker (one invocation per source).
