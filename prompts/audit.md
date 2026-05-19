# Audit prompt

Paste into a Claude Code session to audit an existing node.

---

Run the onboarding steps in `prompts/onboard.md` first if you haven't
this session.

The audit target is: **{PATH}**  (ask the user if not specified)

## Optional pre-audit — surface under-extraction candidates

The mechanical validators verify structural integrity, verbatim-quote
correctness, and prose-drift discipline — but they cannot catch
under-extraction (substantive source content the contributor missed
when populating quotes / entities). Run the read-only source-coverage
diagnostic before the audit-goal pass to surface candidates:

```
python3 scripts/tools/coverage-suggest.py meta/research/{slug}.yaml
```

For each primary source, the tool prints (a) substantive paragraphs
no quote references and (b) capitalized terms not present anywhere
in the artifact. Both lists are audit suggestions — boilerplate /
navigation / tangential matches are common (a hearing transcript
names 50 topics; a witness node only quotes a few). Contributor
judges each candidate manually.

## Recover 404'd primary sources via Wayback

If any manifest entry referenced by the artifact has `status:
pending` plus `wayback_date` set, the original URL is no longer
serving but the Internet Archive Wayback Machine retains a snapshot.
This is a recoverable audit-blocker, not a dead end — see
`meta/sources-access.md` "Wayback Machine fetch — fuzzy-timestamp
URLs bypass anti-bot challenge". Use the fuzzy-timestamp pull
workflow there to retrieve the snapshot, save it locally, update the
manifest entry to `status: archived` with path + sha256, and add the
source to the artifact's `primary_sources[]`. Quotes derived from
the recovered source then pass the verbatim-quote check normally.

Don't conclude "primary source unrecoverable" until the
fuzzy-timestamp pull has been tried — exact-timestamp Wayback URLs
trigger an anti-bot challenge that fuzzy-timestamp URLs bypass.

## Audit goals

1. **Evidentiary integrity** — every confirmed claim traces to a
   primary source archived in `sources/` and registered in
   `sources/manifest.yaml`. Flag any claim that does not.
