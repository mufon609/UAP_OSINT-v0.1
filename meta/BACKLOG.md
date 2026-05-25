---
id: meta/BACKLOG
type: meta
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

Open items are partitioned into three sections by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
and **C — Anytime** (no upstream blockers). Item identifiers within
each section (A1, A2, …, B1, …, C1, C2, …) are positional working
labels, not stable identifiers. A closed item's block is deleted in
full — no marker, no placeholder. A new entry takes the lowest section
number not currently in use, so **numbers recycle**; once a section,
and ultimately the whole BACKLOG, is cleared, numbering restarts from 1.
Because an ID is transient and reused, never reference it from outside
this file — not in code, docs, prompts, commit messages, or `git log`
searches. Describe the work; the commit diff + message are the record.
See `meta/conventions.md` "BACKLOG lifecycle discipline".

**Default focus: Section C.** C items have no upstream dependencies
and can be picked up and finished in a single pass. A and B items
carry ordering or coupling constraints — starting one without its
dependencies risks half-baked implementations and leaves the BACKLOG
cluttered with partial work. For ad-hoc sessions, prefer C work.
Reserve A and B for sessions explicitly scoped to those tracks.

Items waiting on an external event the repo can't drive (FOIA
resolution, registry access, third-party publication) and that are
**topic-specific** to the current investigation live in
`meta/topic/research-queue.md` "Externally blocked" — that's the fork-
boundary-correct home for them. If a genuinely toolkit-neutral
externally-blocked item ever surfaces (rare), reinstate the
"Externally blocked" heading at the bottom of this file.

Cross-references between entries use `**Blocks:**` / `**Blocked by:**`
lines so the dependency graph is visible inline.

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Exercise the pipeline paths the first whole run didn't hit

The six-role pipeline (`prompts/topology.md`) has been run *whole* on one
real node build — a user-directed, all-internal institutional-actor build:
Internal Investigator → Worker (×N) → Build → Audit, with handoff stubs
captured and friction tightened in place. The **External Investigator
(role 2) and Archive (role 3)** roles have since been exercised standalone on
an existing node — a source-recovery that re-pulled a dead JavaScript-shell
capture from a Wayback snapshot (External Investigator confirmed the snapshot
and captured verbatim spans; Archive re-pulled the file and refreshed the
manifest). Both behaved per contract. Paths still unverified end-to-end:

- **role 2 + role 3 integrated inside a full `/build`** with a genuine
  external-source gap — so far they have run standalone, not as the
  external-gap branch of a fresh orchestration.
- the **`foia` worker kind** — `caption` is now exercised (the all-internal
  `jre-2194-elizondo-2024` transcript build hit it end-to-end: internal-survey →
  caption worker → builder → audit). `pdf` + `html` + `caption` done; only `foia`
  remains, and no load-bearing *unarchived* FOIA source currently exists to build
  (every referenced FOIA doc is already archived) — wait for a genuine FOIA gap
  rather than manufacturing one.
- **error routing** (`route_failure.py`) — no validator failure has needed
  routing on a clean run (the caption build was clean; its audit findings were
  applied via builder re-entry, not a routed check failure).

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

### A3 — DIRD extraction: re-level the corpus against the rubric + extract remaining citations

The DIRD extraction standard now exists — the passage-selection rubric in
`meta/conventions.md` "Document-corpus extraction — the DIRD passage rubric"
(provenance / thesis-and-scope / each section's finding / methods / conclusions /
acknowledgements / references), under the "Comparability standard". The
`cited_works` dimension is modeled (`schema-research-artifact.yaml`
`cited_work_entry`; required-but-emptyable on every document), rendered
(`## References` in `renderers/document.py`), source-fidelity-gated
(`scripts/checks/cited_works.py`), and proven on dird-24 (113 references
extracted, references region image-verified). Remaining work:

