# Contributing

How to build a node. Assumes you have read `README.md`, `meta/conventions.md`,
and `meta/schema.yaml`.

---

## Hard rules

1. **One node per build session.** Do not scaffold a second node until the
   first has been fully populated, passed `validate.py` (including
   quote-verification), and been committed. Batch node construction is the
   condition under which evidentiary drift is most likely. See
   `meta/toolkit-notes/pilot-failure-2026-04-17.md` for the postmortem that established
   this rule.

2. **Source-read-first.** Every `✅ Confirmed — verified verbatim` quote
   must rest on text you extracted from the archived source file **in this
   session**. Not training knowledge. Not popular reporting. Not what you
   remember. See Step 4–6 below.

3. **Mechanical quote-verification gate.** `validate.py` extracts each
   cited source file to plaintext and checks that every quote claimed as
   verbatim appears as a substring. Errors block commit. This is a
   mechanical backstop; it does not replace Rule 2.

---

## The standard

Every claim is either **confirmed from a linked primary source** or
**explicitly flagged as unverified**. There is no middle ground. See
`README.md` "What this is" for the full epistemic definition.

---

## Before you build

1. **Check the priority queue.** `meta/topic/research-queue.md` tracks leads
   and unbuilt stubs ordered by impact.
2. **Check for existing references.** Run:
   ```
   python3 scripts/validate.py
   ```
   The broken-link registry at the bottom lists every referenced-but-unbuilt
   stub with source-tracking.
3. **Read the nodes that reference your target.** They contain claims,
   relationships, and open questions your new node needs to address.
4. **Pick the type + kind/archetype.** See section below.

---

## Choosing node type, kind, and archetype

| Type | Use for |
|---|---|
| `person` | Named individuals |
| `organization` | Government bodies, military units, private companies, nonprofits, media outlets |
| `document` | Primary source documents |
| `event` | Discrete events — hearings, encounters, disclosures |
| `transcript` | Interview or testimony transcripts linked to source |
| `media` | Photos, videos, audio, and other non-text-native primary sources |
| `location` | Non-institutional physical sites |
| `finding` | Cross-entity patterns spanning 3+ nodes (see `meta/conventions.md`) |

**Person archetype** is required:

- `eyewitness` — personally observed the event
- `whistleblower` — filed a formal complaint and makes structured claims
- `institutional-actor` — significance rests on institutional role
- `reporter` — significance rests on published journalism

**Organization kind** is required:

- `gov` — government entity (departments, agencies, program offices, federal labs, military units, congressional bodies)
- `gov-contractor` — exists because of a government contract (shell LLCs, contract-research firms)
- `private` — companies, nonprofits, academic institutions, media

**Document kind** + `doc_form` (technical-report, testimony, memo, etc) are required.

**Transcript kind**: `hearing` or `other`. **Event kind**: `hearing` or `encounter`.

When in doubt, consult `meta/schema.yaml` for the authoritative list.

---

## Build a node — step by step

The authoritative procedure lives in `prompts/build.md`. The summary here
is for reference; when building, paste the prompt and follow it step by
step.

### Step 1: Scaffold the empty node

```
python3 scripts/new.py person --archetype eyewitness --slug chad-underwood --name "Chad Underwood"
```

**Do NOT fill in the body yet.** The scaffolder creates the structure.
Content comes after source extraction.

### Step 2: Archive any missing sources

For every source the node will cite:

```
# Download
curl -sL -o sources/government/example.pdf "https://..."

# Register
python3 scripts/manifest.py add https://... --path government/example.pdf
```

See `meta/sources-access.md` for blocked-site workarounds.

### Step 3: Extract every cited source to plaintext — REQUIRED

```
pdftotext -layout sources/government/example.pdf /tmp/scratch-example.txt
```

This is your working material. Content drifts into training-knowledge
territory whenever this step is skipped; the validator will then block
the commit with quote-verification errors.

### Step 4: Build a scratchpad of verbatim passages

Create `/tmp/scratchpad-{slug}.md`. For every quote or fact you plan to
cite, copy the verbatim passage from the extracted source text into the
scratchpad with a location reference (line number, page, timestamp).

**If a claim isn't in the scratchpad, it isn't in the node.**

### Step 5: Fill the node body — only from the scratchpad

Copy-paste quotes and facts from the scratchpad into the node. Character-
identical. No rephrasing, no smoothing. Every `✅ Confirmed — verified
verbatim` marker must follow a direct copy from the scratchpad.

### Step 6: Cross-reference with `[/path]`

Named entities in prose (people, organizations, documents, events) get
wrapped in `[`/path/to/target`]` format even if the target isn't built
yet. The validator tracks broken-link stubs in its registry — that's how
the research queue learns about entities that warrant future nodes.

### Step 7: Regenerate Associated Nodes

```
python3 scripts/associate.py people/chad-underwood.md
```

Auto-generated from `[/path]` references in the body. Never hand-edit.

### Step 8: Validate — quote-verification is mandatory

```
python3 scripts/validate.py
```

Exit 0 = pass (warnings OK), exit 1 = errors found. Errors block commit.

The validator mechanically checks that every quote marked `✅ Confirmed
— verified verbatim` appears in the cited source file. If a quote is
flagged, either:

- Correct the quote text to match the source exactly (by re-copying from
  the scratchpad), OR
- Downgrade the marker to `⏳ Pending` and move the questionable text
  out of block-quote format.

**Do not** silence the check by weakening markers on quotes that genuinely
are verbatim — fix the text instead.

### Step 9: Archive to Wayback + refresh build state

```
python3 scripts/archive.py
python3 scripts/build-state.py --update
```

### Step 10: Commit — one node per commit

```
git add ...
git commit -m "Add /type/slug node"
```

Then stop. Do not start another node this session.

---

## Writing confirmed claims

Every confirmed claim needs a source attribution. In tables:

```markdown
| AARO established July 20, 2022 | ✅ Confirmed | DoD press release (archived) |
```

In prose, name the source inline.

## Writing unconfirmed claims

Unconfirmed claims go in Flagged tables or as `⏳ Pending` rows, never
in confirmed prose.

```markdown
| Tim Phillips Acting Director Dec 2023 – Aug 2024 | ⏳ Pending — primary source pending |
```

## Quote verification blocks

Every direct quote requires a three-field verification table:

```markdown
> "Quoted text verbatim."

| Field | Value |
|---|---|
| Attributed to | Speaker, context, date |
| Source | [archived PDF](../sources/...) or [`/transcripts/...`] |
| Verified | ✅ Confirmed — verified verbatim against archived PDF |
```

## Contradictions

Use the right marker:

- `⚠ Disputed — unknown` — both sides assert; neither has primary-source evidence
- `❌ Contradiction` — positions contradict and at least one side has primary-source evidence

See `meta/conventions.md` for full routing (which section of which node).

---

## What NOT to do

- **Don't mark confirmed without a primary source.** "Everyone knows this" is not a source.
- **Don't write speculative prose.** Put it in Open Questions or the research queue.
- **Don't overwrite existing content.** If new info contradicts, keep the original and add alongside with Superseded By or Contradicted By.
- **Don't conflate sources.** A news article reporting a government statement is not the same as the government statement.
- **Don't add secondary-source summaries as evidence.** Use them to identify leads (research queue), never to confirm.

---

## Commit

After validation passes:

```
git add <files>
git commit -m "Add /people/chad-underwood node"
```

Keep commits focused — one node or one pass per commit where possible.
