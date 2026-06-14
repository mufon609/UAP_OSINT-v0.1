# scripts/ — canonical per-script reference

The canonical reference for every script in the toolkit. Other docs name
directories and point here; per-script detail lives only in this file.

---

## Layout — five role-labeled directories

`scripts/` is organized by caller and role, not by file type: every
script lives in exactly one of five subdirectories — no Python script
sits directly in `scripts/` itself (the no-loose-scripts rule keeps the
top of `scripts/` scannable as five role-labeled directories). New
scripts land at the tier that matches who invokes them and what role
they play:

- **`build/`** — the scaffold → render → validate pipeline + the
  validators that gate each phase (contributor-facing). Per-type
  renderers live under `build/renderers/`.
- **`tools/`** — standalone utilities, integrations, and diagnostics;
  contributor-facing but *not* part of the content-transformation
  pipeline (manifest CLI, Wayback, transcription, read-only diagnostics).
  A tool with environmental prerequisites (binaries, env vars, modules,
  browser session) fails fast at `main()` entry with a contributor-
  friendly install hint rather than deferring the check to first use.
- **`checks/`** — per-check modules; the validators under `build/` are
  thin orchestrators that import and dispatch these via explicit step
  lists. Each check is individually importable for single-check debugging.
- **`tests/`** — gate-internal infrastructure existing only to support
  the pre-commit chain (`pre-commit.sh` + its regression tests). No
  contributor invokes these directly.
- **`lib/`** — shared cross-cutting helpers imported across `build/`,
  `tools/`, and `checks/`; kept separate so the cross-script lockstep
  (same `extract_source_text`, same `STOPWORDS`) is mechanical, not
  comment-discipline-based.
In-progress exploratory queries land at `.scratch/queries/` (the
repo-root scratch tree's throwaway tier — see `.scratch/.gitignore`),
not under `scripts/`. When a query class repeats across sessions,
graduate it to `tools/` as a proper subcommand — the queries tier is the
bridge between inline scripting and a first-class CLI, not a permanent
home.

The `build/`-vs-`tools/` split is produces/transforms vs assists:
`build/` scaffolds, renders, or validates the content layer; `tools/`
syncs the manifest, archives sources, or reports read-only diagnostics
without transforming content.

---

## Build pipeline — `scripts/build/`

| Script | Purpose |
|---|---|
| `new.py` | Scaffold a node from template |
| `research-scaffold.py` | Scaffold an empty research artifact for a node |
| `extract-source.py` | Extract a primary source to plaintext (Phase I) |
| `build-from-research.py` | Regenerate a node from its research artifact (Phase II — document / person / event / transcript / media / organization / location / finding / investigation). Per-type renderers live at `scripts/build/renderers/{type}.py`; `build-from-research.py` is the orchestrator. |
| `merge-fragments.py` | Mechanically merge worker fragment files' verbatim payload (`quotes[]`, `cited_works`) into a research artifact, byte-exactly — the Builder runs this instead of retyping verbatim data (the drift surface the verbatim check exists to catch). Transports schema fields only (a fragment's judgment payload — cross-refs, background material, quirk flags, notes — is read by the Builder, never merged; prose cannot ride the transport). Stamps ids/dates/source blocks; enforces the three-state `cited_works` affirmation (bare `[]` rejected; cross-fragment shape mismatch exits `cited_works_shape_conflict`). Refuses a populated artifact unless `--append` (maintenance mode — `/augment` Shape B — continues qN/cwN numbering). ruamel round-trip per the repo pattern. `--selftest` is engine-free. |
| `stamp-speaker-id.py` | Derive transcript-quote `speaker_id` from the verified attribution sibling — the Builder runs this instead of the Worker hand-keying. Resolves each quote's `[MM:SS]` → sibling turn → speaker, aligns the artifact's `speakers[]` ids + node_links to the sibling (killing the id-divergence hazard), and stamps `speaker_id`. Transcript artifacts → derive mode; person/org → confirm mode (warn-only). Reuses the `speaker_attribution_consistency` resolution helpers; ruamel round-trip keeps unchanged artifacts byte-identical. Dry run by default; `--write` applies. |
| `review-coverage.py` | Coverage / boundary / stub-linking / description-drift review (Phase III) |
| `validate.py` | Schema, structural, and verbatim-quote validation |
| `validate-research.py` | Research-artifact structural validation |
| `validate-speaker-attribution.py` | Structural validator for speaker-attribution YAML siblings (`{slug}-attribution.yaml`) — slug/source-line-count consistency, enums, speaker/node-link refs, full line-range coverage partition, and the verified-structured-only invariant (a verified sibling carries no draft scaffolding). Gated in `pre-commit.sh`. |
| `finalize-attribution.py` | Deterministic finalizer for a verifier-passed attribution sibling — sets `verification_status: verified` + `verifier_session` and strips draft-phase scaffolding (`rationale` / `verifier_notes` / `needs_image_verification`), leaving a structured-only committed artifact. Idempotent on an already-verified sibling. **Active-speaker fold gate:** requires `--video PATH` (runs `spot-check-attribution.py` across all turns; any `contested-fold` BLOCKS finalize and routes back) or `--no-video` (explicit opt-out for a genuinely audio-only source) — no graceful skip by omission. **Fold-gate adjudication:** `--resolve-turn {line_range} --speaker sX --resolution confirmed\|corrected\|ambiguous --resolved-by agent-verifier\|contributor [--write]` applies one adjudication mechanically — relabels the turn's `speaker_id` (corrected/ambiguous; mixed exchange via `--speaker s1,s2`) and upserts the structured `image_verification[]` entry, validating turn existence, speaker ids, and resolution↔relabel agreement. The judgment is the agent's/contributor's; the write is the tool's (the sibling skill carries no Edit tool). Dry-run default. |
| `associate.py` | Regenerate `## Associated Nodes` sections from body links |
| `build-state.py` | Refresh the auto-generated `meta/build-state.md` snapshot |
| `phase_routing_parity.py` | Parity gate — every `--phase` token in `prompts/` + `.claude/` is valid per `scripts/checks/_phases.py`, and every canonical phase is documented in `.claude/skills/build-protocol/SKILL.md` |
| `renderer-coverage.py` | Coverage gate — every schema required/optional/conditional section is renderer-producible (schema sections ⊆ renderer `EMITS`). A blocking gate in `pre-commit.sh`. |

