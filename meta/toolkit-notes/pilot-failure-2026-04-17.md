---
id: meta/toolkit-notes/pilot-failure-2026-04-17
type: meta
schema_version: 1
created: 2026-04-17
---

# Phase 2 Pilot Failure — 2026-04-17

Postmortem of the first Phase 2 pilot cluster. Preserved as institutional
knowledge because the failure mode it exposed is subtle, systematic, and
recurrable.

---

## What happened

On 2026-04-17, 10 pilot nodes were scaffolded and populated in a single
session:

- 1 event: `2023-07-26-house-uap-hearing`
- 3 documents: `written-testimony-{fravor,graves,grusch}-2023`
- 3 transcripts: `2023-07-26-house-{fravor,graves,grusch}`
- 3 people: `david-fravor`, `ryan-graves`, `david-grusch`

The scaffolder, schema, validator, and manifest worked correctly. The
10 nodes passed `validate.py` with 0 errors / 0 warnings. A post-build
fact-check against the archived primary sources then revealed that a
significant portion of the node content was not verifiable from the
cited sources.

The 10 nodes were deleted. The archived source files and manifest
entries were retained (source archival itself was correct).

---

## What failed

### Fabricated or composite quotes marked as `✅ Confirmed — verified verbatim`

**F1.** Fravor opening quote, claimed verbatim in 3 nodes:

> "I was the commanding officer of Strike Fighter Squadron 41, the
> world-famous Black Aces. I had been in the Navy for 18 years and
> had 3,500 hours of flight time and was a graduate of the Top Gun
> naval fighter weapons school."

Zero hits on `grep -i "3500|Top Gun|TOPGUN|Weapons School"` across the
hearing transcript and his written testimony. The phrases "3,500
flight hours" and "Top Gun" do not appear anywhere. The first clause
is a composite of two separate passages in the transcript (opening
statement line 807 + Q&A with Langworthy line 2353).

**F2.** Fravor encounter quote, claimed verbatim in 3 nodes:

> "As I was descending, the object was rising to meet me, almost as
> if it knew or was anticipating my movements. As I got close, it
> rapidly accelerated in front of us and disappeared."

"Rising to meet me / anticipating my movements" does not appear in
the transcript or written testimony. Widely-reported paraphrase,
not Fravor's sworn words.

**F3.** Graves quote, claimed verbatim in 4 nodes:

> "If everyone could see the sensor and video data I witnessed, our
> national conversation would change."

The source (line 189–190) actually reads:

> "If everyone could see the sensor and video data that I have, there
> is no doubt in my mind that UAP would be a top priority for our
> defense, intelligence, and scientific communities."

Paraphrase presented as verbatim.

### Mis-attributed claims

- **"IC IG found the complaint 'credible and urgent'"** — attributed
  to Grusch sworn testimony in 4 nodes. The phrase is not in his
  written testimony or hearing transcript. It's secondary-reporting
  language (The Debrief).
- **"Over 40 current/former military and intelligence personnel"** —
  framed as coming from Grusch's written statement. Actual source:
  hearing transcript line 1148 in Q&A with Garcia, different wording
  ("over 40 witnesses over 4 years").
- **"DoD prepublication review clearance, Apr 4–6, 2023"** — marked
  ✅ Confirmed in Provenance. Not in primary source; secondary
  reporting only.

### Fact errors

- **Virginia Foxx titled "Full Committee Chair"** of House Oversight.
  In the 118th Congress, Foxx chaired Education and the Workforce;
  Oversight full-committee chair was James Comer. The transcript
  roster shows Foxx as a subcommittee member.
- **"Chad Underwood captured FLIR1 on second sortie"** — named in 3
  nodes. Neither the hearing transcript nor Fravor's written
  testimony names Underwood or describes a second sortie.
- **"VFA-11 'Red Rippers'"** — Graves's testimony identifies "VFA-11"
  without the "Red Rippers" nickname. Historically correct but not
  primary-source-confirmed.

### Unsourced claims

