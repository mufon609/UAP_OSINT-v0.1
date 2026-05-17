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
content via `curl` or WebFetch. Many residential / VPN / cloud IP
ranges hit YouTube's anti-bot wall and are rejected by
`youtube-transcript-api` ("YouTube is blocking requests from your
IP") and `yt-dlp` ("Sign in to confirm you're not a bot"). Cookie-
based authentication via yt-dlp consistently bypasses the block,
but `--cookies-from-browser firefox` can't extract cookies if
Firefox is running with its default cookie protections engaged.

### Canonical caption-archival workflow

**Three steps, one tool per step.** Steps 1 + 2 are one-time
per session; step 3 is per-video.

1. **Configure Firefox prereqs** (one-time setup; persistent across
   sessions until you change Firefox settings):

   - `about:preferences#privacy` → **Enhanced Tracking Protection:
     Standard** (NOT Strict — Total Cookie Protection partitioning
     hides cookies from sqlite extraction)
   - Uncheck **"Delete cookies and site data when Firefox is closed"**
   - History: **"Remember history"** (not "Never remember" /
     "Custom" with clear-on-close)
   - Log into `https://youtube.com` in a **regular** (non-private)
     window; click a video so the session writes to `cookies.sqlite`

2. **Extract cookies** via `scripts/tools/extract-firefox-cookies.py`:

   ```
   python3 scripts/tools/extract-firefox-cookies.py --output /tmp/yt-cookies.txt
   ```

   No browser extension, no manual paste, **Firefox stays open**.
   Opens `cookies.sqlite` in read-only + `immutable=1` URI mode to
   bypass Firefox's write locks; writes Netscape-format cookies.txt
   at 0600 perms. Auto-detects the default-esr profile. Reports zero-
   cookie failures with a diagnostic checklist pointing back at the
   prereqs above.

3. **Download captions** via `scripts/tools/transcribe.py URL --cookies /tmp/yt-cookies.txt`:

   `transcribe.py` tries `youtube-transcript-api` first (no cookies
   needed) when `--cookies` is absent. With `--cookies` supplied
   (or on API failure with no cookies), it falls back to yt-dlp,
   downloads JSON3 captions, converts to the canonical `[MM:SS] text`
   markdown format internally, writes to `sources/transcripts/{slug}-downloaded.md`.

   Then register in manifest as documented in the script's output:

   ```
   python3 scripts/tools/manifest.py add URL --path transcripts/{slug}-downloaded.md --format transcript
   ```

   Manually append `transcript_provenance: auto-caption` to the
   manifest entry (the `manifest.py add` CLI doesn't expose the
   field yet — minor ergonomics gap, fix-when-needed).

**After the session**, securely delete the cookies file:

```
shred -u /tmp/yt-cookies.txt
```

The cookies authenticate full Google account access, not just
YouTube. Rotate the Google session if the cookies were ever pasted
inline into a contributor-AI conversation transcript.

### Memory-only workflow (no disk write)

When you want cookies to never touch disk at all,
`extract-firefox-cookies.py --stdout` emits the cookies to stdout
and `transcribe.py --cookies -` reads them from stdin. yt-dlp
receives them via `--cookies /dev/stdin` internally; the data
flows through kernel pipe buffers, never landing in a file.

```
# Single-video chain (cookies in kernel pipe buffer only):
python3 scripts/tools/extract-firefox-cookies.py --stdout |
    python3 scripts/tools/transcribe.py URL --cookies -

# Multi-video with shell variable (cookies in bash process memory):
COOKIES=$(python3 scripts/tools/extract-firefox-cookies.py --stdout)
printf '%s' "$COOKIES" | python3 scripts/tools/transcribe.py URL1 --cookies -
printf '%s' "$COOKIES" | python3 scripts/tools/transcribe.py URL2 --cookies -
unset COOKIES   # clears the variable from shell memory
```

`printf` is a bash builtin (args not visible via `/proc/PID/cmdline`),
the pipe goes through an anonymous kernel pipe (no disk). The
shell variable lives in the bash process's address space until
`unset` or shell exit. **Do not `echo "$COOKIES"` to inspect** —
that would expose the value to your shell history.

Trade-off vs the disk-file workflow: the shell variable / pipe
disappears when the shell exits, so re-extraction is needed for
each new shell session. The disk-file workflow persists across
shell sessions but needs explicit `shred -u` cleanup.

### Last-resort fallback — manual paste from "Show transcript" UI

When even cookies-authenticated yt-dlp fails (rare; YouTube format
restrictions on specific videos, signed-out-only content, etc.):
open the video in a browser, click the three-dot menu under the
video → "Show transcript", select all in the transcript pane,
copy, paste into a file at
`sources/transcripts/<descriptive-name>.txt`. The pasted text
concatenates `<H:MM:SS><spelled-out-duration><line text>` per line
without separators (a screen-reader accessibility artifact of
YouTube's transcript pane); strip the duration overlay with this
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

Strip the trailing `Sync to video time` UI artifact at the bottom
of the paste. Register in manifest with `format: transcript`,
noting the manual-paste origin and the cleanup applied.

### Notes on the auto-caption discipline

- Auto-caption typos (`bigalow`, `lockie martin`, `latsky` for
  Lacatski, `kellerer` for Kelleher, etc.) are preserved verbatim
  per `feedback_transcript_timestamps_in_quotes.md`. Log source-
  form-vs-canonical variances in the artifact's `naming_quirks`
  with `resolution: preserve-as-sic-in-quotes`.
- All three paths above produce the same `[MM:SS] text` shape, so
  downstream tooling (verbatim-quote check, prose-drift tokenizer)
  treats them indistinguishably.
- The audio-vs-caption-as-source-of-record framing is governed by
  the `transcript_provenance` convention (see `meta/conventions.md`
  "Transcript provenance and audit discipline"); cookies-
  authenticated yt-dlp output is `auto-caption` provenance, same
  as the API path and the manual-paste fallback.

Surfaced: 2026-05-06 Ryder build session (IP-blocked extraction
forced manual-paste for the 2025-09-09 hearing transcript;
cleanup regex captured then). 2026-05-17 Lacatski Weaponized
archival session (6 episodes; cookies-extractor +
yt-dlp-fallback workflow shipped as the canonical path; manual
paste demoted to last resort).

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

## Wayback Machine fetch — fuzzy-timestamp URLs bypass anti-bot challenge

**Gotcha:** Exact-timestamp Wayback URLs of the form
`https://web.archive.org/web/{YYYYMMDDhhmmss}/{original_url}` trigger
the Wayback anti-bot challenge from automated clients. The challenge
page is a JavaScript-redirect placeholder with title "One moment,
please…" and a `setTimeout` body that reloads after 5 seconds. Without
JS execution, `curl` saves the placeholder page instead of the actual
snapshot. Tested workarounds that do NOT help: rotating User-Agent
strings, cookie-jar persistence with sleep+retry, the CDX search API
(returns 503), the Memento Time Travel API (returns empty).

**What works:** **fuzzy-timestamp URLs** like
`https://web.archive.org/web/2024/{original_url}` redirect to the
nearest available snapshot WITHOUT triggering the anti-bot challenge.
The redirect path is server-side and serves the snapshot content
directly:

```
curl -sSL --compressed -A "Mozilla/5.0 Firefox/120.0" \
     -o sources/news/foo-wayback-{YYYYMMDD}.html \
     "https://web.archive.org/web/2024/https://www.example.com/path"
```

Use a year-only fuzzy timestamp (`/web/2024/`) or a YYYYMM
(`/web/202412/`) — both work. The actual snapshot timestamp can be
read out of the response (`__wm.wombat("{original_url}","{timestamp}",
…)`); record it in the manifest entry's `note` field for provenance.

**When to use this workflow:** the live URL is HTTP 404 / dead AND
the manifest entry has `wayback_date` set (proving a snapshot exists)
AND the original URL needs to be archived locally. Without a Wayback
snapshot, fall back to manual browser save.

**Manifest update after pull:** set `status: archived`, add `path` +
`sha256` + `archived_date`, set `archive_status: 3` (both bits — local
and Wayback). The note field should explain that the local archive
is a Wayback-recovered snapshot and reference the snapshot timestamp
embedded in the page's `__wm.wombat` call.

Surfaced: Russell Targ audit (2026-05-15) — IRVA speaker bio page
required for the audit; live URL was HTTP 404; fuzzy-timestamp
Wayback URL `https://web.archive.org/web/2024/https://www.irva.org/
speaker/targ-russell` retrieved snapshot 20250123205703 cleanly.
Exact-timestamp URLs against the same path returned the anti-bot
challenge page.

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
`scripts/tools/manifest.py add`.

*No entries yet — Phase 2 pilots not started.*