---

## Tools — `scripts/tools/`

| Script | Purpose |
|---|---|
| `manifest.py` | Manage `sources/manifest.yaml` (add, edit, status, pending, usage, orphans, missing, summary, verify-paths). `add-sibling {clean-text\|speaker-attribution}` registers a derived sibling with every mechanical part derived instead of hand-composed — the synthetic anchor URL (`{parent_url}#clean-text-transcription` / `#speaker-attribution`), `wayback_skip`, the sibling path(s) from the parent stem (speaker-attribution registers the `.yaml` source-of-truth and the rendered `-attributed.md` atomically), `archived_date`, and the note skeleton (editorial remainder rides `--details` verbatim); errors if the parent isn't registered or a sibling file is missing on disk, so the sibling↔parent pairing invariant is checked, not remembered. Single write path: delegates each registration to `add`'s machinery (path-uniqueness, sorted insert, archive_status). |
| `archive.py` | Submit URLs to the Wayback Machine |
| `browser-fetch.py` | Fetch a bot-walled web asset by driving a real browser, then register it on the manifest. Some sources sit behind fingerprint walls (Akamai / Cloudflare bot management) that 403 every plain HTTP client — curl, wget, WebFetch, even cookie replay; the server mints a session token only after a real browser solves a JS sensor challenge. Drives headless Chromium (Playwright), warms the wall on a landing page, then runs `fetch()` from inside the page context and streams the bytes back. Escalation for walls that fingerprint headless Chromium: `--headed`, wrapped in `xvfb-run -a` on a display-less box. Topic-neutral by design — per-host access recipes (which landing page to warm, URL mapping) live in `meta/sources-access.md`, never here. Self-registers the manifest entry (skip a separate `manifest.py add`). Auto-relaunches under `.venv-browser/` (`setup-browser-fetch.sh`). |
| `ocr-consensus.py` | Produce the clean-text `.txt` sibling for an OCR-scan PDF from a VLM page-image read, then confirm it against an uncorrelated tool: PaddleOCR (deep-learning OCR, a different modality, not content-blocked) re-reads the pages and is diffed against the sibling on load-bearing words/numbers only — document furniture (punctuation, bullets, banners) is never compared. Tesseract is a second opinion (a divergence flags only when both engines disagree with the sibling). Content-blocked pages are PaddleOCR-filled; `--blocked-pages` cross-checks the two engines there so an agent can VLM-verify the highest-risk tokens. The engine behind `/prepare-ocr-sibling`. Engine reads are cached under the system temp dir keyed on PDF bytes + dpi + engine versions (`--no-cache` recomputes), so `verify` re-runs after sibling corrections are near-instant — the sibling comparison itself is always recomputed. `verify` rows carry derived `~p.N` page tags. `apply {pdf} --stdin [--write]` mechanically applies a page-verifier correction list (the `LINE <n> \| FIND: … \| REPLACE: …` grammar, from stdin) to the sibling — all-or-nothing, each `FIND` must match exactly once on its stated line, dry-run default — replacing the orchestrator's hand-Edit application step (agents judge; scripts mutate). `--stamp-artifact` (run/verify) writes the `content_block` value onto the artifact's matching `primary_sources[]` entry mechanically — a surgical line edit replacing the hand-paste; a vlm-skipped sentinel from the original `run` is never overwritten. `corroborate-quotes {pdf} --artifact {yaml}` re-applies the consensus rule to just the spans the artifact quotes from this source (post-extraction, `/build` step 6b) and stamps the canonical `quote_corroboration` value — contested tokens and PaddleOCR-filled-page quotes enumerated as the auditor's page-image target list; the `quote_ocr_corroboration` check backstops presence + freshness (sibling sha / quote count) at commit. Auto-relaunches under `.venv-ocr/` (`setup-ocr-consensus.sh`). |
| `transcribe.py` | Download YouTube captions to `sources/transcripts/`. Tries `youtube-transcript-api` first; falls back to yt-dlp automatically when blocked. `--cookies -` reads cookies from stdin (canonical memory-only workflow; see `extract-firefox-cookies.py`). **Canonical timestamp format (corpus-wide standard):** its `format_timestamp` is the reference — **un-padded leading field**, `[M:SS]` under an hour, `[H:MM:SS]` at/over an hour (e.g. `[5:23]`, `[13:31]`, `[1:00:05]`) — never zero-padded `[MM:SS]` / `[HH:MM:SS]`. This is the single transcript timestamp grammar; any transcript reaching `sources/transcripts/` by another path (an external Whisper run for a non-YouTube source, a different downloader) must match it. Quote/timeline `[MM:SS]` anchors mirror the source file verbatim, so a non-conforming source propagates into research-artifact anchors and verified attribution-sibling hashes — fix the format at production, before the source lands. Three legacy files (`lucistrust-rending-veils-ryder-2017`, `nell-salt-2024`, `nell-sol-foundation-2023`) predate this convention and zero-pad; they are grandfathered — **do not retro-edit them** (their timestamps are mirrored into machine-computed sibling `source_content_hash` + research anchors; rewriting breaks both for cosmetic gain). |
| `extract-firefox-cookies.py` | Extract Firefox cookies and emit Netscape-format content to stdout for use with `transcribe.py --cookies -`. Reads `cookies.sqlite` in read-only + `immutable=1` mode so Firefox can stay open; no browser extension, no manual paste, no disk write. Auto-detects the default-esr profile. Capture into a shell variable (`COOKIES=$(...)`) for multi-video sessions; `unset COOKIES` when done. See `meta/sources-access.md` "YouTube" for the Firefox prereqs + full canonical workflow. |
| `check-vocab.py` | Pre-flight vocabulary check for prose-drift discipline — pools an artifact's primary-source significant tokens (shares `lib/_common.py`'s prose-drift tokenizer with `validate-research.py`) and reports per-input-token presence. Contributor convenience for drafting `description` / `background` / `top_relevance` / `credibility_notes` / per-entry residue `.note` fields against source vocabulary. |
| `coverage-suggest.py` | Source-coverage audit aid — for each primary source on an artifact, surfaces (a) substantive source paragraphs that no quote references and (b) capitalized terms that appear in the source but nowhere in the artifact. Forward-direction complement of the verbatim-quote check; flags likely under-extraction candidates. Read-only; contributor judges what's load-bearing vs. boilerplate. Useful at audit time on already-built nodes. |
| `route_failure.py` | Route a failing validator check to the role that owns its data fix (check → phase → role, via `scripts/checks/_phases.py`). The dissolved Error agent — consumed by the `/build` orchestrator loop; the fix target is always artifact data, never the node body. |
| `download-video.py` | Canonical video archival for the speaker-identification pipeline. yt-dlp wrapper with `--cookies-from-browser firefox` (in-memory; no cookies file ever touches disk), JS-challenge solver via `--remote-components ejs:github`, 480p mp4 default. Lands at `sources/video/{slug}.mp4`, registers via `manifest.py add`. Slugs auto-lowercased on input to tolerate uppercase YouTube IDs. |
| `extract-frames.py` | ffmpeg-based frame extraction for speaker identification. Four modes: `anchor` (8 frames spread across video duration at 5%/15%/25%/35%/50%/65%/80%/95% — overridable with `--timestamps`), `burst` (N frames over T seconds at named timestamps, tiled contact-sheet output), `sweep` (periodic bursts across a range), `transcript` (burst at each `[MM:SS]` tick of a transcript file). Always writes `index.md` for the output directory. |
| `detect-faces.py` | dlib HOG face detection + ResNet 128-d face-embedding matching + persistent identity-baseline log under `sources/photo-identity-log/`. Four subcommands: `detect` (process frames → 256×256 jpg crops, embedding-dedup + auto identity-hint), `register` (promote a labeled crop to `baselines/{identity}/ref_NN.jpg` + manifest entry), `prune` (remove crops in `crops/` matching no baseline identity), `encode-baselines` (rebuild the cached `baseline-encodings.npz`). Embeddings replaced the old Haar+pHash engine — the same/different-person distance gap eliminates the look-alike false positives pHash threshold-tuning couldn't. Auto-relaunches under `.venv-face/` (`setup-face-embeddings.sh`). The accumulating baseline set makes who-is-who mechanically resolvable across the corpus. |
| `render-speaker-transcript.py` | Deterministic markdown renderer for a speaker-attribution sibling — reads the verified `{slug}-attribution.yaml` and emits `{slug}-attributed.md`, wrapping the verbatim source bytes (by line range) with speaker labels and foreign-content markers. The YAML is source-of-truth; the `.md` is a derived view, re-runnable as a pure function of (YAML, source). |
| `spot-check-attribution.py` | Mechanical turn-by-turn cross-check of a finished speaker-attribution sibling against the source video. Samples a per-turn frame **burst** across the turn's time window and decides by **who is speaking**, not mere presence: the dlib HOG + embedding engine (via `detect-faces.py`) resolves WHO each on-screen face is, and the active-speaker engine (`active-speaker.py`, `--asd mar`, default) resolves WHICH face is talking (mouth-motion). Verdicts: `confirmed` / `confirmed-with-footnote` / `contested-fold` (another in-transcript speaker is the active speaker — the wrong-label signal) / `contested-other` / `honestly-unverified` (off-camera/voiceover speaker, or no on-camera speaker) / `inconclusive` / `no-baseline` / `n/a-foreign`. Two false-positive guards: a `MIN_FOLD_FRAMES`/`MIN_FOLD_SECONDS` floor (a brief turn can't fold) and off-camera-role awareness. CSV + stdout summary; `--frames`, `--asd`, `--mar-talk-range`, `--silence-rms`, `--embed-threshold`. Auto-relaunches under `.venv-face/`. `--asd none` falls back to the presence/dominance test. |
| `active-speaker.py` | Mouth-aspect-ratio (MAR) active-speaker detection — answers WHICH on-screen face is talking during a turn so the spot-check verifies the *speaking* attribution, not on-camera presence (the two-shot / cutaway / voiceover false-positive killer). Per frame: dlib HOG detect + 128-d ResNet embedding (identity, feeds `detect-faces.identify`) + 68-point lip MAR; across a burst, a face whose MAR *range* exceeds threshold is speaking. Window-level audio-RMS gate separates speech from b-roll/silence. Pure CPU, no GPU, no model download beyond what `face_recognition` bundles. A library for `spot-check-attribution.py`; small CLI for MAR calibration. Auto-relaunches under `.venv-face/`. |
| `setup-photo-identity.sh` | One-time idempotent installer for the frame-handling side of the video pipeline: `ffmpeg`/`ffprobe`, `python3-pil`, `yt-dlp`, a JS runtime. The dlib matching engine is a separate install (`setup-face-embeddings.sh`). Reports any missing pieces; re-runnable. |
| `setup-face-embeddings.sh` | One-time idempotent installer for the dlib face-embedding matcher behind `detect-faces.py` / `spot-check-attribution.py`: apt-installs `cmake`, creates `.venv-face/` with `--system-site-packages`, builds `dlib` from source + installs `face_recognition` + `numpy`, warms the ResNet model. Separate from `setup-photo-identity.sh` because dlib's C++ footprint is heavy and PEP 668 requires a venv. |
| `setup-browser-fetch.sh` | One-time idempotent installer for `browser-fetch.py`: `python3-venv`, a project-local `.venv-browser/` with `--system-site-packages` (PEP 668; keeps system PyYAML importable), Playwright, and Chromium (`--with-deps` when sudo is available; falls back to a no-deps browser download and verifies the OS libs). `browser-fetch.py` auto-detects the venv and re-execs under it. |
| `setup-ocr-consensus.sh` | One-time idempotent installer for the OCR engines behind `ocr-consensus.py`: `tesseract-ocr`, `poppler-utils`, the opencv runtime libs, and a project-local `.venv-ocr/` with `--system-site-packages` carrying `paddleocr` + `paddlepaddle` (CPU). PaddleOCR's architecture differs from Tesseract's, so the two engines have uncorrelated failure modes — the point of the consensus design. |

