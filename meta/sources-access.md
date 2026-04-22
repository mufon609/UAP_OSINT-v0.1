---
id: meta/sources-access
type: meta
schema_version: 1
created: 2026-04-17
---

# Source Access Reference

Site-specific workarounds for primary sources that block standard
automated retrieval. Only sites with confirmed access problems are
listed here. If a source isn't here, assume standard `curl` or WebFetch
works.

When a source is blocked and no workaround exists, register it in the
manifest with status `403-blocked`, `402-blocked`, or `pending` and add
to the Manual Archival Queue at the bottom of this file.

---

## SEC EDGAR (sec.gov)

**Problem:** HTML pages (company search, filing indexes, EDGAR browse)
return 403 for automated requests regardless of user-agent.

**What works:**

- **EFTS full-text search API** — returns JSON; browser user-agent required:
  ```
  curl -sL -A "Mozilla/5.0" "https://efts.sec.gov/LATEST/search-index?q=%22Company+Name%22"
  ```
  Returns filing metadata: CIK, form types, dates, business location, SIC code.
  Filter with `&forms=1-A` or `&dateRange=custom&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD`.

- **Wayback Machine** — archived filing documents are accessible when
  SEC blocks direct access:
  1. Find the filing path via EFTS (get the ADSH number)
  2. Search Wayback CDX:
     ```
     curl -s "http://web.archive.org/cdx/search/cdx?url=sec.gov/Archives/edgar/data/{CIK}/*&output=json&limit=10&filter=statuscode:200"
     ```
  3. Download the snapshot: `https://web.archive.org/web/{timestamp}/{original_url}`

---

## Department of Defense (defense.gov / war.gov)

**Problem:** Returns 403 for all automated requests. As of 2026,
defense.gov redirects to war.gov (DoD domain rebrand).

**What works:**

- **Wayback Machine** — DoD press releases are well-archived:
  ```
  curl -s "http://web.archive.org/cdx/search/cdx?url=defense.gov/News/Releases/Release/Article/{ID}/*&output=json&limit=3&filter=statuscode:200"
  ```
  Then download the snapshot directly.

**Gotcha:** Both `defense.gov` and `war.gov` URLs may exist for the same
document. The CDX API treats them as separate entries. Record both in
the manifest if both appear in your source trail.

---

## Navy HR / NAVADMIN (mynavyhr.navy.mil)

**Problem:** Returns 403 for all automated requests. NAVADMIN documents
(promotion lists, policy messages) are plain-text files hosted here.

**What works:**

- **Wayback Machine** — NAVADMIN documents are archived:
  ```
  curl -s "http://web.archive.org/cdx/search/cdx?url=mynavyhr.navy.mil/Portals/55/Messages/NAVADMIN/*&output=json&limit=5&filter=statuscode:200"
  ```

---

## NAVAIR FOIA (navair.navy.mil)

**Problem:** Returns 403 for all automated requests.

**What works:**

- **Wayback Machine** — FOIA index pages are archived; individual
  documents may not be. Try index first; fall back to Manual Archival
  Queue if the specific document isn't in Wayback.

---

## X / Twitter (x.com)

**Problem:** Returns 402 (payment required) for all automated requests.
Save Page Now returns HTTP 523 (Cloudflare block).

**What works:**

- **Wayback Machine CDX check** — many posts ARE archived even though
  new saves fail:
  ```
  curl -s "http://web.archive.org/cdx/search/cdx?url=x.com/{handle}/status/{id}&output=json&limit=3&filter=statuscode:200"
  ```
  If a snapshot exists, download from the Wayback URL.

- **Manual browser save** — last resort. Screenshot + text copy, save
  to `sources/social/`.

**What doesn't work:** direct `curl`/WebFetch (402), Save Page Now API (523).

---

## YouTube (youtube.com)

**Problem:** Video pages are JavaScript-heavy and don't yield useful
content via `curl` or WebFetch. Video files can't be meaningfully
archived as HTML.

**What works:**

- **`scripts/transcribe.py URL`** — downloads YouTube captions (auto or
  manual) and formats as markdown with timestamps. Writes to
  `sources/transcripts/`.
- **yt-dlp** — for full video download if the node genuinely needs it.

---

## OpenCorporates (opencorporates.com)

**Problem:** Returns HAProxy CAPTCHA for automated requests.

**What works:**

- **State Secretary of State databases** — the authoritative primary
  source for corporate registrations. Each state's SoS site has its own
  access pattern; check `sources-access.md` under each state if listed.
- **Wayback Machine** — older company listings may be cached.

