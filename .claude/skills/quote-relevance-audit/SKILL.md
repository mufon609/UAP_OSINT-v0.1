---
name: quote-relevance-audit
description: Audit a node's quotes[] for load-bearing relevance to the node's subject — the content-relevance layer the verbatim and prose-drift checks don't cover (does each quote advance the subject, or is it really about another entity?). Report before applying. Use on quote-heavy nodes.
argument-hint: meta/research/{slug}.yaml
allowed-tools:
  - Read
  - Edit
  - Bash(python3 scripts/build/build-from-research.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/review-coverage.py *)
---

# Quote-relevance audit

Target artifact: **$ARGUMENTS** (ask the user if empty). This is the
*content-relevance* check the mechanical validators don't cover: verbatim
accuracy and prose-drift are already enforced; this asks whether each verbatim
quote advances the **node's subject** or whether the node has accumulated
quotes whose subject is some other entity. Especially relevant on spokesperson
institutional-actor nodes, whose role is to speak FOR an institution ABOUT
other people / programs / events.

**Hard rules.** (1) Speaker attribution is necessary but not sufficient — a
quote correctly attributed to the subject can still be the wrong home if its
content is heavily about another entity; ask *what is the quote ABOUT?*
(2) Default to keep when uncertain — source drives density; drop only when
over-extraction is visible. (3) Move detail, don't lose it — if a quote belongs
on another entity's node, surface it for transfer (if that node is built) or
add a `[`/path`]` body wrap + a `timeline[]` entry (if it's an unbuilt stub) so
the broken-link registry surfaces it as a build candidate.

1. Confirm the artifact already passes `validate-research.py` +
   `build-from-research.py` + `review-coverage.py` (a failing baseline
   confounds the relevance question).
2. Walk each `quotes[]` entry: `attributed_speaker`, `content_subject` (what
   it's primarily ABOUT), `unique_evidentiary_signal` (what it adds to the
   NODE'S subject), `decision`, one-line `rationale`.
3. Decision matrix: subject-about-subject → KEEP. subject-about-other-entity →
   keep one anchoring quote per institutional moment + surface the rest, OR
   drop and replace with a `timeline[]` entry when it adds no unique signal
   beyond a dated event, OR drop-and-move when the other entity has a built
   node. not-the-subject's-words → never on this node (a misattribution to fix).
4. Consolidation: when several quotes from one source cover one institutional
   moment, prefer one anchoring quote unless each adds a distinct signal.
5. **Report findings BEFORE applying** — present the per-quote table + a summary
   count + concrete recommended edits + any genuinely ambiguous cases for the
   user to adjudicate. Do not auto-apply drops or moves.
6. On approval: edit the artifact (drop / consolidate / add `timeline[]` with a
   `[`/path`]` wrap for any future-node entity; fold dropped siblings'
   `significance`/`context` into the surviving quote), re-render, re-run
   `review-coverage.py`, then the full pre-commit chain. The user commits.

If the same over-extraction shape recurs across many nodes, surface it as a
candidate convention or BACKLOG entry.