Grusch's degrees (B.S. Physics University of Pittsburgh; M.A.
American Military University), "Combat veteran (Afghanistan),"
"Left government service April 7, 2023," specific NRO/NGA period
dates — all cited as Background fact but traceable to documents
(Grusch resume, The Debrief article) that are NOT in the REFACTOR
manifest. The only academic claim IN the archived primary sources
is "I have a degree in physics" (transcript line 1561, Q&A).

---

## Root cause

Content was generated from training knowledge, not from the archived
source files. When a node needed a quote, the quote that came to mind
was written down and marked `✅ Confirmed — verified verbatim`. When a
node needed a fact (e.g., a senator's committee role), the
recollection was treated as source-verified. The quote-verification
markers in templates were filled syntactically because the template
said that's where they go, not because the quote had been extracted
from the cited file.

This is the single failure mode the repository's epistemic standard
exists to prevent. The build produced cosmetically clean nodes (valid
schema, valid frontmatter, structured quote blocks, internal links
resolved) that nevertheless violated primary-source discipline at
every turn.

---

## Why nothing caught it

Five layers of defense, all passive:

| Layer | Worked as | Should have |
|---|---|---|
| Template | Structured slots | (nothing) |
| Scaffolder | Filled frontmatter | (nothing) |
| Build prompt | "Archive sources, cite claims" | Mandate source-read-first |
| Validator | Structural checks only | Verify quotes against source text |
| Build cadence | Allowed batch building | One node at a time |

All five layers assumed good-faith authorship. None verified it.

---

## What changed

### Fix 1 — Mechanical quote verification in `validate.py`

For every `> blockquote` followed by a verification block claiming
`✅ Confirmed — verified verbatim`, the validator now extracts the
cited source file to plaintext (`pdftotext` for PDFs, read for
HTML/TXT), normalizes whitespace and quote styles, and checks that
the quote appears as a substring. If not, an ERROR is emitted.

This alone would have turned every F1/F2/F3 fabrication in the pilot
into a commit-blocking error.

Smoke-tested 2026-04-17: a deliberately-fabricated test quote against
the archived Fravor testimony correctly errored; a real verbatim
passage from the same file verified silently.

### Fix 2 — Source-first build workflow

`prompts/build.md` now mandates:

1. Scaffold empty node
2. For each cited source: extract to plaintext first
   (`pdftotext source.pdf /tmp/scratch.txt`)
3. Build a scratchpad of verbatim passages extracted from the source
4. Fill node body ONLY from the scratchpad
5. Mark `✅ Confirmed` only after copy-paste + visual compare
6. Run `validate.py` — quote-verification check must pass

If a claim is not in the scratchpad, it is not in the node.

### Fix 3 — One-node hard limit

`CLAUDE.md` and `prompts/build.md` now document:

> **One *new* node per build session.** Do not scaffold a second node
> until the first has been fully populated, passed `validate.py`
> (including quote verification), and been committed. Parallel
> *construction* is the condition under which evidentiary drift is
> most likely.

Scope: the rule limits **new-node scaffolding** only. Editing,
auditing, fixing, or rebuilding nodes that already exist — including
multi-node sweeps in a single session — is unrestricted; those tasks
have their own prompts (`audit.md`, `verify-transcript.md`,
`archive-sweep.md`). The pilot failure was caused by spinning up
*fresh* nodes in parallel before any had been verified, not by
working across already-built ones.

Enforced by discipline, not tooling. Batch construction caused this
failure; the rule prevents it.

### Fix 4 — This postmortem

Preserved so the failure mode stays institutional knowledge. Reference
this document when:

- Onboarding a new contributor
- An audit finds drift of the same shape
- Anyone proposes relaxing the one-node rule
- Anyone proposes removing the quote-verification check

---

## Reference case value

This failure is worth more than the 10 broken nodes cost. It surfaced
the gap between "cosmetically-compliant node" and "evidentiarily-sound
node" before 150 nodes were rebuilt. The three mechanical/procedural
fixes close the gap. Phase 2 pilots would have continued producing
broken nodes without this discovery.

The nodes were deleted; the lesson is kept.
