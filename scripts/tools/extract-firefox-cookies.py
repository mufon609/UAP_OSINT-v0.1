#!/usr/bin/env python3
"""Extract Firefox cookies to Netscape cookies.txt format, emitted to stdout.

Stdout always. No file output. The cookies are session credentials that
authenticate full Google account access — the toolkit deliberately
doesn't write them to disk so they can't be backed up, accidentally
committed, or left lying around for the next contributor on a shared
machine. Use shell-variable capture for multi-URL workflows; cookies
live in the bash process's memory until `unset` or shell exit.

No browser extension. No manual paste. No need to close Firefox.
Opens cookies.sqlite in read-only + immutable=1 URI mode (bypasses
Firefox's write locks; reads last-committed state directly).

Status messages go to stderr so stdout stays clean for piping.

Before extraction runs, the script prints a cookie-export warning to
stderr and prompts for explicit consent (type `yes` to proceed).
Non-interactive invocations (stdin not a TTY) require the
`--accept-risks` flag to bypass the interactive prompt. The prompt
fires once per script invocation — the canonical multi-video pattern
(`COOKIES=$(extract-firefox-cookies.py)`) prompts once per session.

Canonical usage:

    # Single video:
    scripts/tools/extract-firefox-cookies.py |
        scripts/tools/transcribe.py URL --cookies -

    # Multi-video (one extract, many transcribes within one shell):
    COOKIES=$(scripts/tools/extract-firefox-cookies.py)
    printf '%s' "$COOKIES" | scripts/tools/transcribe.py URL1 --cookies -
    printf '%s' "$COOKIES" | scripts/tools/transcribe.py URL2 --cookies -
    unset COOKIES

Firefox-side prereqs (one-time setup; cookies must actually persist
to the on-disk store for sqlite3 to see them):
    1. about:preferences#privacy
       - Enhanced Tracking Protection: Standard (NOT Strict — Total
         Cookie Protection in Strict partitions the cookie store in a
         way that sqlite extraction can't follow)
       - Uncheck "Delete cookies and site data when Firefox is closed"
       - History: "Remember history" (not "Never remember")
    2. Log into the target site (e.g. YouTube) in a regular,
       non-private window
    3. Visit the site briefly so the session writes to cookies.sqlite

Then run this script while Firefox stays open.
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_DOMAIN_LIKES = ["youtube", "google", "accounts.google"]


CONSENT_WARNING = """\
═══════════════════════════════════════════════════════════════════════
  COOKIE EXPORT — read before continuing
═══════════════════════════════════════════════════════════════════════

  What this is about to do
  ------------------------
  Read Google / YouTube session cookies from your Firefox profile and
  emit them as a Netscape cookies.txt blob on stdout.

  Why it's needed
  ---------------
  YouTube blocks the unauthenticated transcript API on many residential,
  VPN, and cloud IP ranges. yt-dlp + an authenticated cookie jar reaches
  YouTube reliably where the API path fails — this is the workaround.

  What's at risk
  --------------
  These cookies are live session credentials. Anyone holding them can
  act as YOUR Google identity until the session is invalidated — full
  access to Gmail, Drive, Calendar, YouTube history, account settings,
  and every other Google service tied to the logged-in profile. Treat
  the output like a password.

  How the toolkit mitigates exposure
  ----------------------------------
  • Stdout only — no file is written. Cookies live in the shell
    process's memory and disappear on `unset` or shell exit.
  • cookies.sqlite is opened read-only + immutable; Firefox state is
    untouched.
  • Repo `.gitignore` blocks common cookie filenames.
  • Pre-commit gate (`cookies-check`) refuses commits containing
    Netscape cookies content or Google session cookies.
  • `transcribe.py` pipes cookies kernel→yt-dlp via `/dev/stdin`; no
    intermediate file ever exists.

  STRONG RECOMMENDATION — use a burner account
  --------------------------------------------
  Log into YouTube with a throwaway Google account that owns no real
  data: no meaningful mail, no Drive contents, no calendar, not linked
  to your personal/work identity. After your session, sign out (or
  "Sign out of all devices" in Google account settings) to invalidate
  the exported cookies. Do not use your primary Google account.

