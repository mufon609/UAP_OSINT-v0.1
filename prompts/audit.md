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
     `uap_relevance`, `credibility_notes`) and **per-entry `.note`
     fields** + `vouching_chain.attestation` — zero warnings is the
     target. Each unmatched token either resolves to source-matched
     prose OR gets captured as structured evidentiary data (naming
     quirk, rumor, research_gap).
   - **Structural label cells** (role titles, short relationship
     descriptors, `timeline[].event`, `use_status`, `activity`) are
     not scanned by check #16 — token-matching is a poor instrument
     for compact multi-source labels. Fabrication in these cells is
     Phase III semantic-review territory.
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
8. **Open Questions realism** — each item should have concrete
   methodology. Remove items that are truly unresolvable-and-trivial;
   keep anything that names an investigation pathway. Unresolved items
   trace back to `research_gaps[].statement` in the artifact; fix
   there, not in the node.
9. **Cross-node consistency** — check that claims in this node agree
   with claims in nodes it references. Flag any unexplained divergence.
   For naming quirks (e.g., "Lue" alias-of-record for Elizondo),
   verify the quirk is tracked consistently across all artifacts that
   cite the same source.

## Applying corrections (iteration-correction pattern)

Audit findings that require changes should be applied as a new
iteration on the node's research artifact, not as direct edits to
the node body. Iteration mechanics follow the append-only discipline
in `meta/conventions.md` Versioning; the step-by-step pattern is:

1. Bump `last_iteration` to `i{N+1}` in the artifact
2. Itemize each correction in an `iterations[]` entry with
   `trigger: audit-correction`, listing `entries_modified` (and
   `entries_added` when new material is introduced)
3. Preserve originals via `superseded_by` pointers when substantively
   replacing an entry (not for typo fixes)
4. Regenerate the node (renderer-supported types):
   `python3 scripts/build-from-research.py research/{slug}.yaml`
5. Re-run `review-coverage.py` — must pass all four checks
6. Run the full pre-commit chain — all five gates green

Reference examples:
- Fravor person i0 → i1 audit (commit `f67f6e8`) — tightened four
  contributor-prose drift issues surfaced by check #16
- Nimitz event i0 → i1 audit (commit `305407d`) — revised check #16
  resolution policy; preserved "Lue" as alias-of-record in naming
  quirks; drove prose-field warnings to zero

## Audit output

1. Summary of findings (errors, warnings, suggestions, policy-driven
   corrections)
2. Proposed changes (artifact diff preview + regenerated-node diff
   preview before applying)
3. After user approval, apply changes via the iteration workflow and
   commit as a focused audit-correction iteration

## Do not

- Bulk-delete Open Questions without spot-checking each against body
  content and the corresponding `research_gaps[]` entry
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