2. **Quote verbatim check** — every `> blockquote` has an attribution
   block (Attributed to / Source / Location). The verbatim-quote check
   in `validate.py` runs unconditionally on every quote whose Source
   row points at an archived file under `sources/`, substring-matching
   the quote against the extracted source. A clean `validate.py` run
   covers the mechanical case — but spot-check a few for semantic
   reading (source location refs can be right-but-imprecise; the
   substring check won't catch that). No rendered marker accompanies
   confirmed quotes — confirmation is a precondition for inclusion,
   enforced by the validator, not displayed to the reader. See
   `meta/conventions.md`.
3. **Prose-drift check** — for all artifact types (document, person,
   event, transcript, media, organization, location, finding,
   investigation), re-run `validate-research.py {artifact}` and work
   through the prose-drift warning set. Under the durable policy
   (`feedback_prose_drift_warnings_must_resolve.md`):
   - **Free-prose synthesis fields** (`description`, `background`,
     `top_relevance`, `credibility_notes`) and **per-entry synthesis
     content notes** (`ownership_timeline.note`,
     `top_scope_activity.note`, `key_personnel.note`, `contracts.note`,
     `media_versioning.note`, `vouching_chain.attestation`) — zero
     warnings is the target. Each unmatched token either resolves to
     source-matched prose OR gets captured as structured evidentiary
     data (naming quirk, rumor, timeline entry, or a new quote).
   - **Structural labels + cross-reference descriptor notes** are not
     scanned by the prose-drift check. Role titles, short relationship
     descriptors, `timeline[].event`, `use_status`, `activity`, and
     the `.note` fields on cross-reference entries
     (`corroboration_items`, `witnesses_testimony`, `org_relationships`,
     `location_relationships`) all fall outside scope. Fabrication
     there is Phase III semantic-review territory.
4. **Contradiction markers** — `❌ Contradiction` used where positions
   contradict and at least one side has primary-source evidence;
   `⚠ Disputed — unknown` used only where neither side has
   primary-source evidence. Reclassify if wrong.
5. **Section requirements** — run `python3 scripts/build/validate.py {path}`
   and fix any errors.
6. **Coverage / Boundary / Stub-linking / Description-drift** — run
   `python3 scripts/build/review-coverage.py meta/research/{slug}.yaml`. Any
   Boundary failure means the node was hand-edited after regeneration
   (or the artifact drifted). Fix in the **artifact**; regenerate via
   `build-from-research.py`; never hand-patch the node to silence the
   check.
7. **Associated Nodes freshness** — run
   `python3 scripts/build/associate.py {path}` to regenerate.
8. **Cross-node consistency** — check that claims in this node agree
   with claims in nodes it references. Flag any unexplained divergence.
   For naming quirks (e.g., "Lue" alias-of-record for Elizondo),
   verify the quirk is tracked consistently across all artifacts that
   cite the same source.

For nodes carrying significant quote material (transcripts, hearing
events, podcast-heavy person nodes), follow this prompt with
`prompts/quote-relevance-audit.md` — a deeper layer that evaluates
each `quotes[]` entry for load-bearing relevance to the node's
subject. Extraction-completeness audit (this prompt) and content-
relevance audit (quote-relevance-audit.md) are separate concerns:
this prompt asks "did the contributor extract everything the source
supports?"; quote-relevance asks "is each extracted quote earning
its place on this node?". Both passes complement each other.

## Applying corrections

Audit findings that require changes are edits to the research artifact,
not direct edits to the node body. Pattern:

1. Make the change in the artifact (edit a field, add or remove an
   entry, refine a note)
2. When new material contradicts or supersedes an existing entry,
   preserve the original and add the new one alongside via
   `superseded_by` / `contradicted_by` / `corroborated_by` pointers
   (see `meta/conventions.md` Versioning). Typo fixes and
   clarifications edit in place; content that was substantively
   different gets a new entry + pointer.
3. Regenerate the node (renderer-supported types):
   `python3 scripts/build/build-from-research.py meta/research/{slug}.yaml`
4. **Reader-visibility check** — grep the regenerated node for the
   changed content to confirm the fix actually surfaces in the
   rendered surface. Mechanical validators verify structure; they
   don't verify that an artifact edit produced a reader-visible
   change. Artifact-only fields (`entities_referenced[]` and lifecycle
   fields `id` / `added_date` per `meta/schema-research-artifact.yaml`)
   never render — edits to those land only in the artifact, not in
   the body. If the audit goal required a reader-visible change, the
   grep must hit; if it doesn't, the edit was to an artifact-only
   field and the fix needs to move into a rendered surface (prose,
   timeline entry, quote, structured-data row).
5. Re-run `review-coverage.py` — must pass all four checks
6. Run the full pre-commit chain — all nine gates green
   (`bash scripts/tests/pre-commit.sh`)
7. Commit with a descriptive message; git log is the edit history.

## Audit output

Use this template so audit reports stay comparable across sessions
and contributors. Each section may be empty (skip when nothing applies):

```
## Audit findings — {node path}

### Mechanical (validators)
- validate.py: PASS / FAIL ({error/warning count})
- validate-research.py: PASS / FAIL ({error/warning count})
- review-coverage.py: PASS / FAIL ({per-check status})

### Semantic gaps from existing sources
- (list under-extracted content surfaced by coverage-suggest +
   re-reading; cite paragraph / line refs)

### Missing primary sources
- (list sources we'd want but don't have archived; for each, note
   whether a Wayback snapshot exists per manifest, the retrieval plan
   if known, or the blocker if unrecoverable)

### Rumors / non-primary-sourced circulating claims
- (claims widely repeated in public discourse not yet anchored to a
   primary source; candidates for rumor entries)

### Cross-node consistency findings
- (divergences between this node and nodes it references)

### Proposed changes
- (artifact diff preview)
- (regenerated-node diff preview)

### Recommendations
- (numbered list of actions, ordered fix-now vs queue-for-later;
   queued items get BACKLOG entries per
   feedback_investigate_before_queueing.md)
```

After user approval, apply changes and commit as a focused
audit-correction commit. Per the audit-correction pattern above:
edit the artifact, regenerate the node, run the full pre-commit
chain, commit.

## Do not

- Remove Flagged items without verifying them against a new primary
  source
- Introduce new claims without new archived sources
- Reframe existing confirmed claims without new evidentiary basis
- Hand-edit the node body on renderer-supported types — fix the
  artifact and regenerate
- Silence the verbatim-quote check or the prose-drift check by
  acknowledging warnings as "legitimate synthesis" when they are
  actual drift. Either source-match the prose / quote, or capture
  the variance structurally; or if a quote can't be confirmed
  against its source, remove it from the artifact rather than
  letting it ship.