**(a) Re-level DIRD density against the rubric.** Audit each built DIRD's quote
set against the rubric — the target is each major section's finding captured, NOT
a quote-count (`### Density is source-driven`). **dird-24 DONE** (2026-05-24,
9 → 19 quotes): captured §II Cole-Puthoff thermodynamics / Forward's
no-continuous-extraction limit / "no practicable technique demonstrated", §III
QED + SED origin of the ZPF, §IV Koch et al. corroboration, the §V/Summary
ZPF-modes-placeholder + new-boundary-conditions findings, and §VI SED-inadequate
/ QED-vacuum-degradable conclusions; quotes renumbered to document order; the
equation/superscript energy-density passages intentionally left unquoted. Each
re-level requires image-verifying the relevant OCR-sibling body regions against
the PDF first (the built DIRDs verified only their already-quoted regions — see
the dird-24 sibling note for the precedent). Use `coverage-suggest.py` + the
rubric. Remaining: dird-04 (55 quotes) audited for whether each quote is a
distinct subsection finding (likely over the bar, not under); dird-01/02/03/15/26
audited for any skipped section findings. Re-level the set for consistency.

| DIRD | pages | quotes | quotes/page |
|---|---|---|---|
| dird-24 quantum-vacuum-energy-extraction (RE-LEVELED → 19) | 58 | 9→19 | 0.33 |
| dird-26 field-effects | 39 | 21 | 0.54 |
| dird-01 metallic-glasses | 31 | 17 | 0.55 |
| dird-03 pulsed-hpm | 38 | 23 | 0.61 |
| dird-15 advanced-space-propulsion | 17 | 13 | 0.76 |
| dird-02 programmable-matter | 21 | 17 | 0.81 |
| dird-04 biomaterials | 33 | 55 | 1.67 |

**(b) Extract `cited_works` — the 7 BUILT DIRDs are DONE.** dird-24 (113, `[N]`),
dird-01 (49, `^N` endnotes), dird-02 (9, `N.` list), dird-15 (22, `^N`; Puthoff's
DIRD — cites Davis/Maccone), dird-26 (52, `[N]` + sub-lettered `[5-a/b/c]`; the
UFO-relevant list — Schuessler, Sturrock, Vallee, Cash-Landrum). dird-03
(Pulsed HPM) and dird-04 (Biomaterials) were assessed and **carry no formal
reference list** (end at Conclusion / Summary; sibling marker-scan = 0; PDF last
page confirmed) — their `cited_works: []` is correct, not missing. Remaining:
the UNBUILT DIRDs (dird-05/06/08/11/19/22/25/29/30/33/34/37, etc.) get their
citations when each is built — same per-DIRD flow (locate region → image-verify
sibling vs PDF → worker extract → integrate). The recurring-author network is the
payoff (Puthoff in 7 dird-24 refs + dird-15; E. W. Davis / C. Maccone cross-DIRD).

*Illegible references (deferred — design on first real case).* dird-24's
references were all recoverable by image-verifying the PDF page. If a remaining
DIRD has a reference that is **visibly present but genuinely unreadable** (scan
too degraded to make out, not recoverable from the page), the current mechanism
has no answer (the `cited_works` verbatim check errors). At that point add: an
optional `cited_work_entry.legibility: illegible` flag → `cited_works.py` WARNS
instead of erroring (mirrors the binary-source warn path) and still verifies any
legible fragment provided; the renderer emits a standardized, searchable `[sic]`
label — `**[N]** *[illegible in source — p.N; preserved [sic], flagged for
re-OCR/re-verification]*` — greppable later via `legibility: illegible`
(artifacts) and `[illegible in source` (nodes). Capture the marker + legible
fragment; never fabricate the unreadable span, never skip the entry (skipping
loses the fact a reference exists at [N]).