Full video-pipeline walk-through: see `scripts/tools/VIDEO-PIPELINE.md`
for the four-step workflow (download → extract frames → detect faces →
register baselines), then `spot-check-attribution.py` to cross-check an
attribution sibling against the video.

**Recovering 404'd primary sources via Wayback** — if an audit hits a
manifest entry with `status: pending` plus `wayback_date` set (live URL
dead, Wayback has a snapshot), use the fuzzy-timestamp pull workflow
in `meta/sources-access.md` "Wayback Machine fetch — fuzzy-timestamp
URLs bypass anti-bot challenge". Exact-timestamp Wayback URLs trigger
an anti-bot challenge; fuzzy-timestamp URLs (`/web/{year}/{url}`)
redirect to the nearest snapshot and serve directly.

---

## Checks — `scripts/checks/`

Every named validator check lives here as its own module; the validators
under `build/` (`validate.py`, `validate-research.py`,
`review-coverage.py`) are thin orchestrators that import and dispatch
them via explicit step lists. Each check is individually importable for
single-check debugging.

`_phases.py` is the single source of truth for the build-phase
vocabulary and the check → phase → role routing map (consumed by
`tools/route_failure.py` and the `--phase` flags on the validators). Run
`python3 scripts/checks/_phases.py --list-phases` for the live list with
descriptions.

