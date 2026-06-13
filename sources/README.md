# sources/ — the primary-source archive

*The Tier-1 layer: every primary source this repository quotes lives
here as an archived file, indexed by `manifest.yaml`. This is the
friendly-face index of the directory — what kinds of source the toolkit
ingests, how each kind is fetched and archived, and how a degraded
source earns a trustworthy companion before any quote is drawn from it.
Deep reference lives with the owners (`scripts/README.md` per-script,
`meta/sources-access.md` per-host, `meta/schema.yaml` for the
vocabularies); this file is navigational and points to them.*

> **Topic-neutral.** This README documents the *toolkit*, not this
> instance's subject. For the actual corpora this fork is archiving, read
> `meta/topic/overview.md` ("Primary corpora"). On a fork everything
> under the category directories empties out, but the ingestion mechanics
> below survive unchanged.

---

## 1. What lives here

```
sources/
  manifest.yaml          the archival index — every source URL + its local artifact(s)
  government/            government primary sources (PDFs, HTML, FOIA releases, JSON API dumps)
  news/                  news-article snapshots (HTML, PDF) — stored as source material;
                         the readable /documents/ node lives elsewhere
  social/                social-media post snapshots (HTML, JSON, image)
  transcripts/           downloaded captions / broadcast transcripts (.md, .txt) + their
                         speaker-attribution siblings (.yaml, -attributed.md)
  video/                 archived video (.mp4) — primary-source footage + speaker-ID source
  photo-identity-log/    baseline face crops + their own manifest.yaml (speaker-ID baselines)
```

Six category directories plus the index. The category is **provenance**,
not topic: a source goes under `government/` because a government body
published it, under `news/` because an outlet did — regardless of what it
is about. `photo-identity-log/` is special: it is not a quote source, it
is the corpus of baseline face crops the transcript speaker-ID gate
matches against, and it carries its own `manifest.yaml` schema.

**The flatness rule applies here too.** Sources sit one click into their
category directory — no per-subject nesting. The manifest entry's fields
(`extraction_type`, `transcript_provenance`, `format`) carry the
classification that nesting would otherwise impose.

---

## 2. Every source gets classified

`manifest.yaml` is a flat list of **URL entries**, each owning one or more
**artifacts** (the local renderings). The classification on each artifact
is what the rest of the pipeline reads.

### URL-entry fields
| Field | Meaning |
|---|---|
| `url` | the source URL (or a synthetic `#anchor` URL for a derived sibling) |
| `status` | `archived` · `403-blocked` · `402-blocked` · `pending` |
| `archive_status` | 2-bit: `0` none · `1` local only · `2` Wayback only · `3` both (recomputed on every write) |
| `wayback_date` | YYYY-MM-DD of the Wayback capture, when one exists |
| `wayback_skip` | `true` marks a URL Wayback can't/shouldn't capture (siblings, session-bound URLs) |
| `artifacts[]` | the archived local renderings (see below) |
| `note` | free-text provenance / access context |

### Artifact fields
| Field | Meaning |
|---|---|
| `format` | `pdf · html · txt · audio · image · video · transcript · yaml · md` |
| `path` | location under `sources/`, manifest-unique (one path ↔ one URL) |
| `archived_date` | YYYY-MM-DD the local copy was taken |
| `extraction_type` | how trustworthy the extracted text is — **see below** |
| `transcript_provenance` | for transcripts, how the text was produced — **see below** |
| `note` | extraction quirks, correction record, sibling rationale |

### `extraction_type` — can we trust `pdftotext`?
| Value | Meaning | Consequence |
|---|---|---|
| `text-native` | clean authored text layer (or HTML/plain text) | `pdftotext -layout` / direct read is sufficient. Default if absent. |
| `ocr-scan` | scanned image; text layer is OCR output | character-level corruption likely → **requires a clean-text `.txt` sibling** (§5a) |
| `extraction-lossy` | real (non-OCR) text layer, but extraction is pervasively unreliable (stenographic line-number prefixes, CMap corruption) | same consequence as `ocr-scan` → **requires a clean-text `.txt` sibling** |

### `transcript_provenance` — how was the transcript produced?
| Value | Footing | Needs attribution sibling? |
|---|---|---|
| `stenographic` | court-reporter / accredited — equivalent to text-native | no |
| `published-transcript` | outlet-published with human review | no |
| `human-corrected-caption` | machine caption, human-corrected against audio | **yes** (label-less) |
| `auto-caption` | raw machine output (YouTube auto-caption, Whisper, Otter) | **yes** (label-less) |
| `unknown` | not yet classified | **yes** — fails closed until classified |

Full vocabularies and their exact semantics: `meta/schema.yaml`
(`extraction_type`, `transcript_provenance`, `format`, `status`).

---

## 3. How a source is ingested — pick the tool by how the host fights back

Every ingestion ends the same way: **a file under `sources/{category}/`
+ a `manifest.py add` registration + a Wayback submission.** What differs
is how you get the bytes past the host. Choose the lightest tool that
works:

| If the source is… | Use | Lands at | Notes |
|---|---|---|---|
| a plain, reachable URL (PDF/HTML/JSON) | `curl`/`WebFetch` → `manifest.py add` | you choose | the default path; no special tool |
| behind an Akamai/Cloudflare JS wall (returns 403 to curl) | `scripts/tools/browser-fetch.py URL --path …` | `sources/{path}` | drives headless Chromium, fetches from inside the warmed page context; auto-registers. Per-host recipes: `meta/sources-access.md` |
| a YouTube/Vimeo **video** | `scripts/tools/download-video.py URL --slug …` | `sources/video/{slug}.mp4` | yt-dlp + in-memory Firefox cookies + JS-challenge solver; 480p default (enough for face-ID) |
| a YouTube **transcript/caption** | `scripts/tools/transcribe.py URL --slug …` | `sources/transcripts/{slug}-downloaded.md` | tries `youtube-transcript-api`, falls back to yt-dlp; `--cookies -` reads creds from stdin (never disk) |

