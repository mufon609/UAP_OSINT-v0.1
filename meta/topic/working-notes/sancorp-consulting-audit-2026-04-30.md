---
id: meta/topic/working-notes/sancorp-consulting-audit-2026-04-30
type: meta
schema_version: 1
status: working-notes
created: '2026-04-30'
---

# Audit: `organizations/sancorp-consulting`

**Audited:** 2026-04-30
**Auditor scope:** README-only. No access to `meta/schema.yaml`, `meta/conventions.md`, the organization template, or `sources/manifest.yaml`. Items marked **[SCHEMA-DEPENDENT]** require validator confirmation.
**Verbatim accuracy:** Not verified — no source files were fetched. Quotes inside Key Passages are assumed faithful to their archives; the validator's verbatim-quote check (`scripts/validate.py`) is the source of truth on that.

---

## How to use this file

Work through items in order. Each item has:

- **Where** — section + line range in the source node
- **Issue** — what's wrong
- **Rule** — which README/convention principle it violates
- **Fix** — concrete action to take

Severity tiers:

1. **BLOCKER** — would fail validation or violates a stated rule outright
2. **CONVENTION** — evidentiary or structural drift from project philosophy
3. **POLISH** — accuracy or style nits

---

## BLOCKERS

### B1. Empty row inside `Key Personnel → Confirmed` table

- **Where:** lines 36–40
- **Issue:** The Confirmed table contains a single all-whitespace row `|  |  |  |  |`. This is a malformed/placeholder table, not data.
- **Rule:** README, Status markers section: "Flagged subsections are omitted when empty." Empty Confirmed subsections should be handled the same way — removed, not stubbed with empty rows.
- **Fix:** Choose one of:
  - **(preferred)** Delete the entire `## Key Personnel` section. No Sancorp internal personnel are attested in any Key Passage; the people named in the Description (Verrine, Wells, Holly) are *government* counterparties, not Sancorp employees.
  - **(alternative)** Keep the section heading and replace the table with a one-line note: `_No Sancorp personnel attested in primary sources to date._`
  - Do **not** keep the empty row.

---

### B2. Five Key Passages missing `Attributed to` field

- **Where:**
  - Section 5.2 passage, lines 322–331
  - Section 5.3 passage, lines 335–344
  - Section 5.4 passage, lines 348–358
  - Section 5.5 passage, lines 362–371
  - Section 5.6 passage, lines 375–385
- **Issue:** Every other Key Passage in the node has a three-row metadata table (`Attributed to | Source | Location`). These five have only two rows (`Source | Location`). Inconsistent structure.
- **Rule:** Schema consistency — Key Passages should have uniform metadata. **[SCHEMA-DEPENDENT]** confirm `Attributed to` is required by `meta/schema.yaml`.
- **Fix:** Add `| Attributed to | 2022-09-01 |` as the first row of each of the five metadata tables (the contract was signed September 1, 2022 per HQ003422C0094).

---

### B3. "GovCon in a Box" data cited in Description without a local archive

- **Where:** line 26, mid-paragraph: *"GovCon in a Box lists Sancorp's federal awards (...) at \$61.47M across 185 awards (First Award April 21, 2022; Last Award December 2, 2025)."*
- **Issue:** No `sources/news/govcon-in-a-box-*` archive is cited anywhere in the node, and no Key Passage attests to these aggregate numbers.
- **Rule:** README, Source preservation: *"Every external URL cited in any node is preserved through two independent mechanisms: 1. Local archive ... 2. Wayback Machine."* Citing GovCon in a Box without an archived snapshot violates this.
- **Fix:** Either
  - Archive the GovCon in a Box page to `sources/news/govcon-in-a-box-sancorp-{YYYYMMDD}.html`, register it in `sources/manifest.yaml`, add a Key Passage with the verbatim aggregate figures, then keep the prose claim; or
  - Remove the GovCon in a Box sentence entirely and reconstruct the aggregate from the Primary Contracts table (which is already primary-sourced via USAspending). The current Primary Contracts table sums to a different total than \$61.47M, so the figures need to come from one source or the other, not both.

---

### B4. Apparent contradiction between GovCon in a Box and USAspending — not flagged

- **Where:** line 26 says GovCon in a Box "First Award April 21, 2022"; lines 393–394 (Primary Contracts table) and line 419 (Timeline) record HQ003418C0123 awarded **2018-09-27**.
- **Issue:** Two primary/aggregator sources give different "first award" dates. The node silently passes both through without acknowledging the conflict.
- **Rule:** README, *What this is*: *"Contradictions are preserved, not reconciled — the repository documents what each side says and links to both."* And *Status markers*: `❌ Contradiction` is the marker for this case.
- **Fix:** Once B3 is resolved, if both sources remain in the node, mark the GovCon in a Box "First Award" claim with `❌ Contradiction` and add a brief footnote explaining that USAspending records earlier prime contracts (HQ003418C0123, 2018-09-27) while GovCon in a Box's tracking begins in 2022. Likeliest underlying cause is GovCon in a Box's data window, but per project rules do **not** adjudicate — just document both.