---

## Tests — `scripts/tests/`

| Script | Purpose |
|---|---|
| `pre-commit.sh` | Canonical all-gates health check — chains every gate: help-check / test_stopwords / smoke / `merge-fragments --selftest` / `finalize-attribution --selftest` / `ocr-consensus --selftest` / `build/validate.py` / `build/validate-research.py` / `build/validate-speaker-attribution.py` / `build/review-coverage.py` / `build/build-state.py --check` / `build/associate.py --check` / `build/renderer-coverage.py` / phase-routing-parity / skills-check / file-size-check / scratch-hygiene / cookies-check. Also the blocking commit hook (un-bypassable by `--no-verify`). |
| `help-check.sh` | Confirms every `scripts/{build,tools}/*.py --help` exits 0 with no traceback — catches syntax errors, import errors, and argparse regressions. |
| `skills-check.sh` | Lint for the `.claude/` toolkit surface (skills, subagents, settings): frontmatter shape (`description:` on every SKILL.md, `name:`+`description:` on every agent), topic-neutrality (no skill/agent body hard-codes this instance's topic token — read dynamically from `meta/topic/overview.md`, so `.claude/` survives `/fork-init`), and `settings.json` validity. |
| `test_stopwords.py` | `STOPWORDS` shape + content-word regression test. |
| `smoke.py` | Fixture-based `new.py` + validator smoke tests (single-process; `ProcessPoolExecutor` over fork). |
| `file-size-check.sh` | Warn 50MB / error 100MB on git-tracked files (per `meta/sources-access.md` large-file discipline). |
| `scratch-hygiene.sh` | Verify `.scratch/` tier structure and that every entry is referenced-or-fresh — no stray top-level entry and no unreferenced entry older than the grace window. |
| `cookies-check.sh` | Block commits containing Netscape cookies content or Google session cookies in Netscape-shape rows (defensive backstop to `.gitignore` patterns). |

Before adding or modifying a script, run:

```
bash scripts/tests/help-check.sh
```