Once the bytes are local:

1. **Register** — `python3 scripts/tools/manifest.py add URL --path … --format … [--extraction-type …] [--transcript-provenance …]`. This is the *only* sanctioned manifest write path (path-uniqueness, archive-status bits, atomic save). Use `--dry-run` first.
2. **Archive to Wayback** — `python3 scripts/tools/archive.py` submits pending URLs to the Wayback Machine. It is **CDX-first**: if a 200-status snapshot already exists it records that date rather than re-submitting (a fresh Save-Page-Now of a bot-walled origin would just capture the block page). `wayback_skip: true` entries are left alone.
3. **Extract to read** — `python3 scripts/build/extract-source.py --source {category}/{file}` renders the source to `/tmp/scratch-*.txt` with `--- page N ---` markers. **Every verbatim quote is read from this extracted text, never from training knowledge** — the source-read-first invariant, checked mechanically by `validate.py`.

The archival guarantee is the **local copy**; Wayback is insurance. A
source is only fully archived at `archive_status: 3` (both).

Per-host access workarounds (which hosts 403, which need a headed
browser, which mirror to use when the origin blocks) are catalogued in
`meta/sources-access.md` — that file is mechanics-only by rule, no
research-state findings.

---

## 4. The manifest is the writer's-only boundary

Only `manifest.py` writes `manifest.yaml`. In a `/build`, only the
**archive** role runs it. The helper fetchers (`browser-fetch.py`,
`download-video.py`) shell out to `manifest.py add` rather than editing
the YAML directly, so path-uniqueness and the archive-status bits are
enforced in exactly one place. Inspect with `manifest.py status URL`,
`pending`, `orphans`, `missing`, `summary`, `verify-paths`.

---

## 5. Degraded sources earn a verified companion ("sibling")

Two source classes can't be quoted from their raw extraction. Each gets a
**sibling** file — produced, independently verified, and registered on the
manifest under a synthetic `#anchor` URL with `wayback_skip: true` —
before any quote is drawn. Both siblings are registered via
`manifest.py add-sibling`, which derives every mechanical part (anchor
URL, paths, formats, note skeleton) from the parent and **errors if the
parent isn't registered or the sibling file isn't on disk**.

### 5a. OCR-scan → clean-text `.txt` sibling
- **Trigger:** artifact is `extraction_type: ocr-scan` or `extraction-lossy` with no `.txt` sibling.
- **Produce + verify:** `/prepare-ocr-sibling`. The **ocr-page-producer** agent reads the PDF *page images* (not the corrupt text layer), one page at a time, to per-page text; `scripts/tools/ocr-consensus.py` then confirms each load-bearing token against **PaddleOCR + Tesseract** (a different OCR modality) by ≥2-of-3 consensus, printing divergences for the **ocr-page-verifier** agent to settle.
- **Artifact:** same stem, `.txt` extension, beside the parent PDF. `extract-source.py` then prefers this sibling over `pdftotext`, but quotes still cite the PDF path.
- **Register:** `manifest.py add-sibling clean-text --parent-path … --method "VLM page-image read, confirmed against PaddleOCR + Tesseract" [--blocked-pages …]`.

### 5b. Label-less transcript → speaker-attribution `.yaml` sibling
- **Trigger:** `transcript_provenance: auto-caption` / `human-corrected-caption` / `unknown` (the labeled classes skip this).
- **Produce + verify:** `/prepare-transcript-sibling`. The **attribution-producer** agent semantically parses the transcript into turns expressed as **line ranges only** (never quoted text — the schema has no `text` field, so the source bytes can't be altered); a separate **attribution-verifier** session re-checks both sides of every boundary; `validate-speaker-attribution.py` runs the structural gate.
- **Video fold-gate (mandatory):** for video sources, `finalize-attribution.py` runs `spot-check-attribution.py` across **every** turn — face crops are matched against the `photo-identity-log/` baselines (who is on screen), and mouth-aspect-ratio decides who is *speaking* where the face is large enough to carry that signal. Any unsettled `contested-fold` verdict **blocks finalize**.
- **Artifacts:** `{stem}-attribution.yaml` (source-of-truth for `speaker_id`) + `{stem}-attributed.md` (rendered view), both in `sources/transcripts/`. Unlike the OCR sibling, this one **coexists** with the parent caption — `validate.py` still matches quote text against the unchanged caption; only `speaker_id` reads from the sibling.
- **Register:** `manifest.py add-sibling speaker-attribution --parent-path … --verified … --verify-session … --image-verification …`.

The full video → frames → faces → baselines workflow is
`scripts/tools/VIDEO-PIPELINE.md`.

---

## 6. The lifecycle, one line

**fetch** (`curl`/`browser-fetch`/`download-video`/`transcribe`) →
**register** (`manifest.py add`) → **archive** (`archive.py` → Wayback) →
**[sibling if degraded]** (`/prepare-ocr-sibling` · `/prepare-transcript-sibling`) →
**extract** (`extract-source.py` → scratch text) → **quote** (into
`meta/research/{slug}.yaml`) → **render** (`build-from-research.py` →
node body).

Steps 2–7 are owned by the `/build` pipeline
(`.claude/skills/build/SKILL.md`); the per-script reference with every
flag is `scripts/README.md`; the per-host access notes are
`meta/sources-access.md`; the field vocabularies are `meta/schema.yaml`.
