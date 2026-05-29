#!/bin/bash
# scripts/tools/setup-face-embeddings.sh
#
# One-time setup for the dlib face-embedding matcher backing
# scripts/tools/detect-faces.py and scripts/tools/spot-check-attribution.py.
# Companion to setup-photo-identity.sh (which covers ffmpeg / yt-dlp / the
# frame-extraction side); this script covers only the face-matching engine.
#
# What it puts in place:
#   1. cmake + build-essential (apt) — dlib is C++ and compiles from source
#      on Python versions without a prebuilt wheel (e.g. 3.13). gcc/g++ and
#      python3-dev are assumed present (Kali ships them); cmake is the piece
#      typically missing.
#   2. python3-venv (apt) — required to create the project-local venv.
#   3. A project-local venv at .venv-face/ created WITH --system-site-packages
#      (PEP 668 blocks system-wide pip on Debian/Kali). --system-site-packages
#      is load-bearing: detect-faces.py uses cv2 + PIL for cropping and
#      spot-check-attribution.py uses PyYAML, all of which live in the system
#      site. The venv only adds dlib / face_recognition / numpy on top, so the
#      existing tools keep working after they auto-relaunch under venv Python.
#   4. dlib (source build) + face_recognition + numpy installed in the venv.
#      First face_recognition import warms/downloads dlib's ResNet model.
#
# detect-faces.py and spot-check-attribution.py auto-detect .venv-face/ and
# re-exec under its Python, so contributors never source an activate script.
# When .venv-face/ is absent, both tools still print --help cleanly (the
# heavy import is deferred) but will error at runtime asking you to run this.

set -e

# Resolve repo root (this script lives at REPO_ROOT/scripts/tools/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-face"

echo "============================================================"
echo " dlib face-embedding matcher dependency setup"
echo "============================================================"
echo "Repo root: $REPO_ROOT"
echo "Venv path: $VENV_DIR"
echo

# ---------------------------------------------------------------------------
# Build toolchain for the dlib source compile
# ---------------------------------------------------------------------------
echo "[1/5] Verify build toolchain (cmake + build-essential)..."
MISSING=()
command -v cmake >/dev/null 2>&1 || MISSING+=(cmake)
command -v g++ >/dev/null 2>&1 || MISSING+=(build-essential)
if ! python3 -c "import venv" 2>/dev/null; then MISSING+=(python3-venv); fi
# python3-dev headers (Python.h) — needed to compile the dlib Python bindings.
PYINC="$(python3 -c 'import sysconfig; print(sysconfig.get_path("include"))')"
if [ ! -f "$PYINC/Python.h" ]; then MISSING+=("python3-dev"); fi
if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "  Installing via apt: ${MISSING[*]}"
    sudo apt update -qq
    sudo apt install -y "${MISSING[@]}"
fi
echo "  ✓ cmake:           $(command -v cmake)"
echo "  ✓ g++:             $(command -v g++)"
echo "  ✓ Python.h:        $PYINC/Python.h"
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
# Confirm the system-site bridge works (cv2/PIL/yaml visible from inside venv).
"$VENV_DIR/bin/python3" - <<'PY'
import importlib, sys
ok = True
for mod in ("cv2", "PIL", "yaml"):
    try:
        importlib.import_module(mod)
        print(f"  ✓ system-site {mod} visible inside venv")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  ✗ {mod} NOT visible inside venv: {e}")
        print("    (run setup-photo-identity.sh — these come from the system side)")
sys.exit(0 if ok else 1)
PY
echo

# ---------------------------------------------------------------------------
# pip install inside the venv. dlib compiles from source — this is the slow
# step (often several minutes on first run). face_recognition is the thin
# wrapper; numpy backs the embedding-distance math + the .npz cache.
# ---------------------------------------------------------------------------
echo "[3/5] pip install (inside venv) — dlib builds from source, may take several minutes..."
"$VENV_DIR/bin/pip" install --upgrade pip
echo "  Building dlib (C++ compile via cmake)..."
"$VENV_DIR/bin/pip" install dlib
echo "  Installing face_recognition + numpy..."
"$VENV_DIR/bin/pip" install face_recognition numpy
echo

# ---------------------------------------------------------------------------
# Module verification + model warm-up
# ---------------------------------------------------------------------------
echo "[4/5] Python module verification (in venv):"
"$VENV_DIR/bin/python3" -c "import dlib; print(f'  dlib {dlib.__version__} OK')"
"$VENV_DIR/bin/python3" -c "import face_recognition; print('  face_recognition OK')"
"$VENV_DIR/bin/python3" -c "import numpy; print(f'  numpy {numpy.__version__} OK')"
echo

echo "[5/5] Warm the dlib ResNet model (first encode downloads it once)..."
"$VENV_DIR/bin/python3" - <<'PY'
import face_recognition, numpy as np
# A blank image has no faces; this still forces the models to load/initialise.
img = np.zeros((128, 128, 3), dtype=np.uint8)
face_recognition.face_locations(img, model="hog")
print("  ✓ HOG detector + ResNet encoder initialised")
PY
echo

echo "============================================================"
echo " Setup complete (if all checks passed)."
echo "============================================================"
echo
echo "detect-faces.py and spot-check-attribution.py auto-detect and re-launch"
echo "under the venv Python, so run them directly without activating anything:"
echo
echo "  python3 scripts/tools/detect-faces.py detect --index /tmp/frames-NAME/index.md"
echo "  python3 scripts/tools/spot-check-attribution.py SIBLING.yaml --video sources/video/NAME.mp4"
echo
echo "See scripts/tools/VIDEO-PIPELINE.md, step 3."