**(c) DIRD corpus consistency sweep — two cross-DIRD inconsistencies found during
the dird-05 build.** Both are family-comparability sweeps best done in one focused
`/audit` pass, not piecemeal:
- *DIA forward-ref link.* 7 of 9 built DIRDs link `[`/organizations/dia`]` in their
  description (the AAWSA Program Manager sits in DIA on every DIRD's Administrative
  Note); **dird-02 and dird-26 omit it**. Add the link to those two (prose-drift-safe
  — "Defense Intelligence Agency" is verbatim in each source). The
  dird-build-out-roadmap's "settle when DIA/AAWSAP orgs are built" note resolves to:
  the de-facto convention is the forward-ref link, so settling = making dird-02/26
  match. (Building the `/organizations/dia` node itself remains a separate,
  one-per-session synthesis-node decision.)
- *Front-matter page-ref convention.* `quote_location_page` verifies arabic `p. N`
  against the Nth sibling block but SKIPS roman refs (`p. ii`) as carrying no
  physical-page claim. **5 of 9 DIRDs (dird-01/02/03/15/26) use roman printed-label
  refs for front matter (unverified); 4 (dird-04/24/05/18) use arabic sibling-block
  refs (verified).** Decide the standard and apply: (i) convert the 5 to arabic
  sibling-block (conventional per `meta/conventions.md` "p. N = physical, not
  printed"; verified) — a 5-node content sweep; or (ii) extend `quote_location_page`
  to map roman front-matter labels to sibling blocks and verify them (one-script
  root-cause fix, keeps reader-faithful printed labels — viable where the roman
  value equals the block index, as it does for dird-26). Pick one; don't leave the
  split. (Auditor note: the build-role auditor flagged the roman-ref issue as
  dird-26-specific and missed dird-02's DIA-link omission — its recommend-only
  family-comparability pass is not exhaustive across the family.)

**Blocks:** none.
**Blocked by:** none. Each DIRD's re-level / extraction is gated on OCR-sibling
verification of the relevant region.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — Apply the family-comparability audit to AARO's contested claims

The cross-node comparability mechanism now exists — the "Comparability standard"
in `meta/conventions.md` plus the recommend-only family-comparability goal in the
auditor (`.claude/agents/auditor.md` goal 8, surfaced in `/audit`). Remaining is
the one concrete observed asymmetry: `/organizations/aaro` carries no
`## Primary-Source Contradictions` section while peer `gov` org
`/organizations/ipmo` does. Run `/audit` on `aaro` and apply goal 8 — does AARO
have a circulating public claim that an archived primary source actively refutes
(warranting a `rumors[].status: primary-source-disputed` entry)?
`/findings/aaro-denial-action-mismatch` is a lead. A **source re-check, not a
count match**: add an entry only if a source attests it; if none does, the
absence is correct.

(The Associated-Nodes-vs-Relationships observation was resolved as **by-design** —
Associated Nodes is an unlabeled post-build navigation surface; relation type
lives on the source entity's Relationships row. Duplicating it onto every
backlink is redundancy, not discipline. No change.)

**Blocks:** none.
**Blocked by:** none.

### C2 — Investigate whether the Description "no-duplication" convention should relax

The maintainer wants `## Description` to read as a well-defined summary that may
surface select salient items also living in a structured section (a key
relationship, timeline event, contract, finding). The current convention pushes
the other way — `meta/conventions.md` "Date precision: orientation-grade in prose,
field-precise in tables" states *Description should not duplicate field-precise
dates from a structured surface* and *eliminating duplication removes a drift
surface*. That anti-drift rationale is load-bearing, so a relaxation could easily
go bad; it is deferred for investigation, not changed in place.

Avenues to weigh before any edit: (a) survey how built nodes actually use
Description today — is the overlap pressure real or rare?; (b) whether the
carve-out should stay field-precise-only (exact dates / dollar amounts / control
numbers single-sourced in their table; orientation-grade overlap allowed); (c)
whether the `description_token_drift` check needs any change (it checks grounding,
not overlap, so likely none). Produce a recommended wording, then edit the
convention and record the rationale.

**Blocks:** none.
**Blocked by:** none.