---

### B5. EO 14347 attributed to a budget document, not its own text

- **Where:** Timeline line 442: *"2025-09-05 | Executive Order 14347 — Department of Defense renamed Department of War; OUSD(I&S) becomes OUSW(I&S). | government-action | government/osd-op5-fy26-wayback-20260201.pdf"*
- **Issue:** The OSD OP-5 FY26 budget is a downstream document that *references* the renaming. It is not the primary source for EO 14347. Sourcing the EO itself to a budget doc fails the "primary source" standard.
- **Rule:** README, *What this is*: *"Every claim is either confirmed from a linked primary source or explicitly flagged as unverified."* The primary source for an executive order is the order's published text (Federal Register / White House).
- **Fix:**
  - Archive EO 14347 from its primary publisher to `sources/government/eo-14347-{YYYYMMDD}.{pdf,html}`, register in manifest.
  - Update the Timeline `Source` cell to point at the EO archive.
  - Optionally add a Key Passage with the verbatim renaming clause from the EO; the budget document can remain a separate corroborating Key Passage.

---

### B6. "Department of War" / "OUSW(I&S)" rename claim has no verbatim Key Passage

- **Where:** Description, line 26: *"the office and its parent department appear in 2025 source records as Office of the Under Secretary of War for Intelligence and Security and Department of War."*
- **Issue:** No Key Passage in the node verbatim shows either "Department of War" or "Under Secretary of War for Intelligence and Security." The FY26 OSD OP-5 Key Passage (lines 257–270) still uses "OUSD(I&S)." The Primary Contracts table contains "Office of the Under Secretary of War for Policy" in the description of HQ003425FE405 (line 408), but that string is not surfaced as a verbatim Key Passage.
- **Rule:** README, evidentiary philosophy: claims framed as appearing "in source records" need a verbatim primary-source attestation to be confirmed.
- **Fix:** Add a Key Passage extracting the verbatim "Under Secretary of War" / "Department of War" string from `usaspending-hq003425fe405.txt` (or another primary source where the new naming appears), with `Attributed to`, `Source`, and `Location`.

---

## CONVENTIONS

### C1. Description claims that lack a backing Key Passage

- **Where:** line 26
- **Issue:** Several specific claims appear in the Description with no Key Passage to anchor them verbatim:
  - **UEI `GRYKNJ8BGFC8`** — claimed in prose; not in any Key Passage. (HigherGov is plausibly the source — see C2.)
  - **CAGE Code `7NZQ9`** — claimed in prose and in the Overview table; not in any Key Passage.
  - **"DCAA DODAAC HAA47 audits the LH and T&M CLINs"** — specific operational claim with no Key Passage. Presumably from `foia-23-f-0905-doc-1-released.pdf` or the AARO PWS.
  - **SBA Richmond District Office's role and address** — partially attested (Section 8(a) Direct Award Key Passage at lines 170–187 covers the cognizant-office identification), but the Description states more than the passage attests.
- **Rule:** README, evidentiary philosophy: claims should be anchored to verifiable primary sources. The Key Passages section is the verbatim-attestation layer; specific claims in the Description that aren't covered there are weakly sourced.
- **Fix:** For each claim above, either add a Key Passage extracting the verbatim language from the relevant primary source, or remove the claim from the Description if it isn't load-bearing.

---

### C2. HigherGov data referenced without a Key Passage

- **Where:** line 26: *"Per HigherGov registry data the company's SBA 8(a) Certification was Graduated August 26, 2017 to March 11, 2026; it also has Service-Disabled Veteran-Owned Small Business and Veteran-Owned Small Business certifications."*
- **Issue:** The HigherGov source file (`news/highergov-sancorp-profile-20260430.html`) is registered in the Timeline (lines 417–418, 446) but there is no Key Passage extracting the verbatim HigherGov text for SBA 8(a) status, SDVOSB, VOSB, UEI, or CAGE.
- **Rule:** When prose attributes a specific claim to a named source ("Per HigherGov..."), the verbatim attestation should be in Key Passages.
- **Fix:** Add a Key Passage with verbatim text from the HigherGov profile covering the certifications, UEI, and CAGE Code in one entry.

---

### C3. Analytical/interpretive framing inside Key Passage headings