═══════════════════════════════════════════════════════════════════════
"""


def prompt_consent(accept_risks_flag):
    """Print the cookie-export warning and require explicit consent.

    Returns True if consent is granted, False otherwise. Interactive
    sessions (stdin is a TTY) require typing `yes`; non-interactive
    sessions require the `--accept-risks` flag.
    """
    sys.stderr.write(CONSENT_WARNING)
    sys.stderr.flush()

    if accept_risks_flag:
        print("--accept-risks supplied; skipping interactive prompt.", file=sys.stderr)
        return True

    if not sys.stdin.isatty():
        print(
            "ERROR: stdin is not a TTY (non-interactive invocation).\n"
            "Re-run with --accept-risks to acknowledge the above and proceed.",
            file=sys.stderr,
        )
        return False

    sys.stderr.write(
        "Type 'yes' to acknowledge these risks and continue. Anything else aborts.\n> "
    )
    sys.stderr.flush()
    try:
        response = input().strip().lower()
    except EOFError:
        return False
    return response == "yes"


def find_firefox_profile():
    base = Path.home() / ".mozilla" / "firefox"
    if not base.is_dir():
        return None
    for pattern in ("*.default-esr", "*.default"):
        matches = sorted(base.glob(pattern))
        if matches:
            return matches[0]
    return None


def build_cookies_text(cookies_db, domain_likes):
    """Query cookies.sqlite and return (text, count). Text is the full
    Netscape cookies.txt body including header lines."""
    domain_clauses = " OR ".join(f"host LIKE '%{d}%'" for d in domain_likes)

    # immutable=1 tells sqlite to treat the file as read-only media,
    # which bypasses Firefox's write locks. Returns last-committed
    # state (any in-flight WAL writes are ignored — fine for cookies
    # extraction; the user only needs cookies that are already persisted).
    uri = f"file:{cookies_db}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    rows = con.execute(f"""
        SELECT host, path, isSecure, expiry, name, value
        FROM moz_cookies
        WHERE {domain_clauses}
        ORDER BY host, name
    """).fetchall()
    con.close()

    lines = [
        "# Netscape HTTP Cookie File",
        "# Generated by extract-firefox-cookies.py",
        f"# Source profile: {cookies_db.parent}",
        f"# Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]
    for host, path, is_secure, expiry, name, value in rows:
        include_subs = "TRUE" if host.startswith(".") else "FALSE"
        secure = "TRUE" if is_secure else "FALSE"
        lines.append(
            f"{host}\t{include_subs}\t{path}\t{secure}\t{expiry}\t{name}\t{value}"
        )
    return "\n".join(lines) + "\n", len(rows)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="Firefox profile path (auto-detects *.default-esr if omitted)",
    )
    parser.add_argument(
        "--domain",
        action="append",
        help=(
            "Domain LIKE-pattern fragment (repeatable; default: "
            "youtube google accounts.google)"
        ),
    )
    parser.add_argument(
        "--accept-risks",
        action="store_true",
        help=(
            "Skip the interactive consent prompt (required when stdin "
            "is not a TTY; equivalent to typing 'yes' interactively). "
            "The warning text is still printed to stderr for the record."
        ),
    )
    args = parser.parse_args()

    profile = args.profile or find_firefox_profile()
    if not profile or not profile.is_dir():
        sys.exit(f"ERROR: Firefox profile not found (tried: {profile})")

    cookies_db = profile / "cookies.sqlite"
    if not cookies_db.is_file():
        sys.exit(f"ERROR: cookies.sqlite not found at {cookies_db}")

    if not prompt_consent(args.accept_risks):
        sys.exit("Aborted — consent not granted; no cookies extracted.")

    domain_likes = args.domain if args.domain else DEFAULT_DOMAIN_LIKES
    text, count = build_cookies_text(cookies_db, domain_likes)

    if count == 0:
        print(
            "ERROR: Zero cookies extracted. Likely causes:\n"
            "  - Firefox set to ETP Strict (Total Cookie Protection partitions cookies)\n"
            "  - 'Delete cookies on close' is enabled\n"
            "  - You were in a private window when logging in\n"
            "  - You haven't logged into the target site yet\n"
            "See the docstring for the full prereq checklist.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.stdout.write(text)
    print(
        f"✓ Emitted {count} cookies to stdout (profile: {profile.name})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
