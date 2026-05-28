---
name: audit
description: Audit an existing node for evidentiary integrity, verbatim/prose-drift correctness, contradiction markers, coverage, and cross-node consistency, then apply approved fixes. Use to audit or health-check a built node on its own.
argument-hint: {type}/{slug}
allowed-tools:
  - Agent(auditor)
  - Read
  - Grep
  - Glob
  - Edit
  - Bash(python3 scripts/build/build-from-research.py *)
  - Bash(python3 scripts/build/validate.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/review-coverage.py *)
  - Bash(python3 scripts/build/associate.py *)
  - Bash(python3 scripts/tools/coverage-suggest.py *)
  - Bash(python3 scripts/tools/route_failure.py *)
---

# Audit a node

Target: **$ARGUMENTS** (ask the user if empty).

1. **Independent assessment.** Spawn the **auditor** subagent on the target for
   a fresh-context cold pass — it runs the full validators + the audit goals
   and returns findings + `adjacent_needs_update[]`. The independent read is
   the point: the session that built a node can't reliably self-verify it.
2. **Pre-audit under-extraction + source-form grounding:**
   `python3 scripts/tools/coverage-suggest.py meta/research/{slug}.yaml`
   surfaces substantive paragraphs no quote references + capitalized terms
   absent from the artifact (suggestions; boilerplate is common — judge each),
   and **ungrounded `## Source-Form Notes`** — `preserve-as-sic-in-quotes`
   entries whose `observed` form appears only in its own table row (an
   incidental source typo logged but never quoted → drop it; a deliberate
   not-on-node variant → reclassify `resolution: off-node-variant`, which
   renders in `## Name Variants` — resolve each, Source-Form Notes carries no
   orphans).
   Then weigh the auditor's **family-comparability** pass (goal 8): per
   `meta/conventions.md` "Comparability standard", does a same-`type` /
   `kind` / `archetype` peer carry a source-anchored optional section this
   target lacks (`## Primary-Source Contradictions`, `## Public-Record Claims`,
   `## Source-Form Notes` / `## Preserved Disagreements`, `## References`)? If
   so, re-check the target's OWN sources for the same class of material — a
   source re-check, never adding entries to match a peer's count.
3. **Present findings before changing anything** — the mechanical results, the
   semantic gaps, missing sources, cross-node divergences, and proposed
   artifact edits. Get approval for content changes.
4. **Apply approved fixes to the artifact, never the node body** (the body is
   hook-blocked and regenerated). Route a failing check with
   `python3 scripts/tools/route_failure.py {check_names}`. When new material
   contradicts/supersedes an entry, preserve the original and add the new one
   with `superseded_by` / `contradicted_by` / `corroborated_by` pointers; typo
   fixes edit in place.
5. **Regenerate + reader-visibility check:**
   `python3 scripts/build/build-from-research.py meta/research/{slug}.yaml`,
   then grep the regenerated body to confirm the change actually surfaces (a
   fix that lands only in an artifact-only lifecycle field never renders — move
   it to a rendered surface).
6. **Re-validate:** `review-coverage.py --all` must pass clean; then the
   full pre-commit chain. The user commits.

For quote-heavy nodes (transcripts, hearings, podcast-heavy people), follow
with `/quote-relevance-audit` — the content-relevance layer mechanical checks
can't evaluate.

Do not: remove Flagged items without a new primary source; introduce claims
without new archived sources; hand-edit the node body; or silence the
verbatim / prose-drift checks by calling real drift "legitimate synthesis."
