# Iterate prompt — append new material to an existing node

Paste into a Claude Code session to add new material, correct a drift
issue, or re-audit an already-built node. Iterations bump
`last_iteration` (`i0 → i1 → i2 ...`) and log an `iterations[]` entry;
entries themselves are append-only (use `superseded_by` /
`contradicted_by` / `corroborated_by` to preserve history).

The iteration target is: **{PATH}**  (ask the user if not specified)

---

## Hard rules

Same as build:

1. **One iteration per session.** Do not iterate a second node until
   the first is fully populated, regenerated, review-coverage-clean,
   and committed. See `meta/toolkit-notes/pilot-failure-2026-04-17.md`.

2. **Source-read-first.** Any new claim, quote, or entity must trace
   to text extracted from an archived source **in this session**.
   Not training knowledge.

3. **Append-only research artifacts.** Never delete entries. Corrections
   to existing entries are allowed but must be itemized in the
   iteration-log `entries_modified`. New material arrives as new entries,
   not overwrites.

---

## Iteration triggers

Different triggers set a different `trigger` value in the iteration
entry and a different scope:

| Trigger | When | Scope |
|---|---|---|
| `new-source` | A new primary source has been archived and extracted since the last iteration | Add quotes / claims / entities / research-gaps drawn from the new source |
| `audit-correction` | Review surfaces drift, mis-attribution, or prose-field warnings under the revised check #16 policy | Tighten prose to source vocabulary; strengthen naming-quirks notes; fix mis-attributed entries — preserve originals via `superseded_by` |
| `oq-resolution` | A research_gap is now answerable | Promote resolution into the body (new claim or prose); close the gap with `resolved: true`; retain as DONE only for null findings |
| `cross-node-update` | A claim in another artifact changed the evidentiary picture for this node | Cross-reference updates with `corroborated_by` / `superseded_by` / `contradicted_by` pointers |

Whatever the trigger, the same Phase I → II → III pipeline applies.
The only difference is scope — you add / modify fewer entries.

---

## Workflow

### Step 1. Read the current artifact

Open `research/{slug}.yaml`. Review:
- `last_iteration` — what to bump (`i{N}` → `i{N+1}`)
- Most recent `iterations[]` entry — what was last done
- `research_gaps` — open gaps that this iteration might close

### Step 2. Determine scope from the trigger

Before touching anything, write a short scope statement: *what new
material am I adding, and which source attests it?* If the answer
isn't "these specific quotes from this specific archived source," stop
and archive the source first.

### Step 3. For `new-source` triggers — archive + extract

```
# Download (if not yet archived)
curl -sL -o sources/{category}/{filename} "https://..."

# Register in manifest
python3 scripts/manifest.py add https://... --path {category}/{filename}

# Extract to plaintext
python3 scripts/extract-source.py --artifact research/{slug}.yaml
```

Add the new source's path to `primary_sources[]` in the artifact
before running `extract-source.py` if the artifact doesn't already
list it. See `meta/sources-access.md` for site-specific blocks.

### Step 4. Append new material to the artifact

Append (do not overwrite) to whichever sections the iteration touches:

- `quotes[]` — new verbatim passages from the new source. Copy-paste
  from the extracted scratch file; `observation_type` required on
  person artifacts; `context` required on person-artifact quotes.
- `claims[]` — only if the node type's renderer emits claims (today
  that's no renderer-supported type; see `build.md` claim scope note).
  For hand-authored pending-renderer types, claims apply per
  `meta/conventions.md`.
- `entities_referenced[]` — new entities named in the new source or
  new quotes. Deduplicate against existing entries.
- `naming_quirks[]` — new source-vs-canonical variances.
- `research_gaps[]` — new actionable gaps; existing gaps can close via
  `resolved: true` + `resolved_date` + `resolving_source` +
  `resolution_summary` (all three `resolved_*` fields required when
  `resolved == true`; `retain_as_done: true` optional for null
  findings / methodology outcomes).
- `timeline[]` — new dated facts (person / organization / event /
  finding artifacts).
- Archetype- or kind-specific lists — `corroboration_items[]`,
  `program_involvement[]`, `participants[]`, `witnesses_testimony[]`,
  etc.

Every new entry carries `added_by_iteration: i{N}` where `i{N}` is
the new iteration ID.

### Step 5. Modify existing entries only when required

For `audit-correction` triggers, the modified entries are tracked in
the iteration-log `entries_modified` list. For any entry that is
substantively replaced (not just a typo fix), consider using
`superseded_by` to preserve the original and add a new entry instead.

Typical audit-correction scope (based on F.1c Fravor and F.2c Nimitz
audits, commits `f67f6e8` and `305407d`):

- Contributor-prose drift in `description` / `background` /
  `uap_relevance` / `credibility_notes` / `timeline[].event` /
  `affiliations[].role` / `relationships[].relationship` /
  `corroboration_items[].note` (check #16 review)
- Mis-attributed subject referent (Battle Group vs squadron; "Lue"
  alias-of-record vs canonical "Luis")
- Cross-artifact consistency (naming quirks tracked on one artifact
  but not another for the same source)

### Step 6. Log the iteration

Append an entry to `iterations[]`:

```yaml
- id: i{N}
  date: '{YYYY-MM-DD}'
  trigger: {new-source | audit-correction | oq-resolution | cross-node-update | other}
  summary: |
    Prose description of what changed and why. For audit-corrections,
    itemize each fix with before/after and the source line reference.
    Cite any policy memory that drove the iteration (e.g.,
    feedback_check16_warnings_must_resolve.md).
  entries_added: [list of new entry ids]
  entries_modified: [list of modified entry ids]
```

Bump top-level `last_iteration` to match.

### Step 7. Validate the artifact

```
python3 scripts/validate-research.py research/{slug}.yaml
```

Must exit 0. Check #16 warnings — review per policy:
- Free-prose synthesis fields (`description`, `background`,
  `uap_relevance`, `credibility_notes`) → drive to zero
- Timeline cells → exempt from cosmetic source-morphology warnings
  (see `feedback_check16_warnings_must_resolve.md`)
- Other per-entry label fields → contextual; consult user if unsure

### Step 8. Regenerate the node (if renderer-supported)

```
python3 scripts/build-from-research.py research/{slug}.yaml
```

For unsupported types (transcript / media / organization / location /
finding), hand-edit the node body per the artifact changes, then run
`validate.py` + `associate.py`.

### Step 9. Review coverage (renderer-supported types)

```
python3 scripts/review-coverage.py research/{slug}.yaml
```

All four checks (Coverage / Boundary / Stub-linking / OQ dedup) must
pass. If Boundary fails, the node body drifted from the artifact
dry-run — regenerate instead of hand-editing the node.

### Step 10. Pre-commit chain

```
bash tests/pre-commit.sh
```

All six gates green. Refresh build state if the iteration changed
node status:

```
python3 scripts/build-state.py --update
```

### Step 11. Commit

Focused commit message describing the iteration:

```
{slug} i{N} — {trigger}: {short summary}

{prose body describing what changed, which source(s) supported it,
 and any policy memory that drove the iteration}
```

Then stop. Do not start another node / iteration this session.

---

## What NOT to do

- Do not delete or overwrite existing entries. Append with
  `superseded_by` pointers for corrections.
- Do not iterate a second node in the same session.
- Do not introduce claims from training knowledge — source-read-first
  applies in full to iterations.
- Do not skip the iteration-log entry. `iterations[]` is the audit
  trail; a missing entry silently erases the change's provenance.
- Do not bump `last_iteration` without a corresponding `iterations[]`
  entry (the validator will still pass today, but the two must agree
  for downstream audits).
