---
id: meta/toolkit-notes/cross-artifact-consistency-check
type: meta
schema_version: 1
created: 2026-05-05
---

# Cross-artifact consistency check during corpus sweeps

A systematic-review technique for catching pre-existing structured-ref errors
that single-artifact validation can't see. Surfaced during BACKLOG C1 Phase C
cluster 4 (2026-05-04), where running the check against the cluster's freshly-
converted location refs found 11 stale page-anchor errors in a sibling artifact
that no validator gate had ever caught.

---

## The principle

When a corpus-wide sweep converts structured refs (locations, dates, periods,
contract values, etc.) in one class of artifact, sibling artifacts that cite
the same underlying source may already carry pre-existing canonical refs to
the SAME content. Pairing entries by normalized content and comparing the
new conversion against the pre-existing ref — then investigating any
disagreement against the rendered source — is the one slice of validation
that catches this class of error.

The check is **complementary**, not redundant, with the validator. The
verbatim-quote check confirms quote text appears *somewhere* in the source;
it does not verify the cited page anchor is correct. Single-artifact
validation can't see refs in other artifacts pointing at the same source.
Pre-existing canonical refs (non-deprecated form) escape strict-deprecated-
form sweeps entirely. The cross-artifact consistency check is what's left.

---

## What surfaced it

BACKLOG C1 Phase C cluster 4 converted 188 deprecated `lines N-M` location
refs in 8 hearing-transcript and related artifacts to canonical `p. N` form
via PDF form-feed counting. The systematic re-review included a cross-
artifact consistency check:

- `/research/2023-07-26-house-grusch.yaml` (transcript artifact, 44 quotes
  freshly converted in cluster 4)
- `/research/david-grusch.yaml` (person artifact, 78 pre-existing canonical
  refs to the same House Oversight PDF, using the form `<context>, p. N`)

Pairing quotes by `normalize_for_compare(text)` first ~80 chars surfaced 17
page-number disagreements between same-quote-same-source pairs.

Direct PDF verification by per-page pdftotext extraction + anchor-regex
search of the cited pages:

| Artifact | Disagreements verified on cited page |
|---|---|
| Cluster 4 conversions (transcript artifact) | 17/17 |
| Pre-existing canonical refs (person artifact) | 8/17 |

9 of the 11 person-artifact errors were off by ±1 page — the contributor
had cited "the page where I read this" rather than "the first page that
contains the quote text." Most cases (q67-q70, q75, q76-q77, q143) were
+1 errors where the quote starts at the top of a page and the contributor
cited the previous page (where introductory context ends). Two cases
(q106-q107) were -1 errors. One case (q118) had the contributor citing
`p. 37-38` for a quote fully contained on `p. 36`.

All 11 errors were corrected in cluster 5. Without the cross-check, those
errors would have remained indefinitely — `validate.py` never failed on them
and no single-artifact view exposed the inconsistency.

---

## How to run the check

When designing the systematic re-review for a corpus sweep, include a cross-
artifact consistency check whenever the converted artifacts may share sources
with other artifacts. Common pairings:

- **Transcript ↔ witness person** (same hearing source) —
  `transcripts/2023-07-26-house-fravor` ↔ `people/david-fravor`
- **Document ↔ author / subject person** (same document source)
- **Event ↔ participant person** (same event source)
- **Organization ↔ employee/director person** (same organizational source)

Pair entries by normalized content, not by ID — IDs differ across artifacts.
For quote pairs, match on `normalize_for_compare(text)` first ~80 chars. For
other entry types, match on the most stable identifying field.

Categorize disagreements before flagging:

- **Within-range** — contributor used a range form like `p. 22-23` and the
  other artifact uses `p. 22` for the same quote within that range.
  Different granularity, both correct, no action.
- **Different-page** — cited pages don't overlap. Verify each against the
  rendered source (per-page pdftotext extraction + anchor-regex search).
  Whichever side fails verification is the error.

When the cross-check identifies pre-existing errors in the older artifact:
fix them (per `meta/conventions.md` "Versioning" — corrections of factually
wrong refs are pure errata, not the Superseded By / Contradicted By case
that needs a versioning trail). Bundle as a follow-up cluster or commit,
separate from the strict-deprecated work that triggered the sweep. Verify
each fix against the rendered source before committing.

---

## Why it's worth the time

The check found 11 errors that would have stayed in the corpus indefinitely.
The error class — page anchors that point at adjoining pages instead of the
quote-bearing page — is invisible to every other validation surface in the
toolkit:

- `validate.py` verbatim-quote check: passes (text is in source somewhere).
- Phase B `normalize-locations.py` deprecated-form scan: passes (the
  pre-existing refs are in `p. N` canonical form, not deprecated `lines N-M`).
- Single-artifact human review: doesn't see refs in other artifacts.
- Renderer regeneration: produces a wrong Location row matching the wrong
  artifact data; no inconsistency to flag.

The cross-artifact consistency check is the only systematic catcher for this
class of error. Run it once per corpus sweep where artifact pairs share
sources; the marginal cost is small (a few minutes of pairing + spot-check)
and the surfaced error rate is non-trivial.
