#!/bin/bash
# scripts/tools/setup-diarize-audio.sh
#
# One-time setup for scripts/tools/diarize-audio.py — speaker diarization
# wrapping pyannote.audio. Companion to setup-photo-identity.sh; covers
# only the audio-side dependencies (pyannote + torch + HF auth).
#
# Four things have to be in place:
#   1. python3-venv (apt) — required to create the project-local venv
#   2. pyannote.audio + torch + torchaudio installed inside .venv-diarize/
#      (a project-local virtual environment at the repo root; required
#      because PEP 668 blocks system-wide pip installs on Debian/Kali,
#      and the dependency footprint is too large to want system-wide
#      anyway). diarize-audio.py auto-relaunches under this venv's Python
#      so contributors don't have to source the activate script.
#   3. User conditions accepted on Hugging Face for the two gated models
#      backing speaker-diarization-3.1 (manual step — opens a browser)
#   4. HF_TOKEN set in the shell env so diarize-audio.py can authenticate
#
# Steps 3 and 4 require user action — this script reports what's needed
# and verifies state, but doesn't try to drive a browser or write to ~/.bashrc.

set -e

# Resolve repo root (this script lives at REPO_ROOT/scripts/tools/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-diarize"

echo "============================================================"
echo " Speaker-diarization dependency setup"
echo "============================================================"
echo "Repo root: $REPO_ROOT"
echo "Venv path: $VENV_DIR"
echo

# ---------------------------------------------------------------------------
# Ensure python3-venv is installed (apt-managed)
# ---------------------------------------------------------------------------
echo "[1/5] Verify python3-venv is available..."
if ! python3 -c "import venv" 2>/dev/null; then
    echo "  python3 venv module not available — installing python3-venv via apt..."
    sudo apt update -qq
    sudo apt install -y python3-venv
fi
python3 -c "import venv; print('  ✓ python3 venv module OK')"
echo

# ---------------------------------------------------------------------------
# Create the project-local venv if not already present
# ---------------------------------------------------------------------------
echo "[2/5] Project-local venv at $VENV_DIR..."
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "  Creating venv..."
    python3 -m venv "$VENV_DIR"
fi
echo "  ✓ venv Python: $($VENV_DIR/bin/python3 --version)"
echo

# ---------------------------------------------------------------------------
# pip install pyannote.audio inside the venv (pulls torch + torchaudio + deps)
# ---------------------------------------------------------------------------
echo "[3/5] pip install pyannote.audio (inside venv)..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install --upgrade pyannote.audio
echo

# ---------------------------------------------------------------------------
# Python module verification — using the venv Python
# ---------------------------------------------------------------------------
echo "[4/5] Python module verification (in venv):"
"$VENV_DIR/bin/python3" -c "import pyannote.audio; print(f'  pyannote.audio {pyannote.audio.__version__} OK')"
"$VENV_DIR/bin/python3" -c "import torch; print(f'  torch {torch.__version__} OK (cuda available: {torch.cuda.is_available()})')"
"$VENV_DIR/bin/python3" -c "import torchaudio; print(f'  torchaudio {torchaudio.__version__} OK')"
echo

# ---------------------------------------------------------------------------
# Hugging Face model gating + HF_TOKEN — manual steps
# ---------------------------------------------------------------------------
echo "[5/5] Hugging Face user conditions + HF_TOKEN (MANUAL one-time steps):"
echo
echo "  pyannote/speaker-diarization-3.1 is gated. Visit each of these and"
echo "  click 'Agree and access repository':"
echo
echo "    https://hf.co/pyannote/speaker-diarization-3.1"
echo "    https://hf.co/pyannote/segmentation-3.0"
echo
echo "  Then create a read-token at:"
echo
echo "    https://hf.co/settings/tokens"
echo
echo "  (only need 'Read access to contents of public/gated repos' scope)"
echo
if [ -n "$HF_TOKEN" ]; then
    echo "  ✓ HF_TOKEN is set in this shell (${HF_TOKEN:0:6}...)"
else
    echo "  ✗ HF_TOKEN not set in current shell."
    echo
    echo "  Set it for this session:"
    echo "    export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx"
    echo
    echo "  Or persist via your shell config (don't commit token-bearing"
    echo "  shell files to a repo)."
fi

echo
echo "============================================================"
echo " Setup complete (if all checks passed)."
echo "============================================================"
echo
echo "diarize-audio.py auto-detects and re-launches under the venv Python,"
echo "so you can run it directly without activating anything:"
echo
echo "  python3 scripts/tools/diarize-audio.py sources/video/NAME.mp4"
echo "  python3 scripts/tools/diarize-audio.py sources/video/NAME.mp4 --start 19:00 --end 22:00"
echo
echo "See scripts/tools/VIDEO-PIPELINE.md, step 1.5."
