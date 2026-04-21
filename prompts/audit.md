# Audit prompt

Paste into a Claude Code session to audit an existing node.

---

Run the onboarding steps in `prompts/onboard.md` first if you haven't
this session.

The audit target is: **{PATH}**  (ask the user if not specified)

## Audit goals

1. **Evidentiary integrity** — every confirmed claim traces to a
   primary source archived in `sources/` and registered in
   `sources/manifest.yaml`. Flag any claim that does not.
2. **Quote verbatim check** — every `> blockquote` has a verification
   block. Re-verify a sample of quotes against the archived source
   file. `validate.py` check #11 mechanically verifies every
   `✅ Confirmed — verified verbatim` marker as a substring match
   against the cited source file, so a clean `validate.py` run covers
   this — but spot-check a few for semantic reading (source location
   refs can be right-but-imprecise; the mechanical check won't catch
   that).
3. **Prose-field drift check (check #16)** — for artifacts of
   renderer-supported types (document, person, event), re-run
   `validate-research.py {artifact}` and work through the check #16
   warning set. Under the durable policy
   (`feedback_check16_warnings_must_resolve.md`):
   - **Free-prose synthesis fields** (`description`, `background`,
     `uap_relevance`, `credibility_notes`) and **per-entry synthesis
     content notes** (`ownership_timeline.note`,
     `uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
     `media_versioning.note`, `vouching_chain.attestation`) — zero
     warnings is the target. Each unmatched token either resolves to
     source-matched prose OR gets captured as structured evidentiary
     data (naming quirk, rumor, claim).
   - **Structural labels + cross-reference descriptor notes** are not
     scanned by check #16. Role titles, short relationship
     descriptors, `timeline[].event`, `use_status`, `activity`, and
     the `.note` fields on cross-reference entries
     (`corroboration_items`, `witnesses_testimony`, `org_relationships`,
     `location_relationships`) all fall outside scope. Fabrication
     there is Phase III semantic-review territory.
4. **Contradiction markers** — `❌ Contradiction` used where positions
   contradict and at least one side has primary-source evidence;
   `⚠ Disputed — unknown` used only where neither side has
   primary-source evidence. Reclassify if wrong.
5. **Section requirements** — run `python3 scripts/validate.py {path}`
   and fix any errors.
6. **Coverage / Boundary / Stub-linking / OQ dedup** — for
   renderer-supported types, run
   `python3 scripts/review-coverage.py research/{slug}.yaml`. Any
   Boundary failure means the node was hand-edited after regeneration
   (or the artifact drifted). Fix in the **artifact**; regenerate via
   `build-from-research.py`; never hand-patch the node to silence the
   check.
7. **Associated Nodes freshness** — run
   `python3 scripts/associate.py {path}` to regenerate.
8. **Cross-node consistency** — check that claims in this node agree
   with claims in nodes it references. Flag any unexplained divergence.
   For naming quirks (e.g., "Lue" alias-of-record for Elizondo),
   verify the quirk is tracked consistently across all artifacts that
   cite the same source.

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
   `python3 scripts/build-from-research.py research/{slug}.yaml`
4. Re-run `review-coverage.py` — must pass all four checks
5. Run the full pre-commit chain — all five gates green
6. Commit with a descriptive message; git log is the edit history.

## Audit output

1. Summary of findings (errors, warnings, suggestions, policy-driven
   corrections)
2. Proposed changes (artifact diff preview + regenerated-node diff
   preview before applying)
3. After user approval, apply changes and commit as a focused
   audit-correction commit

## Do not

- Remove Flagged items without verifying them against a new primary
  source
- Introduce new claims without new archived sources
- Reframe existing confirmed claims without new evidentiary basis
- Hand-edit the node body on renderer-supported types — fix the
  artifact and regenerate
- Silence check #11 (quote verbatim) or check #16 (prose drift) by
  downgrading markers or acknowledging warnings as "legitimate
  synthesis" when they are actual drift. Either source-match the
  prose or capture the variance structurally.
