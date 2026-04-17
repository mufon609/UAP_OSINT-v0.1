# Iterate prompt — STUB (Phase D deliverable)

Paste into a Claude Code session to add new material to an already-built
node.

---

**Status: stub.** The full iterate prompt is a Phase D deliverable —
the layered-process tooling (research artifacts, Phase I/II/III)
needs to be in place before iteration has a well-defined procedure.

Until then, this file exists so `AGENT.md`'s task-router table has a
valid target. If an iteration is genuinely needed now (i.e., new
material surfaces for an existing node before Phase D ships), follow
the interim procedure below.

---

## Interim procedure (pre-Phase-D)

The iteration model — append-only research artifacts, regeneratable
nodes, three-phase process — is documented in `meta/conventions.md`.
Read that section first.

For nodes that exist today without a research artifact:

1. **One iteration per session.** Same hard rule as initial build.
   See `meta/toolkit-notes/pilot-failure-2026-04-17.md`.

2. **Source-read-first.** If the iteration adds a claim from a new
   source, that source must be extracted to plaintext (`pdftotext`
   for PDFs) and the new claim must be copy-pasted from the
   extraction, not paraphrased from memory.

3. **Preserve originals.** Do not overwrite or delete existing
   claims. New material is appended. Corrections use
   `Superseded By` / `Contradicted By` pointers on the original
   row per `meta/conventions.md` → "Versioning" section.

4. **Mandatory validator pass** after each iteration:
   - `python3 scripts/validate.py` (must exit 0)
   - `python3 scripts/manifest.py verify-checksums` (if the iteration
     added sources)
   - `python3 scripts/associate.py PATH` (regenerate Associated Nodes)

5. **Commit as a distinct iteration.** Focused commit message
   describing what was added and which source supports it.

---

## What Phase D will add to this prompt

- Step-by-step for each of the eight iteration types (A–H, see
  `meta/conventions.md` → "Iteration" discussion) with specific script
  invocations
- `scripts/iterate.py` (or equivalent) to scaffold an iteration that
  appends to the target node's research artifact rather than editing
  node prose directly
- Cross-node update queue integration (`scripts/pending-cross-updates.py`)
- Coverage check that node still matches its research artifact after
  iteration (`scripts/review-coverage.py`)

When those ship, this file will be rewritten with the real procedure.