---

## Media.defense.gov

**Problem:** Returns 403 for automated PDF downloads.

**What works:**

- **Wayback Machine** — most media.defense.gov PDFs are archived:
  ```
  curl -s "http://web.archive.org/cdx/search/cdx?url=media.defense.gov/{path}&output=json&limit=3&filter=statuscode:200"
  ```

---

## DoD FOIA reading room (esd.whs.mil)

**Problem:** Akamai edge-blocks automated retrieval of FOIA PDFs at
`esd.whs.mil/Portals/54/Documents/FOID/Reading%20Room/` — 403 to curl
with any user-agent.

**What works:**

- **The Black Vault mirror** — John Greenewald's archive at
  `documents2.theblackvault.com/documents/osd/{case}.pdf` mirrors most
  DoD FOIA releases. Path pattern is `/osd/{case-number}.pdf` (not
  `/dod/`). Confirmed working for cases `23-F-0946` (Grusch DOPSR
  materials) and `24-F-0266` (AARO invitations to Grusch).
- Note `23-F-0946` appears in the canonical path as
  `23-F-0946-0958-1317-David_Grusch_DOPSR_Request_09-15-23.pdf` on
  esd.whs.mil but as simply `23-F-0946.pdf` on The Black Vault mirror.

---

## The Hill (thehill.com)

**Problem:** Returns 403 for all direct automated requests; Cloudflare.

**What works:**

- **Wayback Machine** — articles are reliably archived. Prefer older
  snapshots (2023-era) over newer (2024+) — newer snapshots sometimes
  honor robots.txt exclusions at replay time:
  ```
  curl -sSL -A "Mozilla/5.0" "https://web.archive.org/web/2023id_/{original_url}"
  ```

---

## NewsNation (newsnationnow.com)

**Problem:** Returns 403 for all direct automated requests; Cloudflare.

**What works:**

- **Wayback Machine, 2023-era snapshot** — most Grusch/Coulthart-era
  articles are archived with `statuscode:200` from June-August 2023.
  Use `/web/2023id_/` prefix for raw HTML (strips Wayback chrome).

**Gotcha:** Some articles (confirmed case: the "david-grusch-patriot-lue-elizondo"
URL) have only a single Wayback snapshot that was captured as HTTP 403
at origin. No retrievable form exists; register in the manifest as
`pending` or skip.

---

## house.gov subdomains

**Problem:** Mixed — some member subdomains 403 direct curl, others
respond normally. Not predictable from the subdomain name alone.

**What works:**

- **Try direct curl with desktop UA first.** Confirmed working in 2026-04
  for `burchett.house.gov`, `burlison.house.gov`, `carson.house.gov`,
  `gaetz.house.gov`. Some return 403; fall through to Wayback.
- **Wayback Machine fallback** — press releases are widely archived.

---

## Wayback Machine fetch — auto-decompress gzip

**Gotcha:** `web.archive.org` responses are gzip-encoded when the client
sets `Accept-Encoding: gzip`. `curl -sSL` WITHOUT `--compressed` saves
the gzipped bytes to disk. On-disk gzipped HTML is unreadable to
`validate.py`'s prose-drift check and token-tests produce cascading
false errors.

**What works:**

- **Always add `--compressed` to curl** when fetching from
  `web.archive.org`:
  ```
  curl -sSL --compressed -A "Mozilla/5.0" -o sources/news/foo.html \
       "https://web.archive.org/web/2023id_/{original_url}"
  ```
- **If already saved gzipped**, decompress in place:
  ```
  for f in $(find sources -name '*.html' -newer <flag>); do
    if file "$f" | grep -q gzip; then
      gunzip -c "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    fi
  done
  ```
  Then update SHA256 in manifest via `manifest.py` (or hand-edit).

Surfaced: Grusch rebuild (2026-04-22) — 5 Wayback-fetched HTMLs arrived
gzipped; decompressed post-hoc with checksum update.

---

## Adding new entries

When a new site blocks access, document it here with:

1. **Problem** — the specific failure mode (HTTP code, behavior)
2. **What works** — confirmed workaround with copy-pasteable command
3. **What doesn't work** — if non-obvious (Save Page Now fails, etc.)

If no workaround exists, record the URL in the manifest with the
appropriate block status and add to the Manual Archival Queue below.

---

## Manual Archival Queue

Sources requiring manual browser download. Save to the appropriate
`sources/` subdirectory and update `sources/manifest.yaml` via
`scripts/manifest.py add`.

*No entries yet — Phase 2 pilots not started.*
