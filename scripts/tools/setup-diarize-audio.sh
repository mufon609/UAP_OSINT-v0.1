#!/bin/bash
# scripts/tools/setup-diarize-audio.sh
#
# One-time setup for scripts/tools/diarize-audio.py — speaker diarization
# wrapping pyannote.audio. Companion to setup-photo-identity.sh; covers
# only the audio-side dependencies (pyannote + torch + HF auth).
#
# Three things have to be in place:
#   1. pyannote.audio + torch installed (pip)
#   2. User conditions accepted on Hugging Face for the two gated models
#      backing speaker-diarization-3.1 (manual step — opens a browser)
#   3. HF_TOKEN set in the shell env so diarize-audio.py can authenticate
#
# Steps 2 and 3 require user action — this script reports what's needed
# and verifies state, but doesn't try to drive a browser or write to ~/.bashrc.

set -e

echo "============================================================"
echo " Speaker-diarization dependency setup"
echo "============================================================"
echo

# ---------------------------------------------------------------------------
# pip install pyannote.audio (pulls torch + torchaudio + dependencies)
# ---------------------------------------------------------------------------
echo "[1/4] pip install pyannote.audio..."
if ! command -v pip >/dev/null 2>&1 && ! command -v pip3 >/dev/null 2>&1; then
    echo "  ✗ pip / pip3 not found. Install python3-pip first."
    exit 1
fi
PIP=$(command -v pip3 || command -v pip)
"$PIP" install --user --upgrade pyannote.audio
echo

# ---------------------------------------------------------------------------
# Python module verification
# ---------------------------------------------------------------------------
echo "[2/4] Python module verification:"
python3 -c "import pyannote.audio; print(f'  pyannote.audio {pyannote.audio.__version__} OK')"
python3 -c "import torch; print(f'  torch {torch.__version__} OK (cuda available: {torch.cuda.is_available()})')"
python3 -c "import torchaudio; print(f'  torchaudio {torchaudio.__version__} OK')"
echo

# ---------------------------------------------------------------------------
# Hugging Face model gating — manual step reminder
# ---------------------------------------------------------------------------
echo "[3/4] Hugging Face user conditions (MANUAL one-time step):"
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
echo "  (no other repo scope needed beyond 'Read access to contents of public/gated repos')"
echo

# ---------------------------------------------------------------------------
# HF_TOKEN env-var check
# ---------------------------------------------------------------------------
echo "[4/4] HF_TOKEN env-var check:"
if [ -n "$HF_TOKEN" ]; then
    echo "  ✓ HF_TOKEN is set (\${HF_TOKEN:0:6}...)"
else
    echo "  ✗ HF_TOKEN not set in current shell."
    echo
    echo "  Set it for this session:"
    echo "    export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx"
    echo
    echo "  Or persist in ~/.bashrc / ~/.zshrc (don't commit token-bearing"
    echo "  shell files to a repo)."
fi

echo
echo "============================================================"
echo " Setup complete (if all four checks passed)."
echo "============================================================"
echo
echo "Next: see scripts/tools/VIDEO-PIPELINE.md, step 2.5."
echo
echo "Quick reference:"
echo "  diarize-audio.py sources/video/NAME.mp4                 # full video"
echo "  diarize-audio.py sources/video/NAME.mp4 --start 19:00 --end 22:00"
