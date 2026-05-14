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

When all automated retrieval routes fail (direct curl 403/402/523,
Wayback SPN failure, no useful CDX coverage), **manual browser save**
preserves the source-read-first bar: open the URL in a browser, save
the rendered page, register in `sources/manifest.yaml` via
`manifest.py add` (sets sha256 + archive_status). Local archive +
sha256 carry the integrity guarantee even when Wayback insurance is
unavailable.

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

**Problem:** The HTML page returns 402 (payment required) for all
automated requests. Save Page Now returns HTTP 523 (Cloudflare block).
Wayback CDX captures often exist but contain only the React shell —
the rendered post content never lands in the snapshot because Twitter
requires client-side JS to fetch and render the Tweet payload.

**What works:**

- **`cdn.syndication.twimg.com` tweet-result endpoint** — public,
  unauthenticated, returns canonical machine-readable Tweet JSON:
  ```
  curl -sSL -A "Mozilla/5.0" -o sources/social/{slug}.json \
       "https://cdn.syndication.twimg.com/tweet-result?id={status_id}&token=a"
  ```
  The `token` parameter is required (any non-empty value works). Payload
  includes:
  - `text` — full tweet text with HTML entities (`&amp;`, etc.)
  - `created_at` — ISO 8601 UTC timestamp
  - `user.{name, screen_name, id_str}` — author identity
  - `mediaDetails[].media_url_https` — photo URL; append `?name=orig`
    for full-resolution download
  - `entities.urls[]` — expanded link cards
  - `__typename` — `Tweet` for normal posts; other values may indicate
    a deleted / protected / suspended account
  Save the JSON itself as the canonical archive (it IS the source of
  record for the post's content), then download attached photos
  separately into the same `sources/social/` directory.

- **`publish.twitter.com/oembed`** — lighter-weight alternative when
  you only need the embeddable HTML blockquote and not the full JSON
  payload:
  ```
  curl -sSL -A "Mozilla/5.0" \
       "https://publish.twitter.com/oembed?url=https://twitter.com/{handle}/status/{id}&omit_script=true"
  ```
  Returns ~1KB JSON with the post text inside an HTML `blockquote`.

- **Wayback Machine CDX check** — fallback for cases where syndication
  returns 404 (deleted / protected). Many older posts ARE captured at
  the URL level even when the rendered content isn't:
  ```
  curl -s "http://web.archive.org/cdx/search/cdx?url=twitter.com/{handle}/status/{id}&output=json&limit=3&filter=statuscode:200"
  ```
  Note: the pre-rebrand `twitter.com` URL form has more captures than
  the current `x.com` form. Even when CDX returns hits, expect
  React-shell content unless the snapshot is from the brief 2012-2014
  window when Twitter rendered server-side.

- **Manual browser save** — last resort, only if the post is deleted
  but visible in the user's own browser cache.

**Manifest convention.** Register the original `x.com` URL as the
primary; set `path` to the saved `.json` file in `sources/social/`;
`format: txt` (the JSON is text-payload — `image` is reserved for the
photos themselves); `wayback_skip: true` (the syndication URL is
synthetic and Wayback can't meaningfully snapshot it). Add the photo
file as a SEPARATE manifest entry keyed off the `pbs.twimg.com` media
URL with `format: image`.

**What doesn't work:** direct `curl`/WebFetch on `x.com` (402), Save
Page Now API (523), Wayback CDX of the `x.com` HTML page (React-shell
only).

Surfaced: Kirkpatrick audit pass (2026-04-29) — Fugal X posts (status
1788708348340187605, 1788707062408421795) needed for Skinwalker briefing
attendance documentation; cdn.syndication endpoint returned full text +
photo metadata in two unauthenticated calls.

---

## YouTube (youtube.com)

**Problem:** Video pages are JavaScript-heavy and don't yield useful
content via `curl` or WebFetch. Video files can't be meaningfully
archived as HTML. Some IPs (cloud provider ranges, VPN exit nodes,
sustained-scraping IPs) hit YouTube's anti-bot wall and are rejected
by both `youtube-transcript-api` ("YouTube is blocking requests from
your IP") and `yt-dlp` ("Sign in to confirm you're not a bot") even
with `--cookies-from-browser` and a JS runtime in place.

**What works (in priority order):**

- **`scripts/transcribe.py URL`** — first attempt. Uses
  `youtube-transcript-api` to download captions (auto-generated or
  manual). Formats as timestamped markdown to `sources/transcripts/`.
- **`yt-dlp` with `--cookies-from-browser firefox` and a JS runtime
  (`deno`)** — second attempt. Modern yt-dlp requires a JS runtime
  to navigate YouTube's anti-bot challenge; install `deno` if missing
  (`curl -fsSL https://deno.land/install.sh | sh`). Use this path
  for full video downloads (subject to the "Large primary-source
  files (>100MB)" section below) or as a transcribe.py fallback.
- **Manual paste from YouTube's "Show transcript" UI** — fallback
  when both extraction libraries are IP-blocked. Open the video in
  a browser, click the three-dot menu → "Show transcript", select
  all, copy, paste into a file at `sources/transcripts/<descriptive-name>.txt`.
  The pasted text concatenates `<H:MM:SS><spelled-out-duration><line text>`
  per line without separators (a screen-reader accessibility artifact
  of YouTube's transcript pane); strip the duration overlay with this
  Python regex before registering:

  ```python
  import re
  LINE_RE = re.compile(
      r'^'
      r'(?P<ts>\d{1,2}(?::\d{2}){1,2})'
      r'\d+\s+(?:hour|minute|second)s?'
      r'(?:,\s+\d+\s+(?:hour|minute|second)s?){0,2}'
      r'(?P<text>.*)$'
  )
  # Apply per line; replace each match with f'[{ts}] {text}'.
  ```

  Strip the trailing `Sync to video time` UI artifact at the bottom of
  the paste. Register in manifest with `format: transcript`, noting
  the manual-paste origin and the cleanup applied.

**Notes on the manual-paste discipline:**

- Auto-caption typos (`bigalow`, `lockie martin`, etc.) are preserved
  verbatim per `feedback_transcript_timestamps_in_quotes.md`. Log
  source-form-vs-canonical variances in the artifact's `naming_quirks`
  with `resolution: preserve-as-sic-in-quotes`.
- The cleaned `[H:MM:SS] text` shape matches what `transcribe.py`
  produces, so downstream tooling (verbatim-quote check, prose-drift
  tokenizer) treats the paste indistinguishably from a CLI download.
- If the video is auto-caption-derived (most), the audio-vs-caption-
  as-source-of-record framing is governed by the `transcript_provenance`
  convention (see `meta/conventions.md` "Transcript provenance and
  audit discipline"); the manual-paste path inherits the same
  per-provenance discipline.

Surfaced: 2026-05-06 Ryder build session — IP-blocked YouTube
extraction forced manual-paste fallback for the 2025-09-09 House
Oversight UAP hearing transcript; cleanup regex captured here so
the next session doesn't re-derive it.

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

## Large primary-source files (>100MB)

**Problem:** GitHub's git remote enforces a 100MB hard limit per file
and a 50MB warning threshold. Common primary-source media — full-
length video recordings, large scanned-image PDFs, audio archives —
routinely exceed both thresholds. A push containing such a file is
rejected with `GH001: Large files detected`, which forces a recovery
that strips the file from history before re-pushing.

**What works:**

- **Local archive + manifest registration only.** The local file in
  `sources/<category>/<filename>` is the integrity guarantee per
  `meta/conventions.md`; the manifest entry records the source URL
  and sha256, so anyone cloning the repo can re-download from the
  source URL and verify integrity against the recorded sha256. The
  file itself is never committed to the git remote.

- **Add the source category directory (or a specific file pattern
  within it) to `.gitignore`** so future primary sources of the same
  shape don't accidentally land in the git index. Already-tracked
  small files in the same directory remain tracked because gitignore
  does not retroactively untrack files. Example for video:

  ```
  # Video primary sources — kept locally per manifest entries
  # (URL + sha256) but excluded from git remote due to file-size
  # limits.
  sources/video/
  ```

- **The pre-commit gate `scripts/tests/file-size-check.sh`** (gate 8
  in `scripts/tests/pre-commit.sh`) walks the git index and warns on
  any file 50MB–100MB / errors on any file >100MB. The error blocks
  the commit; the warning prints but does not block. Set up before
  the first oversized primary source lands.

**Recovery if a large file was committed before the gate caught it:**

1. Add the file's directory or a specific pattern to `.gitignore`.
2. `git rm --cached <path>` — removes from the git index, preserves
   the local file.
3. `git commit --amend --no-edit` — replaces the existing commit so
   the file is no longer in history. If the commit hasn't been pushed
   yet, this is enough; otherwise force-push rewrites shared history
   and should be coordinated with collaborators (or avoided if the
   commit is already widely fetched).
4. Re-push.

**Why not Git LFS?** Git LFS would track large files via pointers and
push the actual content to a separate LFS store. It's a viable path
for repos that genuinely need versioning of large binaries. This
toolkit instead treats large primary sources as content-addressable
through their source URL + sha256 — the file is regeneratable from
the URL, and integrity is checked at extraction time. LFS adds
infrastructure dependencies without solving a problem the manifest
doesn't already solve.

Surfaced: 2026-05-06 Ryder build session — two Vimeo recordings (826
MB and 1.2 GB) were committed before the file-size discipline was
documented; push to GitHub failed; recovery via `.gitignore` +
`git rm --cached` + amend cleaned the history. Discipline codified
here and gated by `file-size-check.sh` so the failure mode doesn't
recur.

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
