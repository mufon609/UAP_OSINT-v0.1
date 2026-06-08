#!/usr/bin/env python3
"""browser-fetch.py — fetch a bot-walled web asset by driving a real browser,
then register it on the manifest.

Some sources sit behind anti-scraping infrastructure (Akamai / Cloudflare bot
management) that 403s every plain HTTP client — curl, wget, WebFetch, and even
a cookie-replay of a logged-in browser. The wall isn't an auth wall (no
credential to copy); it's a *fingerprint* wall: the server mints a session
token only after a real browser solves a JS sensor challenge, and binds that
token to the browser's TLS fingerprint. The only reliable way past it is to BE
a real browser. This tool drives headless Chromium (Playwright), warms the
wall on a landing page so the session token is minted, then runs ``fetch()``
from INSIDE the page context — so the browser sends the token + correct
``sec-fetch``/referer headers, not us — and streams the bytes back.

Some walls (notably Akamai) further fingerprint *headless* Chromium and 403 the
fetch anyway. The escalation: retry with ``--headed`` (the full, headed Chromium
clears it); on a display-less box the headed browser needs a virtual framebuffer,
so wrap the whole command in ``xvfb-run -a``. The 403 / verify-fail messages
restate this at the point of failure.

This is the bot-wall analog of ``download-video.py`` (which wraps yt-dlp for
media behind YouTube's JS challenge). Like that tool it lands the asset under
``sources/`` and registers it via ``manifest.py add`` so the same archival
discipline (archive_status bits, Wayback eligibility) applies uniformly.

**Topic-neutral by design.** This tool knows nothing about any particular
source, host, or subject. The caller supplies the direct asset URL, where it
lands, and the manifest fields. Per-host knowledge (which landing page to warm,
how a fragment URL maps to a direct asset URL, how to enumerate a corpus) lives
in ``meta/sources-access.md`` as a per-host access recipe — never here.

Requires Playwright + Chromium. Run ``scripts/tools/setup-browser-fetch.sh``
once to install them into ``.venv-browser/``; this tool auto-relaunches under
that venv's Python (so ``--help`` works under bare Python, before setup).

Usage:
  # Single asset (caller resolves the direct URL per the host recipe):
  python3 scripts/tools/browser-fetch.py URL \\
      --path government/NAME.pdf --format pdf \\
      --warm-url https://host/landing/ \\
      --extraction-type ocr-scan --wayback-skip --note "context for manifest"

  # Batch: a list file of  URL <TAB> path [<TAB> note]  lines:
  python3 scripts/tools/browser-fetch.py --from-list urls.tsv \\
      --warm-url https://host/landing/ --extraction-type ocr-scan --wayback-skip

  # Show what would happen without fetching:
  python3 scripts/tools/browser-fetch.py URL --path government/NAME.pdf --dry-run
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Venv auto-relaunch — same guarded re-exec idiom as active-speaker.py /
# detect-faces.py / ocr-consensus.py. Playwright + its Chromium live in
# .venv-browser/ (heavy; PEP 668 blocks system-wide pip on Debian/Kali).
# Guarded on the venv existing so --help works under bare Python before setup.
# ---------------------------------------------------------------------------
_VENV_DIR = Path(__file__).resolve().parent.parent.parent / ".venv-browser"
_VENV_PYTHON = _VENV_DIR / "bin" / "python3"
if (
    _VENV_PYTHON.is_file()
    and Path(sys.prefix).resolve() != _VENV_DIR.resolve()
    and os.environ.get("BROWSER_FETCH_VENV_ACTIVE") != "1"
):
    os.environ["BROWSER_FETCH_VENV_ACTIVE"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON)] + sys.argv)

import argparse  # noqa: E402
import base64  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from urllib.parse import urlsplit, urlunsplit  # noqa: E402

# scripts/tools/browser-fetch.py — put scripts/ on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (  # noqa: E402
    REPO_ROOT,
    SOURCES_DIR,
    compute_sha256,
    format_from_path,
)

MANIFEST_TOOL = REPO_ROOT / "scripts" / "tools" / "manifest.py"

# A browser-realistic UA. The point isn't to spoof — a real Chromium IS the
# client — but to present a current, non-headless-looking UA string.
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Assets above this size are pulled in Range chunks rather than one in-page
# base64 string, which would otherwise pin the whole file in the page's JS heap.
RANGE_THRESHOLD = 50 * 1024 * 1024
RANGE_CHUNK = 8 * 1024 * 1024

# First bytes that prove a fetched binary is the real thing, not a 403/challenge
# HTML page wearing the right filename. Keyed by manifest format.
_MAGIC = {
    "pdf": b"%PDF-",
    "image": None,  # validated by non-HTML sniff below (jpg/png/gif vary)
    "audio": None,
    "video": None,
}


def origin(url: str) -> str:
    """Scheme://host of a URL — the natural page to warm a bot-wall on when no
    explicit --warm-url is given."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/", "", ""))


