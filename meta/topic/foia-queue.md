---
id: meta/topic/foia-queue
type: meta
---

# FOIA Queue

FOIA and Mandatory Declassification Review requests **we intend to file** but
have not sent yet. A planned request has no correspondence, so under the
repository's evidentiary standard it cannot be a `foia` node. It lives here
until it is sent.

## Lifecycle

| State | Meaning | Where it lives |
|---|---|---|
| `idea` | A records gap worth requesting; no letter yet | Row in this table |
| `drafted` | Letter text written, still being refined | `meta/topic/foia-drafts/{slug}.md` |
| `ready` | Final text agreed; waiting for the maintainer to submit | Same draft file |
| `sent` | Submitted. Build the `foia` node with the **same slug** and remove the row | `sources/foia/{slug}/` + `foia/{slug}.md` |

**The slug is fixed at `drafted` and never changes.** The letter-URL convention
(`sources/README.md`) keys letters with no public URL to the node slug, so the
draft, the sent letter, the agency correspondence and the node all share one
identifier before any tracking number exists.

When a sent request later blocks research on its response, also list it under
"Externally blocked" in `meta/topic/research-queue.md`.

## Queue

| Slug | Agency | Records sought | Serves | State | Draft |
|---|---|---|---|---|---|
| `whs-hq003426fe050-pws` | WHS Acquisition Directorate (via OSD/JS FOIA) | PWS, RFQ and award notice for BPA call order HQ003426FE050; the BPA HQ003425A0001 PWS | Confirms or refutes the flagged inference that HQ003426FE050 is Sancorp's post-January-2026 AARO support vehicle ([`/organizations/sancorp-consulting`], [`/organizations/aaro`]) | `ready` | [draft](foia-drafts/whs-hq003426fe050-pws.md) |
