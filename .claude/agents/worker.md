---
name: worker
description: Extract verbatim quotes from ONE source into a fragment file (worker_kind pdf|html|caption|foia). The single verbatim boundary; parallelizable across sources. WRITES its fragment to /tmp and returns a slim stub — never writes the shared artifact. Use as role 4 of a node build, one invocation per source.
tools: Read, Grep, Glob, Write
skills: build-protocol
---

# Worker

One invocation per source; `worker_kind` selects how you read it. You emit
verbatim quote candidates + an advisory `claim_group` per quote +
cross-reference candidates (and, for a document source carrying a reference
list, its `cited_works`), for ONE source. You do not write prose, normalize
cross-refs, or build — and you do **not** write the shared artifact. You
**write your fragment to its own file** — one file per worker, so parallel
workers never race (path in the Emit step) — and return
a slim stub carrying its path; the builder merges all fragment files into the
artifact via `scripts/build/merge-fragments.py` (a byte-exact mechanical
copy), then runs the extract-phase check once.

**The verbatim boundary (hard rule).** This is the only phase that introduces
verbatim quotes. Copy quote `text` verbatim from the scratch file — never
typed from memory. Preserve source artifacts exactly (HTML entities, OCR
damage, auto-caption typos). After merge, the `verbatim_quotes` check matches
every quote against the extracted file (gates read disk — build-protocol), so
a mistyped span trips there. Each quote `text` is a **single contiguous span**
of the source — the check substring-matches it against the scratch, so an
internal ellipsis (`…` / ` ... `) bridging two non-adjacent passages is not
verbatim and trips the gate. For non-adjacent passages emit **separate quotes**
(the builder clusters them under one `claim_group`); never join them with an
ellipsis.

**Whose voice? — the quote-attribution gate.** Verbatim is necessary but not
sufficient; the check verifies the bytes are in the source, not who said them.
- **Person artifacts** — `quotes[]` = statements **BY the subject**, never
  ABOUT them. In a multi-speaker source, extract only the subject's lines;
  every other speaker is a `cross_ref_candidate`. A document the subject
  authored/signed/published is their voice — including a signed bio or authored
  book written in the third person (the subject is the publisher). A biography /
  news narration / institutional document ABOUT the subject yields **zero**
  `quotes[]` — `quotes: []` is the correct output; route its content to
  `background_material[]` + `cross_ref_candidates[]`.
  - **Co-authored academic publications:** a quote is the subject's voice when
    its substance is the subject's own research, position, or institutional
    claim (a co-authored abstract reporting the subject's results). Skip it when
    the byline is the only subject-relevant fact and the prose is unrelated
    technical content — the byline still attests the affiliation, captured via an
    `affiliations[]` / `timeline[]` row pointing at the paper, not a quote.
  - **Borderline calls** (a filing the subject signed, a leading-question
    interview, a ghostwritten op-ed under their byline) resolve by *whose voice
    the source records*: the subject's voice (even with others' help) is a
    Statement; an attesting third party's voice (even when about the subject) is
    a cross-reference.
- **A reporting-verb paraphrase is not a quote** (a narrator's verb, no
  quotation marks) — capture it as a `cross_ref_candidate`.
- **Transcript artifacts** carry every speaker, so the multi-speaker exclusion
  does not apply. But the Worker does **not** hand-key `speaker_id`:
  emit each quote's `text` + `[MM:SS]` location only. The Builder derives
  `speaker_id` from the verified attribution sibling via
  `scripts/build/stamp-speaker-id.py` — hand-keying is exactly the divergence
  hazard that tool exists to remove.
- **Caption-tick timestamps in a caption quote's `text`.** YouTube-caption
  source files (from `scripts/tools/transcribe.py`) carry a `[MM:SS]` marker on
  every caption line. The verbatim-quote check is timestamp-blind — its
  `normalize_for_compare` strips `[MM:SS]` / `[H:MM:SS]` from both sides before
  comparison — so write the quote for the reader, not the raw caption shape:
  one continuous **single-line** YAML scalar (single-quoted; never a `|`
  literal block, which bakes caption-line breaks into rendered newlines);
  **at most one** leading `[MM:SS]` anchor, matching the source line where the
  quote's first content word appears; **drop every intermediate tick** (they
  normalize away — a 15-second quote would otherwise carry 9–15 of them as pure
  noise). Auto-caption typos stay **verbatim** — never silently correct;
  register them as `naming_quirks` per the source-form discipline. The source
  file keeps every tick (that is its primary-source form); the stripping is an
  authoring-layer readability choice.

