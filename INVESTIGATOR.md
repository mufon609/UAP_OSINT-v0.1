# INVESTIGATOR.md — using the repository

*How to actually use this repository once it's populated with nodes. The
`README.md` is the what-and-why; this is how an investigator wields the
corpus, and how to read a node's evidentiary state. The mechanical query
protocol is `AGENTS.md`; the contributor build path is `CLAUDE.md`.*

---

## The problem this solves

A general-purpose language model is trained on a broad slice of public
text. On any specific, niche, fast-moving, or contested subject its
knowledge is thin, dated, or averaged toward the loudest secondary
sources. Point it at such a subject cold and you get the familiar failure
modes:

- **Gaps** — it doesn't have the document, so it guesses.
- **Doubt** — it hedges or refuses, because it can't tell what's real.
- **Hallucination** — it fills the gap with plausible invention.
- **Low-quality or condescending answers** — it falls back on generic
  priors and the conventional wisdom *about* a topic rather than the
  record *of* it.

The gaps are the root cause; the other three follow from them.

---

## The fix: primary sources under a verbatim-quote policy

This repository removes the gap. Every claim is anchored to a primary
source that is archived locally and quoted character-for-character — the
verbatim-quote check enforces it mechanically (see `CLAUDE.md`). The model
is no longer reaching into a vague memory of the topic; it is reading the
actual record, with each quote traceable to a source file you can open.

Because the floor is grounded, **you control the frame.** You can tailor
`CLAUDE.md`, the persona, and the goal of a session however you want —
skeptical, narrow, adversarial, exhaustive — and the answers stay anchored
to evidence instead of drifting into the model's priors. Grounding and
framing are independent: the data keeps you honest; the frame is yours.

That grounding lets you:

- **Focus on one investigation or thread** — work the record for a single
  question without the model wandering into adjacent topics.
- **Ignore public opinion** (as distinct from policy or on-record action)
  — the corpus holds primary sources, not the discourse about them.
- **Ignore unrelated-but-similar data** — superficially close material
  that isn't part of this record stays out of the frame.
- **Keep the token window efficient** — you load the nodes that bear on
  the question, not a sprawl of half-relevant context.
- **Fine-tune a persona with consistent, data-driven results** — the same
  grounded inputs produce the same grounded outputs across sessions.

---

## What it's for

The structure makes a subject's own record legible and comparable:

- Surfacing where a public figure's on-record statements conflict with
  one another, or with primary-source evidence.
- Tracking shifting stances — and the data behind them — over time.
- Setting claims of conspiracy or fraud against what the primary record
  actually establishes, and what it does not.

In every case the repository **shows; it does not adjudicate** (see
`README.md`, "What this is not"): it lays out each side with its sources
and lets the reader weigh them. That discipline is also what makes the
corpus usable as an open-source, primary-source reporting surface —
**facts with citations, without opinion.**

---

## How to query it

Point the CLI at the node files and ask. There are two modes — @-node
composition for cross-entity synthesis, and research-artifact lookup for
exact quote provenance — both documented in `AGENTS.md` ("The investigator
workflow"). In short:

```
@people/{a} @people/{b} — what do they share in common?
@events/{e} @transcripts/{t} — does the testimony match the event record?
@findings/{f} — which primary sources back each side of the dispute?
```

Each node carries an `## Associated Nodes` section, so one @-mentioned
node fans out to the related people, organizations, documents, and events.

---

## Reading a node's evidentiary state

Nodes record source quality structurally, so you see the evidentiary
distinction before you read the content. Any section that mixes
primary-source-supported entries with secondary-source-only ones —
affiliations, relationships, organization key-personnel, event
participants — splits into two subsections:

| Subsection | Meaning |
|---|---|
| `### Confirmed` | Established from a primary source linked in the row |
| `### Flagged` | Cited in secondary sources only; awaiting primary-source confirmation |

`### Flagged` is omitted entirely when empty. The split records source
**quality, not truth**: a Flagged item may well be true — it just hasn't
been verified against a primary source yet. Treat Confirmed as the floor
you can build on, and Flagged as a lead to run down.

Which sections carry the split is defined and enforced at build time by
`meta/schema.yaml`; the above is the reader's-eye view.