def looks_like_block_page(head: bytes) -> bool:
    """True if the bytes look like an HTML error/challenge page (the shape a
    bot-wall 403 takes) rather than a binary asset."""
    sniff = head[:512].lstrip().lower()
    return (
        sniff.startswith(b"<")
        or b"<html" in sniff
        or b"access denied" in sniff
        or b"<!doctype html" in sniff
    )


def verify_asset(path: Path, fmt: str) -> bool:
    """Magic-byte / non-HTML sniff. Reject a 403 HTML page masquerading as a
    binary asset BEFORE it reaches the manifest. For text-ish formats
    (html/txt/json) we can't sniff meaningfully, so accept non-empty."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    with open(path, "rb") as fh:
        head = fh.read(512)
    magic = _MAGIC.get(fmt, "__textish__")
    if magic == "__textish__":
        return True  # html/txt/json/etc. — nothing reliable to sniff
    if magic is not None:
        return head.startswith(magic)
    # Binary format with no fixed magic (image/audio/video): the only failure
    # mode we guard is "got an HTML block page instead of the asset".
    return not looks_like_block_page(head)


def _playwright():
    """Lazy import so --help works without Playwright installed. Exits with a
    setup hint (not a traceback) when the dependency is absent."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "error: Playwright not installed. Run:\n"
            "  bash scripts/tools/setup-browser-fetch.sh\n"
            "(installs Playwright + Chromium into .venv-browser/; this tool "
            "auto-relaunches under it)."
        )
    return sync_playwright


# --- in-page fetch helpers (JavaScript run inside the warmed browser page) ---

# Whole-asset fetch: returns {ok, status, len, b64} so Python sees the HTTP
# status even on a block (a 403 body is small HTML, fine to inline).
_JS_FETCH_ALL = """
async (url) => {
  const r = await fetch(url, {credentials: 'include'});
  const buf = await r.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let bin = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return {ok: r.ok, status: r.status, len: bytes.length, b64: btoa(bin)};
}
"""

# Content-Length probe for the Range path.
_JS_PROBE = """
async (url) => {
  const r = await fetch(url, {method: 'GET', credentials: 'include',
                              headers: {'Range': 'bytes=0-0'}});
  return {status: r.status,
          cr: r.headers.get('content-range'),
          cl: r.headers.get('content-length')};
}
"""

# One Range chunk.
_JS_FETCH_RANGE = """
async (url, start, end) => {
  const r = await fetch(url, {credentials: 'include',
                              headers: {'Range': `bytes=${start}-${end}`}});
  const buf = await r.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let bin = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return {status: r.status, len: bytes.length, b64: btoa(bin)};
}
"""


def _total_length(page, url):
    """Return the asset's byte length from a Range probe, or None if the server
    doesn't report it."""
    res = page.evaluate(_JS_PROBE, url)
    cr = res.get("cr")
    if cr and "/" in cr:
        tail = cr.rsplit("/", 1)[-1]
        if tail.isdigit():
            return int(tail)
    cl = res.get("cl")
    if cl and str(cl).isdigit():
        # With a bytes=0-0 range the CL is 1; only trust it absent a range echo.
        return None
    return None


def _fetch_via_page(page, url, out_path):
    """Fetch url from within the page context, write to out_path. Picks whole
    -asset vs. Range-chunked by reported length. Raises on HTTP error."""
    total = _total_length(page, url)
    if total is not None and total > RANGE_THRESHOLD:
        print(f"  large asset ({total / 1e6:.1f} MB) — Range-chunked fetch")
        with open(out_path, "wb") as fh:
            start = 0
            while start < total:
                end = min(start + RANGE_CHUNK - 1, total - 1)
                res = page.evaluate(_JS_FETCH_RANGE, [url, start, end])
                if res["status"] not in (200, 206):
                    raise RuntimeError(
                        f"Range fetch HTTP {res['status']} at byte {start}")
                fh.write(base64.b64decode(res["b64"]))
                start = end + 1
                pct = 100.0 * start / total
                print(f"    {start / 1e6:7.1f}/{total / 1e6:.1f} MB ({pct:5.1f}%)",
                      end="\r", flush=True)
        print()
    else:
        res = page.evaluate(_JS_FETCH_ALL, url)
        if not res["ok"]:
            raise RuntimeError(
                f"in-page fetch returned HTTP {res['status']} (bot-wall block? "
                f"headless is often fingerprinted — retry with --headed; on a "
                f"display-less box wrap the command in `xvfb-run -a`)")
        with open(out_path, "wb") as fh:
            fh.write(base64.b64decode(res["b64"]))