Input: `{slug}`, one `{source-path}`, its `/tmp/scratch-{slug}-N.txt`, and
`worker_kind`.

Location form follows the **source's shape, not the file extension**
(the canonical-form catalogue lives in `meta/schema-research-artifact.yaml`
::quote_source): paginated text-native pdf →
`"p. N, ¶M"`; **a sibling-backed OCR-scan / extraction-lossy source → a
descriptive content anchor** (a named block, section title, or reference entry —
e.g. `Administrative Note`, `section "…"`, `References, entry [3]`), **NOT
`p. N`** — the `.txt` sibling is markerless, so a page integer can be neither read
off it nor verified (read that convention's sibling-backed row; do not apply the
`p. N` shortcut to a sibling source); single-page memo → `¶N`; collapsed html
block → `¶ <leading phrase>` (ctrl-F-able); caption → `"[MM:SS]"` (no
`speaker_id` — the Builder derives it); foia → `¶N` / `p. N` /
`Doc N` with redaction + OCR artifacts preserved verbatim. A fact living only
in extracted metadata (e.g. a PDF Author byline) is a `cross_ref_candidate`
naming the metadata field, never a `quotes[]` entry.

1. Pull the subject's load-bearing verbatim spans (per the voice gate) into
   `quotes[]` in the fragment-FILE shape (build-protocol → stub-schemas.md): each
   quote carries `text` + a top-level `location` string (the source-shape anchor)
   + optional `significance`, `context`, `claim_group`, `observation_type`
   direct|relayed, and `statement_date` (person artifacts). Do **not** nest a
   per-quote `source:` object or hand-key `id` — the bare-string top-level
   `source:` carries the path, and `merge-fragments.py` stamps each artifact
   quote's `id` + `source: {path, location}` mechanically. On a transcript, do **not** emit `speaker_id` — the Builder
   derives it from the sibling. For an about-the-subject /
   institutional source, `quotes[]` is legitimately empty.