- **Where:**
  - line 46 — *"dated fourteen months before the IPMO contract award"*
  - line 58 — *"establishes Sancorp as a participant in the doctrinal-framework production layer, not only an operational vendor"*
  - line 70 — *"Architecturally significant: identifies IPMO's '(reveal and conceal)' framing — the doctrinal mission Sancorp's IPMO contract HQ003422C0064 services through 'professional, administrative, and operational support.'"*
  - line 245 — *"The architecture-handoff's framing of 'Sancorp competitor cluster' understated this..."*
  - line 257 — *"Architecturally significant: this is the L1 doctrinal anchor that the Sancorp IPMO contract chain (...) services."*
  - line 310 — *"corrects the architecture-handoff's 'USSOUTHCOM STO July 2025' attribution..."*
- **Issue:** Headings include argumentative/interpretive framing ("doctrinal-framework production layer," "Architecturally significant," "doctrinal anchor," "understated this," "corrects the attribution"). This is closer to advocacy/analysis than neutral source description.
- **Rule:** README, *What this is not*: *"Not advocacy for any conclusion."* And *What this is*: *"Source data is never overwritten."* Neutral, descriptive headings keep evidentiary distance between source and reader.
- **Fix:** Rewrite each flagged heading to neutrally describe what the passage *is* (source, date, scope), not what it *means* in the investigator's framework. Examples:
  - line 46 → `Sancorp self-attestation of INSA membership and Insider Threat Subcommittee participation, March 2021`
  - line 70 → `OSD OP-5 FY23 budget — IPMO program description ("reveal and conceal")`
  - line 257 → `OSD OP-5 FY26 budget — IPMO program description (post-EO-14347)`

---

### C4. References to "the architecture-handoff" — undefined external document

- **Where:** lines 245, 310 (Key Passage headings).
- **Issue:** The phrase "the architecture-handoff" is used as if it's a known referent, but no node, link, or definition appears anywhere in the file. A reader cannot resolve what document is being corrected.
- **Rule:** Internal cross-references in this repo go through node links (`[`/documents/...`]` etc.). External documents must be either nodes or archived sources. Floating prose references break that contract.
- **Fix:** Either
  - replace each mention with a concrete node link (e.g., `[`/documents/architecture-handoff-{slug}`]`) if the document exists in the repo;
  - rewrite the headings to remove the comparative framing entirely (preferred — see C3); or
  - if the "architecture-handoff" is private/working-notes material outside the repo, it should not be referenced inside a node at all.

---

### C5. Description paragraph 2 — IPMO establishment phrasing is misleading

- **Where:** line 28: *"supports the Influence and Perception Management Office (established March 1, 2022 per a memorandum from James A. Holly ([`/people/james-holly`]), Acting Director — see [`/documents/ipmo-notre-dame-memo-2022`])"*
- **Issue:** The Notre Dame memo's verbatim text (Key Passage lines 87–92) attributes IPMO establishment to *"direction from the Secretary of Defense (SecDef) and Under Secretary of Defense for Intelligence and Security (USD(I&S))"* — not to Holly. Holly *signed* the memo as Acting Director; he did not establish the office. The Description's "established ... per a memorandum from James A. Holly" elides this.
- **Rule:** Description prose should track what primary sources actually say. **[SCHEMA-DEPENDENT]** — `scripts/build-from-research.py` regenerates Description from the YAML research artifact, so this may need to be fixed in `/research/` rather than directly in the node.
- **Fix:** Rephrase to: *"established March 1, 2022 by direction from the Secretary of Defense and the Under Secretary of Defense for Intelligence and Security, per a memorandum signed by James A. Holly ([`/people/james-holly`]), Acting Director — see [`/documents/ipmo-notre-dame-memo-2022`]"*. If the node is built from a research artifact, edit the artifact and rerun `build-from-research.py`.

---

### C6. Status markers absent throughout

- **Where:** Whole node.
- **Issue:** None of the five status markers (`✅ Confirmed`, `⏳ Pending`, `⚠ Flagged`, `⚠ Disputed — unknown`, `❌ Contradiction`) appear anywhere in the body. Tables and Description treat all claims as implicitly confirmed.
- **Rule:** README, Status markers: these markers exist *"to document evidentiary state throughout the repository"*.
- **Fix:** **[SCHEMA-DEPENDENT]** — confirm against `meta/schema.yaml` whether organization-node tables (Primary Contracts, Timeline, Relationships, Overview) require per-row status markers, or whether the `### Confirmed` / `### Flagged` subsection split is sufficient. If per-row markers are required, add them. If subsection-only is sufficient, this is not a fix item — but the contradiction surfaced in B4 still needs `❌ Contradiction`.

---

## POLISH

### P1. Arithmetic error: "fourteen months"

