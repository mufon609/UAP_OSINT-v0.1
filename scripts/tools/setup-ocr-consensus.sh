#!/bin/bash
# scripts/tools/setup-ocr-consensus.sh
#
# One-time setup for the second OCR engine behind the multi-engine consensus
# pipeline (scripts/tools/ocr-consensus.py). The consensus pipeline produces a
# trustworthy clean-text `.txt` sibling for OCR-scan sources by cross-checking
# THREE uncorrelated votes — Tesseract (vote A), PaddleOCR (vote B), and a VLM
# page-image read (vote C) — and flagging any token the engines disagree on for
# image adjudication. Tesseract is the system OCR engine (apt: tesseract-ocr);
# the VLM vote is produced by an agent. This script installs the missing piece:
# PaddleOCR, a deep-learning OCR engine with a DIFFERENT architecture from
# Tesseract, so the two have uncorrelated failure modes (the whole point — see
# meta/conventions.md "Producing the `.txt` sibling").
#
# What it puts in place:
#   1. tesseract-ocr (apt) — vote A. Usually already present; installed if not.
#   2. poppler-utils (apt) — pdftoppm rasterizer + pdftotext (the contamination
#      signal). Assumed present (the repo already uses it); installed if not.
#   3. python3-venv (apt) — required to create the project-local venv.
#   4. apt runtime libs PaddleOCR/opencv need (libgl1, libglib2.0-0, libgomp1).
#   5. A project-local venv at .venv-ocr/ created WITH --system-site-packages
#      (PEP 668 blocks system-wide pip on Debian/Kali). --system-site-packages
#      keeps the system PyYAML / PIL importable; the venv adds paddleocr +
#      paddlepaddle (CPU) + numpy on top.
#
# ocr-consensus.py auto-detects .venv-ocr/ and re-execs under its Python, so
# contributors never source an activate script. When .venv-ocr/ is absent the
# tool still prints --help cleanly (the heavy import is deferred) but errors at
# runtime asking you to run this. Companion to setup-face-embeddings.sh; the two
# venvs are independent (PaddleOCR's footprint is heavy and kept off the face
# venv).

set -e

# Resolve repo root (this script lives at REPO_ROOT/scripts/tools/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-ocr"

echo "============================================================"
echo " Multi-engine OCR consensus dependency setup"
echo "============================================================"
echo "Repo root: $REPO_ROOT"
echo "Venv path: $VENV_DIR"
echo

# ---------------------------------------------------------------------------
# System packages: Tesseract (vote A), poppler (rasterize), venv, runtime libs
# ---------------------------------------------------------------------------
echo "[1/5] Verify system packages (tesseract + poppler + venv + runtime libs)..."
MISSING=()
command -v tesseract >/dev/null 2>&1 || MISSING+=(tesseract-ocr)
command -v pdftoppm  >/dev/null 2>&1 || MISSING+=(poppler-utils)
if ! python3 -c "import venv" 2>/dev/null; then MISSING+=(python3-venv); fi
# PaddleOCR pulls opencv (libGL) + uses libgomp; these are common gaps on a
# headless box. dpkg-query is cheap; only queue what's actually missing.
for lib in libgl1 libglib2.0-0 libgomp1; do
    dpkg-query -W -f='${Status}' "$lib" 2>/dev/null | grep -q "install ok installed" || MISSING+=("$lib")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "  Installing via apt: ${MISSING[*]}"
    sudo apt update -qq
    sudo apt install -y "${MISSING[@]}"
fi
echo "  ✓ tesseract: $(command -v tesseract) ($(tesseract --version 2>&1 | head -1))"
echo "  ✓ pdftoppm:  $(command -v pdftoppm)"
echo

# ---------------------------------------------------------------------------
# Create the project-local venv WITH system site packages
# ---------------------------------------------------------------------------
echo "[2/5] Project-local venv at $VENV_DIR (--system-site-packages)..."
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "  Creating venv..."
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
echo "  ✓ venv Python: $($VENV_DIR/bin/python3 --version)"
"$VENV_DIR/bin/python3" - <<'PY'
import importlib, sys
ok = True
for mod in ("PIL", "yaml"):
    try:
        importlib.import_module(mod)
        print(f"  ✓ system-site {mod} visible inside venv")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  ✗ {mod} NOT visible inside venv: {e}")
sys.exit(0 if ok else 1)
PY
echo

# ---------------------------------------------------------------------------
# pip install inside the venv. paddlepaddle (CPU) is the heavy wheel; paddleocr
# is the OCR pipeline on top. Pinned to the CPU build — no CUDA on this box.
# ---------------------------------------------------------------------------
echo "[3/5] pip install (inside venv) — paddlepaddle CPU wheel is large, may take several minutes..."
"$VENV_DIR/bin/pip" install --upgrade pip
echo "  Installing paddlepaddle (CPU)..."
"$VENV_DIR/bin/pip" install paddlepaddle
echo "  Installing paddleocr + numpy..."
"$VENV_DIR/bin/pip" install paddleocr numpy
echo

# ---------------------------------------------------------------------------
# Module verification + model warm-up (first PaddleOCR() downloads its models)
# ---------------------------------------------------------------------------
echo "[4/5] Python module verification (in venv):"
"$VENV_DIR/bin/python3" -c "import paddle; print(f'  paddlepaddle {paddle.__version__} OK')"
"$VENV_DIR/bin/python3" -c "import paddleocr; print('  paddleocr OK')"
"$VENV_DIR/bin/python3" -c "import numpy; print(f'  numpy {numpy.__version__} OK')"
echo

echo "[5/5] Warm the PaddleOCR models (first construction downloads them once)..."
"$VENV_DIR/bin/python3" - <<'PY'
try:
    from paddleocr import PaddleOCR
    PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
    print("  ✓ PaddleOCR detector + recognizer initialised")
except Exception as e:  # noqa: BLE001
    # Older/newer paddleocr signatures vary; a construction attempt still warms
    # the model cache. Report but don't hard-fail the setup on a kwarg mismatch.
    print(f"  (warm-up note: {e})")
PY
echo

echo "============================================================"
echo " Setup complete (if all checks passed)."
echo "============================================================"
echo
echo "ocr-consensus.py auto-detects and re-launches under the venv Python:"
echo
echo "  python3 scripts/tools/ocr-consensus.py run sources/government/NAME.pdf \\"
echo "      --vlm /tmp/NAME-vlm.txt"
echo
echo "See the /prepare-ocr-sibling skill for the full producer→consensus→adjudicate flow."