def register(url, rel_path, fmt, *, extraction_type=None, note=None,
             wayback_skip=False, dry_run=False):
    """Shell out to manifest.py add (keeps add-discipline in one place). Runs
    under SYSTEM python3 — never sys.executable — so manifest.py resolves its
    system PyYAML rather than the bare .venv-browser interpreter."""
    add_cmd = [
        "python3", str(MANIFEST_TOOL), "add", url,
        "--path", str(rel_path), "--format", fmt,
    ]
    if extraction_type:
        add_cmd += ["--extraction-type", extraction_type]
    if wayback_skip:
        add_cmd += ["--wayback-skip"]
    if note:
        add_cmd += ["--note", note]
    if dry_run:
        add_cmd += ["--dry-run"]
    # Literal "python3" resolves via PATH to the SYSTEM interpreter (the venv
    # re-exec above replaces the process but never prepends .venv-browser/bin to
    # PATH), so manifest.py finds system PyYAML — never use sys.executable here.
    proc = subprocess.run(add_cmd)
    if proc.returncode != 0:
        print(
            "\nWARN: manifest.py add failed. Register manually with:\n"
            f"  python3 scripts/tools/manifest.py add {url!r} "
            f"--path {rel_path} --format {fmt}",
            file=sys.stderr,
        )
        return False
    return True