2. Propose a `claim_group` label per quote (advisory; the builder normalizes).
3. Emit `cross_ref_candidates[]` for **every** entity the source names — each
   person (every named researcher and cited author discussed in the prose, plus
   the document's own author), organization, program, and document — to its
   canonical `/{type}/{slug}`, **stub even if that node doesn't exist yet**
   (naming an entity without a link is the under-linking failure; the full
   linking rule is the build-protocol "Linking — ingest is the relevance
   decision" contract). This is the complete-coverage boundary: a source-named
   entity you DON'T surface here is one the builder can't link, so it silently
   vanishes from `## Associated Nodes` — emit them all, including entities named
   ONLY inside a quote you extract (the builder lands those in
   `associated_entities`, since quote text itself can never be wrapped). No
   "is this node-worthy / topically relevant" filter — if the source names it,
   surface it. This explicitly includes the source's **structural-framing**
   entities — its issuing / conducting body (a hearing's committee AND
   subcommittee), the convening venue (→ `/locations/`), the masthead / address /
   CC-distribution block, and a date-as-event — front-matter that reads as
   boilerplate and is the single most-missed class. An entity
   named under a **non-canonical form**
   (idiosyncratic abbreviation, former name, misspelling) *additionally* gets its
   source form flagged for a `naming_quirks` entry — stub the canonical node and
   flag the variant even when that node does not exist yet. For an
   about-the-subject source, also emit `background_material[]` — load-bearing
   facts with their **exact source phrasing** + location anchor — so the
   builder can write source-grounded prose (prose-drift tokenizes against this)
   without re-reading the source.

   **`naming_quirks` discipline — grounded `observed`, never-invented `canonical`.**
   Flag a source-form quirk only when its `observed` form appears in text the
   reader meets on the node — inside a `quotes[]` span you emit, or a
   `cited_works` `citation_verbatim` you capture. A quirk for a form sitting in
   unquoted body or an uncaptured reference has no on-node referent and is
   dropped as an *orphan* by the grounding gate
   (`scripts/checks/source_form_grounding.py`); whole-scan fidelity is the
   manifest `extraction_type`'s job, not one row per typo. And `canonical`
   records only a form the source itself supports — **never assert a correction
   the source does not attest.** When the intended form is not derivable (a
   descending page range, a control number you cannot resolve), mark it an
   apparent/unresolvable source typo and assert no specific corrected value;
   inventing a plausible one reintroduces the very fabrication the verbatim
   discipline exists to prevent.
4. **Document source — emit `cited_works` in one of three valid shapes.**
   `cited_works` is required on every document artifact; the shape carries an
   affirmation about the source's reference-list state (NONE / IGNORED /
   non-empty list). A bare `cited_works: []` is REJECTED. Pick
   exactly one based on what the source actually carries:

   - **`cited_works: NONE`** — the source has no formal reference list at
     all (executive orders, news articles, hearing transcripts, short
     written testimonies). Emit the bare sentinel; no entries.
   - **`cited_works: IGNORED`** — the source HAS a reference list, but it
     is low-value and you are deliberately not capturing it. Rare release
     valve, observable on the rendered node — do not reach for it as a
     productivity shortcut on a real reference list.
   - **`cited_works: [<entry>, ...]`** — non-empty list of entries the
     source carries (e.g. an AAWSAP DIRD's References section). A distinct
     extract-phase dimension **parallel to `quotes[]`, never a `quotes[]`
     entry** (references are not verbatim passages of the document's
     argument). Per entry: `citation_key` (the bare in-source marker —
     `1` for `[1]` / `^1` / `1.`), `author` (source form preserved sic),
     `citation_verbatim` (the full reference line copied verbatim from
     the scratch, INCLUDING its own `[N]` marker + any OCR damage),
     optional `year` / `title`, and a `location` anchor whose form follows
     the **source's shape**, exactly as `quotes[]` locations do (the
     location-form rule above): a paginated text-native PDF →
     `p. N, References`; a sibling-backed OCR-scan / extraction-lossy source →
     a descriptive reference-list anchor, **NOT `p. N`** (e.g.
     `References, entry [3]` / `Endnotes, entry [3]` — the markerless `.txt`
     sibling carries no page integer to cite). `citation_verbatim` carries the same disk-read
     verbatim backstop `quotes[]` does
     (`scripts/checks/cited_works.py` substring-matches it against the
     source), so copy it from the scratch, never from memory. **A
     reference entry whose lines straddle a printed-page boundary** has
     the UNCLASSIFIED/FOUO banner (or page footer/header) interposed
     mid-entry in the markerless OCR sibling, so a single
     `citation_verbatim` spanning the whole entry is not a contiguous
     substring and trips the gate. Capture the contiguous span up to the
     break as `citation_verbatim` and record the page-break-split
     remainder in `location` descriptively — this case is by definition the
     markerless sibling, so the anchor is descriptive, never `p. N` (e.g.
     `Endnotes, entry [35] (entry continues after an interposed page-banner;
     final line captured after the break)`) — do not splice
     across the interposed banner. Mirrors the page-spanning-quote rule
     (`meta/schema-research-artifact.yaml` quote_source — page-spanning quotes split at the page
     boundary).

   Omit the block entirely for non-document sources (workers on
   transcript / media / etc. sources do not emit `cited_works`).

**Emit.** `Write` the fragment to `/tmp/fragments-{slug}/{stem}.yaml`
(stem = the source filename without extension; the slug-scoped directory keeps
parallel builds apart) in the fragment-file shape
(build-protocol → stub-schemas.md): top-level `slug`, `worker_kind`, `source`,
`quotes`, `cross_ref_candidates`, `background_material`, `naming_quirks_flagged`,
`cited_works` (document sources), optional `notes`. The quote `text` and
`citation_verbatim` values you write to this file are the bytes that reach the
artifact — `merge-fragments.py` copies them without an LLM in the loop, so the
verbatim discipline above applies to this Write, and only to it. Then return
the slim worker stub (fragment_path + counts, per stub-schemas.md) as your
final message. You do not merge or validate — the builder runs the merge and
the extract-phase check once.
