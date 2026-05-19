#!/usr/bin/env python3
"""download-video.py — canonical video archival for the speaker-identification
pipeline.

Wraps yt-dlp with the known-good invocation discovered the hard way:

  --cookies-from-browser firefox     YouTube requires authenticated cookies on
                                     residential / VPN IPs. This flag reads
                                     directly from Firefox's profile in memory;
                                     no cookies file ever touches disk. The
                                     bare `--cookies -` form is dangerous —
                                     yt-dlp writes refreshed cookies back to
                                     the path argument, and `-` becomes a
                                     literal filename in the working directory.
                                     `--cookies-from-browser` avoids that path
                                     entirely.

  --remote-components ejs:github     YouTube currently uses JS challenges that
                                     yt-dlp must solve to access the actual
                                     video streams (not just thumbnails). This
                                     flag downloads yt-dlp's solver from
                                     GitHub on demand. Requires a JS runtime
                                     (deno / node / bun) — install verified
                                     by setup-photo-identity.sh.

  -f 'bv*[height<=H][ext=mp4]+ba    Default 480p mp4 + best audio, merged into
   [ext=m4a]/b[height<=H][ext=mp4]   single mp4. 480p is sufficient for face
   /b[height<=H]'                    detection at the speaker-identification
                                     scale; H configurable via --quality.

Output lands at ``sources/video/{slug}.mp4``. After download:

  1. Compute sha256 of the resulting file.
  2. Register in sources/manifest.yaml via the existing manifest.py add CLI
     (so the same add-discipline applies — archive_status bits, wayback
     submission downstream, etc.).
  3. Print extract-frames invocation as the natural next step.

Idempotent: if sources/video/{slug}.mp4 already exists, skips the download.
If the URL is already in sources/manifest.yaml, manifest.py add handles
that case (its own idempotency).

Requires yt-dlp, ffmpeg, ffprobe, and a JS runtime (deno / node / bun).
Run scripts/tools/setup-photo-identity.sh to install + verify.

See scripts/tools/VIDEO-PIPELINE.md for the full end-to-end workflow.

Usage:
  python3 scripts/tools/download-video.py URL --slug NAME
  python3 scripts/tools/download-video.py URL --slug NAME --quality 720
  python3 scripts/tools/download-video.py URL --slug NAME --note "context for manifest"
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# scripts/tools/download-video.py — scripts/ on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT, SOURCES_DIR


VIDEO_DIR = SOURCES_DIR / "video"
MANIFEST_TOOL = REPO_ROOT / "scripts" / "tools" / "manifest.py"

# JS runtimes acceptable to yt-dlp's EJS challenge solver. Listed in
# preference order — deno first because Kali / Debian ARM64 ships deno via
# the .deno installer at /home/$USER/.deno/bin/deno more commonly than node
# with the right ESM support; node second; bun last (less common).
JS_RUNTIMES = ("deno", "node", "bun")


def preflight() -> None:
    """Verify yt-dlp + ffmpeg + ffprobe + a JS runtime are available. Exit 2
    with a contributor-friendly install hint if anything's missing."""
    missing = []
    for tool in ("yt-dlp", "ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            missing.append(tool)
    if not any(shutil.which(r) for r in JS_RUNTIMES):
        missing.append(f"JS runtime (one of: {', '.join(JS_RUNTIMES)})")
    if missing:
        sys.exit(
            f"error: missing dependencies: {', '.join(missing)}.\n"
            f"  Install via: bash scripts/tools/setup-photo-identity.sh"
        )


def slug_type(s: str) -> str:
    """argparse type for kebab-case slug validation.

    Auto-lowercases input. YouTube IDs are case-sensitive in URLs
    (``kRO5jOa06Qw``) but slugs are kebab-case lowercase — pasting the URL
    ID verbatim into the slug is the natural failure mode. We lowercase and
    print a one-line notice instead of rejecting outright.
    """
    s = s.strip()
    lowered = s.lower()
    if lowered != s:
        print(
            f"note: lowercasing slug for kebab-case compliance: "
            f"{s!r} → {lowered!r}",
            file=sys.stderr,
        )
        s = lowered
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", s):
        raise argparse.ArgumentTypeError(
            f"slug must be kebab-case (lowercase letters, digits, hyphens, "
            f"starting with letter/digit); got {s!r}"
        )
    return s


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="Video URL (YouTube, Vimeo, etc.)")
    parser.add_argument(
        "--slug", type=slug_type, required=True,
        help="Kebab-case slug for the output file (sources/video/{slug}.mp4)",
    )
    parser.add_argument(
        "--quality", type=int, default=480,
        help="Maximum video height in pixels (default: 480). Higher = bigger "
             "files but more facial detail.",
    )
    parser.add_argument(
        "--note", default=None,
        help="Optional contributor note for the manifest entry",
    )
    parser.add_argument(
        "--no-cookies", action="store_true",
        help="Skip --cookies-from-browser flag (only works for sources that "
             "don't require authentication; YouTube typically rejects)",
    )
    parser.add_argument(
        "--skip-manifest", action="store_true",
        help="Skip the manifest.py add step (debugging only; leaves the "
             "downloaded file untracked in sources/manifest.yaml)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the yt-dlp command that would run without executing",
    )
    args = parser.parse_args()

    preflight()

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VIDEO_DIR / f"{args.slug}.mp4"

    # Idempotency — if file already exists, don't re-download.
    if out_path.exists():
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"Already downloaded: {out_path}  ({size_mb:.1f} MB)")
        print(f"  Re-running manifest.py add (idempotent) to ensure registration.")
    else:
        # Construct yt-dlp command. -o template uses %(ext)s so the merger
        # writes the canonical extension; we pre-create with .mp4 expectation
        # via --merge-output-format mp4.
        fmt = (
            f"bv*[height<={args.quality}][ext=mp4]+ba[ext=m4a]/"
            f"b[height<={args.quality}][ext=mp4]/"
            f"b[height<={args.quality}]"
        )
        cmd = ["yt-dlp"]
        if not args.no_cookies:
            cmd.extend(["--cookies-from-browser", "firefox"])
        cmd.extend([
            "--remote-components", "ejs:github",
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", str(VIDEO_DIR / f"{args.slug}.%(ext)s"),
            args.url,
        ])
        if args.dry_run:
            print("Would run:")
            print("  " + " ".join(repr(p) if " " in p else p for p in cmd))
            return
        print(f"Downloading: {args.url}")
        print(f"  → {out_path}")
        print(f"  quality: <= {args.quality}p")
        print(f"  cookies: {'--cookies-from-browser firefox' if not args.no_cookies else '(none)'}")
        print()
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            sys.exit(f"yt-dlp failed (exit {proc.returncode})")
        if not out_path.exists():
            sys.exit(
                f"yt-dlp returned success but {out_path} not found. "
                f"Check yt-dlp output above for the actual write path."
            )
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print()
        print(f"Downloaded: {out_path}  ({size_mb:.1f} MB)")

    # Manifest registration via manifest.py add — shells out so the existing
    # add-discipline (sha256, archive_status bits, etc.) applies uniformly.
    if not args.skip_manifest:
        rel_path = out_path.relative_to(SOURCES_DIR)
        add_cmd = [
            "python3", str(MANIFEST_TOOL), "add", args.url,
            "--path", str(rel_path), "--format", "video",
        ]
        if args.note:
            add_cmd.extend(["--note", args.note])
        print()
        print("Registering in sources/manifest.yaml...")
        proc = subprocess.run(add_cmd)
        if proc.returncode != 0:
            print(
                "\nWARN: manifest.py add failed. Manually register with:",
                file=sys.stderr,
            )
            print(
                f"  python3 scripts/tools/manifest.py add {args.url!r} "
                f"--path {rel_path} --format video",
                file=sys.stderr,
            )

    print()
    print("Next steps (see scripts/tools/VIDEO-PIPELINE.md for the full workflow):")
    rel = out_path.relative_to(REPO_ROOT)
    print(f"  python3 scripts/tools/extract-frames.py anchor --video {rel}")
    print(
        f"  python3 scripts/tools/extract-frames.py burst --video {rel} "
        f"--timestamps MM:SS,MM:SS,..."
    )


if __name__ == "__main__":
    main()