- **Where:** line 46.
- **Issue:** March 2021 to June 2022 is **15 months**, not 14 (March 2021 → June 9, 2022 = 15 months and 8 days).
- **Fix:** "fifteen months." (Or remove the comparative framing entirely per C3, in which case this is moot.)

---

### P2. Inconsistent node-linking for federal agencies in Description

- **Where:** line 26: *"the Department of Defense ([`/organizations/dod`]), the General Services Administration ([`/organizations/gsa`]), the Department of the Army, the Department of Justice, the Department of the Navy, and the Missile Defense Agency ([`/organizations/mda`])"*
- **Issue:** DoD, GSA, and MDA have node links; Army, DOJ, Navy do not. No clear rationale for the asymmetry.
- **Fix:** Either link all six to their org nodes (creating stub nodes if needed) or remove all six links and treat them as plain references. Consistency either way.

---

### P3. Non-standard date in source filename

- **Where:** Key Passage line 144: `../sources/news/insa-naming-convention-20220900.pdf`
- **Issue:** `20220900` uses `00` for the day, which is not a real date. The INSA paper is dated September 2022 but the day is unspecified in the source.
- **Fix:** Pick a convention and apply consistently. Options:
  - `insa-naming-convention-202209.pdf` (drop the day when unknown)
  - `insa-naming-convention-20220901.pdf` (default to first of month)
  - Whatever `meta/conventions.md` or `meta/sources-access.md` specifies. **[SCHEMA-DEPENDENT]**.
  - Update `sources/manifest.yaml` to match.

---

### P4. Inconsistent dollar-sign escaping

- **Where:** Description (line 26) escapes `\$61.47M`, `\$11.2M`; Primary Contracts table (lines 393–409) and Timeline (lines 417+) use unescaped `$`.
- **Issue:** Cosmetic inconsistency.
- **Fix:** Pick one form. Markdown does not require escaping `$` outside math-rendering contexts. Recommend unescaping the Description occurrences to match the tables.

---

### P5. Description sentence parenthetical-depth

- **Where:** line 26: the long sentence beginning *"GovCon in a Box lists Sancorp's federal awards (under awarding agencies including ..."*
- **Issue:** Three nested parenthetical layers; readability suffers.
- **Fix:** Once B3/B4 are resolved (which will likely shorten or remove this sentence), restructure remaining content into shorter sentences. Stylistic only.

---

### P6. Source-cell formatting inconsistency between Key Passages and tables

- **Where:** Key Passages use `[archived source](../sources/...)` markdown-link form (e.g., line 54). Relationships, Primary Contracts, and Timeline tables use bare relative paths (e.g., line 393: `government/usaspending-hq003418c0123.txt`).
- **Issue:** Two source-citation formats coexist in the same node.
- **Fix:** **[SCHEMA-DEPENDENT]** — confirm against `meta/schema.yaml` whether table cells should be bare paths or markdown links. Then normalize one direction. If both are permitted, no action.

---

## Items I could not audit

- **Verbatim accuracy** of Key Passage quotes vs. archived source files. `scripts/validate.py` is the verbatim-quote gate; run it.
- **Frontmatter completeness** vs. organization template (`meta/templates/organization.md` not provided).
- **Section ordering and required sections** vs. template — current order is Overview → Description → Key Personnel → Key Passages → Primary Contracts → Timeline → Relationships → Associated Nodes; can't confirm this matches the template.
- **`sources/manifest.yaml` registration** for every cited source path. Run `scripts/manifest.py verify-paths` and `verify-checksums`.
- **Wayback submission status** for every external URL (`scripts/archive.py`).
- **Whether `/research/sancorp-consulting.yaml` exists and is in sync** with the node body. If the Description was hand-edited rather than rebuilt from research, Phase II / Phase III review will surface drift (`scripts/review-coverage.py`).
- **Whether the renamed orgs `/organizations/ousd-is`, `/organizations/aaro`, `/organizations/ipmo`, etc. actually exist as nodes** — the node assumes they do.

---

## Suggested order of operations for Claude CLI

1. Resolve **B1** (delete or annotate empty Key Personnel section) — trivial.
2. Resolve **B2** (add `Attributed to` to five Key Passages) — trivial.
3. Resolve **B3** + **B4** together (the GovCon in a Box archive question and the contradiction it creates).
4. Resolve **B5** + **B6** together (EO 14347 sourcing and the rename's verbatim attestation).
5. Walk **C1**–**C5** in order; each likely requires editing both the node body and the backing research artifact in `/research/`.
6. **C6** is a check-the-schema task before any rewriting.
7. **P1**–**P6** are quick sweeps once the structural edits are done.
8. Run `bash tests/pre-commit.sh` and post the gate results back for re-audit.
