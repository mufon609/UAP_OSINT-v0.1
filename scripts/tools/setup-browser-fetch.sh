#!/bin/bash
# scripts/tools/setup-browser-fetch.sh
#
# One-time setup for scripts/tools/browser-fetch.py — the generic fetcher that
# drives a real (Chromium) browser to pull assets sitting behind bot-detection
# walls (Akamai / Cloudflare) that 403 every plain HTTP client. The only piece
# that needs installing is Playwright + its Chromium build.
#
# What it puts in place:
#   1. python3-venv (apt) — required to create the project-local venv.
#   2. A project-local venv at .venv-browser/ (override with VENV_DIR=... to
#      build elsewhere, e.g. for a throwaway test) created ISOLATED — no
#      --system-site-packages. Debian/Kali ship a python3-playwright package
#      whose bundled Node driver is broken (`playwright install` fails with
#      MODULE_NOT_FOUND); with --system-site-packages, pip sees that package
#      and reports playwright "already satisfied," so the venv never gets a
#      working install. Isolating the venv forces a real pip-installed
#      playwright regardless of what the system copy claims (same lesson as
#      setup-ocr-consensus.sh's venv — see its C10 backlog note).
#   3. Everything browser-fetch.py imports, installed explicitly in the venv
#      (pip, playwright) — including PyYAML, since browser-fetch.py imports
#      lib/_common, which imports yaml, and the isolated venv can no longer
#      fall back to the system copy.
#   4. Chromium + its OS runtime libraries (`python -m playwright install
#      --with-deps chromium`), downloaded into the venv's browser cache. The
#      --with-deps apt step needs sudo; if that's unavailable the script falls
#      back to a no-deps browser download and verifies whether the OS libs are
#      already present (often they are on a desktop box).
#
# browser-fetch.py auto-detects .venv-browser/ and re-execs under its Python, so
# contributors never source an activate script. When .venv-browser/ is absent
# the tool still prints --help cleanly (the Playwright import is deferred) but
# errors at runtime asking you to run this. Companion to setup-face-embeddings.sh
# / setup-ocr-consensus.sh; the venvs are independent.

set -e

# Resolve repo root (this script lives at REPO_ROOT/scripts/tools/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv-browser}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "============================================================"
echo " Browser-fetch (Playwright + Chromium) dependency setup"
echo "============================================================"
echo "Repo root: $REPO_ROOT"
echo "Venv path: $VENV_DIR"
echo

# ---------------------------------------------------------------------------
# System package: python3-venv (the Chromium OS libs are handled by Playwright's
# own --with-deps below, which knows the exact apt set per distro).
# ---------------------------------------------------------------------------
echo "[1/4] Verify python3-venv..."
if ! python3 -c "import venv" 2>/dev/null; then
    echo "  Installing python3-venv via apt..."
    sudo apt update -qq
    sudo apt install -y python3-venv
fi
echo "  ✓ venv module present"
echo

# ---------------------------------------------------------------------------
# Create the project-local venv ISOLATED (no --system-site-packages). See the
# header note: with --system-site-packages, Debian's broken python3-playwright
# package satisfies pip's dependency check and nothing gets installed.
# ---------------------------------------------------------------------------
echo "[2/4] Project-local venv at $VENV_DIR (isolated)..."
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "  Creating venv with: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
echo "  ✓ venv Python: $($VENV_DIR/bin/python3 --version)"
echo

# ---------------------------------------------------------------------------
# pip install everything browser-fetch.py imports (playwright, plus PyYAML for
# lib/_common — the isolated venv has no system-site fallback for it), then
# fetch the Chromium browser + its OS deps. `python -m playwright install
# --with-deps chromium` apt-installs the runtime libraries Chromium needs and
# downloads the browser into the venv's cache. --with-deps uses sudo apt under
# the hood; on a box where that's unavailable, drop it and install the libs
# manually (Playwright prints the list).
# ---------------------------------------------------------------------------
echo "[3/4] pip install playwright + PyYAML (in venv, isolated — ignoring any system copy)..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install --ignore-installed playwright pyyaml
echo
echo "  Installing Chromium + OS runtime libs (downloads a browser build)..."
# Try the full --with-deps install (apt + browser). It needs sudo; in a
# non-interactive / no-sudo environment the apt step fails. Fall back to a
# no-deps browser download — the OS libs are frequently already present on a
# desktop box, and the [4/4] launch check below is the real verdict.
if ! "$VENV_DIR/bin/python3" -m playwright install --with-deps chromium; then
    echo
    echo "  --with-deps failed (typically: no sudo for the apt step)."
    echo "  Falling back to a no-deps browser download..."
    "$VENV_DIR/bin/python3" -m playwright install chromium || {
        echo "  ! browser download itself failed — see output above."
        exit 1
    }
    echo "  (If the [4/4] launch check below fails, apt-install the libraries"
    echo "   Playwright names: sudo $VENV_DIR/bin/python3 -m playwright install-deps chromium)"
fi
echo

# ---------------------------------------------------------------------------
# Verify the imports + that a Chromium launch succeeds headless.
# ---------------------------------------------------------------------------
echo "[4/4] Verify Playwright + PyYAML + headless Chromium launch (in venv):"
"$VENV_DIR/bin/python3" - <<'PY'
import yaml  # noqa: F401 — lib/_common's dependency, isolated venv has no fallback
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    b.close()
print("  ✓ PyYAML import OK")
print("  ✓ Playwright + headless Chromium OK")
PY
echo

echo "============================================================"
echo " Setup complete (if all checks passed)."
echo "============================================================"
echo
echo "browser-fetch.py auto-detects and re-launches under the venv Python:"
echo
echo "  python3 scripts/tools/browser-fetch.py URL \\"
echo "      --path government/NAME.pdf --format pdf \\"
echo "      --warm-url https://host/landing/ \\"
echo "      --extraction-type ocr-scan --wayback-skip"
echo
echo "Per-host access recipes (which warm-url, fragment->URL mapping, corpus"
echo "enumeration) live in meta/sources-access.md."
