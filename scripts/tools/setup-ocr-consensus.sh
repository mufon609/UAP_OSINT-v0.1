#!/bin/bash
# scripts/tools/setup-ocr-consensus.sh
#
# One-time setup for the OCR engine behind scripts/tools/ocr-consensus.py. That
# tool produces a clean-text `.txt` sibling for OCR-scan sources from a VLM
# page-image read, then CONFIRMS it against the OCR engines: PaddleOCR (a
# different modality from the VLM, and not content-blocked) re-reads the pages
# and is diffed against the sibling on the words/numbers, flagging any the
# engines disagree on for an agent to reconcile against the page image. PaddleOCR
# is the better OCR engine; Tesseract is an available second opinion. This script
# installs the missing piece: PaddleOCR, a deep-learning OCR engine with a
# DIFFERENT architecture from Tesseract, so the two have uncorrelated failure
# modes (the whole point — see .claude/skills/prepare-ocr-sibling/SKILL.md).
#
# What it puts in place:
#   1. tesseract-ocr (apt) — second-opinion OCR. Usually present; installed if not.
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

# Interpreter used to create the venv. paddlepaddle wheels can lag the newest
# CPython (e.g. no cp313 wheel yet); if `pip install paddlepaddle` below reports
# no matching wheel, re-run pointing at a 3.11/3.12 interpreter, e.g.:
#   PYTHON_BIN="$HOME/.pyenv/versions/3.11.9/bin/python" scripts/tools/setup-ocr-consensus.sh
PYTHON_BIN="${PYTHON_BIN:-python3}"

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
# PaddleOCR pulls opencv, which needs the GL + glib + gomp shared libraries.
# Detect the actual .so files via ldconfig rather than dpkg package NAMES:
# Debian/Kali's 64-bit time_t (t64) transition renamed many of these
# (libglib2.0-0 -> libglib2.0-0t64). A name check both false-alarms on the old
# name AND, if it then installs the pre-t64 package, CONFLICTS with the
# installed t64 one (the failure this script originally hit). The loadable .so
# is what actually matters; only queue a package when its .so is truly absent,
# using the t64 package name as the candidate.
declare -A SO_PKG=(
  [libGL.so.1]=libgl1
  [libgthread-2.0.so.0]=libglib2.0-0t64
  [libgomp.so.1]=libgomp1
)
for so in "${!SO_PKG[@]}"; do
  ldconfig -p 2>/dev/null | grep -q "$so" || MISSING+=("${SO_PKG[$so]}")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "  Installing via apt: ${MISSING[*]}"
    sudo apt update -qq
    sudo apt install -y "${MISSING[@]}" || {
      echo "  ! apt install failed. On a t64 system the needed shared libraries"
      echo "    are usually already present under *t64 packages — re-run; the"
      echo "    ldconfig check above skips any .so that is already loadable."
      exit 1
    }
fi
echo "  ✓ tesseract: $(command -v tesseract) ($(tesseract --version 2>&1 | head -1))"
echo "  ✓ pdftoppm:  $(command -v pdftoppm)"
echo

# ---------------------------------------------------------------------------
# Create the project-local venv WITH system site packages
# ---------------------------------------------------------------------------
echo "[2/5] Project-local venv at $VENV_DIR (--system-site-packages)..."
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "  Creating venv with: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
    "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
fi
echo "  ✓ venv Python: $($VENV_DIR/bin/python3 --version)"
echo

# ---------------------------------------------------------------------------
# pip install inside the venv. paddlepaddle (CPU) is the heavy wheel; paddleocr
# is the OCR pipeline on top. Pinned to the CPU build — no CUDA on this box.
# ---------------------------------------------------------------------------
echo "[3/5] pip install (inside venv) — paddlepaddle CPU wheel is large, may take several minutes..."
"$VENV_DIR/bin/pip" install --upgrade pip
echo "  Installing paddlepaddle (CPU)..."
"$VENV_DIR/bin/pip" install paddlepaddle || {
  echo
  echo "  ! paddlepaddle install failed — most often there is no wheel for this"
  echo "    Python ($("$PYTHON_BIN" --version 2>&1)). Re-run against 3.11/3.12:"
  echo "      rm -rf \"$VENV_DIR\""
  echo "      PYTHON_BIN=\"\$HOME/.pyenv/versions/3.11.9/bin/python\" scripts/tools/setup-ocr-consensus.sh"
  exit 1
}
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
echo "See the /prepare-ocr-sibling skill for the full produce → confirm flow."