def read_list(list_path):
    """Parse a --from-list file: tab-separated  URL [path [note]]  per line.
    Blank lines and # comments skipped. path may be omitted only if every line
    carries one (we validate per row in main)."""
    rows = []
    for lineno, raw in enumerate(Path(list_path).read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        url = parts[0].strip()
        path = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        note = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
        rows.append((url, path, note, lineno))
    return rows


def process_one(url, rel_path, fmt, args, page_fetch):
    """Fetch + verify + register one asset. Returns True on success. `page_fetch`
    is a callable(url, out_path) so batch mode can reuse one browser context."""
    out_path = SOURCES_DIR / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Idempotency — skip the fetch if a valid asset is already on disk; still
    # (re-)register, which is idempotent at the manifest layer.
    if out_path.exists() and verify_asset(out_path, fmt):
        size_mb = out_path.stat().st_size / 1e6
        print(f"  already present ({size_mb:.1f} MB) — re-registering")
    else:
        if args.dry_run:
            print(f"  [dry-run] would fetch → {rel_path}  (format={fmt})")
            register(url, rel_path, fmt, extraction_type=args.extraction_type,
                     note=args.note, wayback_skip=args.wayback_skip, dry_run=True)
            return True
        try:
            page_fetch(url, out_path)
        except Exception as exc:  # noqa: BLE001 — isolate per-asset failures
            print(f"  FAIL fetch: {exc}", file=sys.stderr)
            if out_path.exists():
                out_path.unlink()  # never leave a partial/block page behind
            return False
        if not verify_asset(out_path, fmt):
            head = out_path.read_bytes()[:80]
            print(
                f"  FAIL verify: fetched bytes are not a valid {fmt} "
                f"(got {head!r}…) — likely a bot-wall block page. Retry with "
                f"--headed (display-less box: `xvfb-run -a python3 "
                f"scripts/tools/browser-fetch.py … --headed`).",
                file=sys.stderr,
            )
            out_path.unlink()
            return False
        size_mb = out_path.stat().st_size / 1e6
        sha = compute_sha256(out_path)
        print(f"  OK {size_mb:.1f} MB  sha256={sha[:16]}…  → {rel_path}")

    if args.skip_manifest:
        return True
    return register(url, rel_path, fmt, extraction_type=args.extraction_type,
                    note=args.note, wayback_skip=args.wayback_skip)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "url", nargs="?",
        help="Direct asset URL to fetch (resolve any landing-page fragment to "
             "the direct URL first, per the host recipe in meta/sources-access.md)")
    parser.add_argument(
        "--path",
        help="Output + manifest path under sources/ (e.g. government/NAME.pdf). "
             "Required in single-asset mode.")
    parser.add_argument(
        "--format",
        help="Manifest format (pdf|html|txt|image|video|audio|...). "
             "Default: inferred from --path extension.")
    parser.add_argument(
        "--from-list",
        help="Batch mode: a file of tab-separated  URL <TAB> path [<TAB> note]  "
             "lines (# comments + blanks skipped). Mutually exclusive with a "
             "positional URL.")
    parser.add_argument(
        "--warm-url",
        help="Page to load first so the bot-wall mints its session token before "
             "the asset fetch. Default: the asset URL's scheme://host/.")
    parser.add_argument(
        "--extraction-type",
        choices=["text-native", "ocr-scan", "extraction-lossy"],
        help="Passed through to manifest.py add (set ocr-scan for image scans).")
    parser.add_argument(
        "--note",
        help="Manifest note (single-asset mode; per-row note overrides in a list).")
    parser.add_argument(
        "--wayback-skip", action="store_true",
        help="Mark the URL ineligible for Wayback (set when the host also blocks "
             "the Internet Archive crawler — see the host recipe).")
    parser.add_argument(
        "--headed", action="store_true",
        help="Run the browser headed (visible). Fallback when a bot-wall "
             "fingerprints headless Chromium and 403s the in-page fetch. On a "
             "display-less box (no $DISPLAY) wrap the whole command in "
             "`xvfb-run -a` so headed Chromium renders off-screen.")
    parser.add_argument(
        "--rate-delay", type=float, default=2.0,
        help="Seconds to pause between assets in --from-list mode (default 2.0).")
    parser.add_argument(
        "--skip-manifest", action="store_true",
        help="Skip manifest registration (debugging; leaves the file untracked).")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be fetched + the manifest add (validated via "
             "manifest.py add --dry-run) without fetching or writing.")
    args = parser.parse_args()

    # ---- assemble the work list (single asset or batch) ----
    if args.from_list:
        if args.url:
            parser.error("provide either a positional URL or --from-list, not both")
        rows = read_list(args.from_list)
        if not rows:
            sys.exit(f"error: no usable URL lines in {args.from_list}")
        work = []
        for url, path, note, lineno in rows:
            if not path:
                sys.exit(
                    f"error: {args.from_list}:{lineno} has no path column "
                    f"(need  URL <TAB> path)")
            work.append((url, path, note))
        print(f"Batch: {len(work)} asset(s) from {args.from_list}")
    else:
        if not args.url:
            parser.error("a positional URL is required (or use --from-list)")
        if not args.path:
            parser.error("--path is required in single-asset mode")
        work = [(args.url, args.path, args.note)]

    # ---- run ----
    failures = []
    if args.dry_run:
        # No browser needed for a dry run.
        for url, path, note in work:
            fmt = args.format or format_from_path(path)
            print(f"- {url}")
            row_args = argparse.Namespace(**vars(args))
            row_args.note = note if note is not None else args.note
            if not process_one(url, path, fmt, row_args, page_fetch=None):
                failures.append(path)
    else:
        sync_playwright = _playwright()
        warm = args.warm_url or origin(work[0][0])
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=not args.headed,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                context = browser.new_context(
                    user_agent=DEFAULT_UA,
                    viewport={"width": 1366, "height": 900},
                )
                page = context.new_page()
                print(f"warming bot-wall: {warm}")
                page.goto(warm, wait_until="networkidle", timeout=60_000)

                def page_fetch(url, out_path):
                    _fetch_via_page(page, url, out_path)

                for i, (url, path, note) in enumerate(work):
                    fmt = args.format or format_from_path(path)
                    print(f"[{i + 1}/{len(work)}] {url}")
                    row_args = argparse.Namespace(**vars(args))
                    row_args.note = note if note is not None else args.note
                    ok = process_one(url, path, fmt, row_args, page_fetch=page_fetch)
                    if not ok:
                        failures.append(path)
                    if i + 1 < len(work) and args.rate_delay > 0:
                        time.sleep(args.rate_delay)
            finally:
                browser.close()

    # ---- summary ----
    done = len(work) - len(failures)
    print(f"\nDone: {done}/{len(work)} succeeded.")
    if failures:
        print(f"Failed ({len(failures)}):", file=sys.stderr)
        for p in failures:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
