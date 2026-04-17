---
id: meta/topic/addenda/aawsap-dird
type: meta
schema_version: 1
created: 2026-04-17
---

# AAWSAP DIRD Corpus Addendum

Additional structural requirements for document nodes with
`corpus: aawsap-dird` in frontmatter. Nodes inherit all `gov-doc`
requirements from `schema.yaml` and add the rules below.

This file is the template for corpus-specific addenda. When a new
primary-source corpus surfaces with its own recurring structural
requirements (e.g., a specific FOIA release series, a specific
litigation document set), create a parallel `meta/topic/addenda/{corpus}.md`
and have affected nodes set `corpus: {corpus}` in their frontmatter.

---

## Additional required frontmatter

On document nodes with `corpus: aawsap-dird`:

| Field | Format | Description |
|---|---|---|
| `dird_number` | integer | Black Vault numbering (1–37) |
| `dia_attachment_number` | integer | DIA Jan 2018 SASC list position |
| `author` | string | Primary author name |
| `icod` | date | Intelligence Cutoff Date |
| `batch` | string | Month of release, e.g., "2010-04" |
| `review_category` | `A` / `B` / `C` | See Review Status below |

---

## Additional required sections

Inserted into the node body by the scaffolder immediately before
`## Key Passages`:

### `## Review Status`

Documents the per-DIRD review status against the three-tier FY09
review regime.

**Three categories:**

- **Category A — Primary-source-confirmed outside review.** Reviewer
  excerpt quoted verbatim in DIA DWO Info Memo U-429-09 (Oct 30, 2009)
  AND/OR review mark in the Aug 24, 2009 DIA contract status briefing's
  Exchange or Sandia column. Specify which tier(s) and reference the
  primary sources.

- **Category B — Program Manager review only.** Primary-source confirmed
  via U-429-09's "has reviewed all of the papers and concurs with the
  reviews" — covering all 26 FY09 deliverables. Outside review neither
  confirmed nor disproven.

- **Category C — No primary-source review documentation.** FY10+
  delivery batch (DIA attachments #26–#37) has no archived DIA memo or
  briefing covering its review regime. Archival gap — not an
  affirmative finding in either direction.

**Format:** ~3-paragraph block stating the category designation,
primary-source citations, impact on AARO HRR Vol I §IV framing, and
reference to the AAWSAP per-deliverable tracker for full context.

---

## How addenda resolve

When `scripts/validate.py` encounters a document node with `corpus: X`,
it loads `meta/topic/addenda/X.md` and merges the addendum's required
sections and frontmatter fields with the base `gov-doc` rules.

When `scripts/new.py` scaffolds a node with `--corpus X`, it pulls the
addendum's template sections and injects them into the base template at
the documented insertion point (`<!-- CORPUS-ADDENDUM-INSERT -->`).

This keeps corpus-specific patterns out of the global schema. The base
`document` template serves DoD IG reports, NASA studies, agency
assessments, and FOIA releases uniformly; corpus-specific structure
(DIRD Review Status, or any future recurring pattern) is additive.
