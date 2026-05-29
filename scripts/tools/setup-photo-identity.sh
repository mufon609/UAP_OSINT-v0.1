#!/bin/bash
# scripts/tools/setup-photo-identity.sh
#
# One-time setup for the video pipeline + speaker-identification toolset.
# Installs and verifies the frame-handling dependencies the pipeline needs:
#
#   download-video.py    yt-dlp + ffmpeg + JS runtime (EJS challenge solver)
#   extract-frames.py    ffmpeg + ffprobe
#   detect-faces.py      Pillow (cropping) + the dlib face-embedding engine
#
# The dlib HOG detector + ResNet face-embedding matcher behind detect-faces.py
# and spot-check-attribution.py lives in a separate venv — run
# scripts/tools/setup-face-embeddings.sh for that. This script covers only the
# frame-handling side (download / extract / crop).
#
# See scripts/tools/VIDEO-PIPELINE.md for the end-to-end workflow.
#
# apt-installable pieces are installed automatically (sudo required).
# yt-dlp and JS runtimes are verified-only since they have multiple valid
# install paths (pip, apt, native installer); the script reports what's
# missing and points at install guidance.

set -e

echo "============================================================"
echo " Photo-identity + video-pipeline dependency setup"
echo "============================================================"
echo

# ---------------------------------------------------------------------------
# apt install: ffmpeg + Pillow
# ---------------------------------------------------------------------------
echo "[1/3] apt install ffmpeg + python3-pil..."
sudo apt update -qq
sudo apt install -y ffmpeg python3-pil
echo

# ---------------------------------------------------------------------------
# Python module verification
# ---------------------------------------------------------------------------
echo "[2/3] Python module verification:"
python3 -c "from PIL import Image; print('  Pillow OK')"
echo

# ---------------------------------------------------------------------------
# Verify-only: yt-dlp, ffprobe, JS runtime
# (Tools that may already be installed via pip / native installer / apt;
# script reports rather than installs.)
# ---------------------------------------------------------------------------
echo "[3/3] Video-pipeline dependency check:"

# yt-dlp
if command -v yt-dlp >/dev/null 2>&1; then
    YTDLP_VERSION=$(yt-dlp --version 2>/dev/null | head -1)
    echo "  ✓ yt-dlp ${YTDLP_VERSION}"
else
    echo "  ✗ yt-dlp NOT FOUND."
    echo "    Install via:  pip install --user yt-dlp"
    echo "    or:           sudo apt install yt-dlp"
fi

# ffprobe (ships with ffmpeg, sanity check)
if command -v ffprobe >/dev/null 2>&1; then
    echo "  ✓ ffprobe (with ffmpeg) OK"
else
    echo "  ✗ ffprobe NOT FOUND (ffmpeg apt install above should have provided it)"
fi

# JS runtime — yt-dlp's --remote-components ejs:github solver requires one
JS_FOUND=""
for runtime in deno node bun; do
    if command -v "$runtime" >/dev/null 2>&1; then
        JS_FOUND="$runtime"
        echo "  ✓ JS runtime: $runtime ($($runtime --version 2>/dev/null | head -1))"
        break
    fi
done
if [ -z "$JS_FOUND" ]; then
    echo "  ✗ No JS runtime found (need one of: deno, node, bun)."
    echo "    yt-dlp's EJS challenge solver requires a JS runtime to handle"
    echo "    YouTube's anti-bot challenges."
    echo "    Install one:"
    echo "      deno:  curl -fsSL https://deno.land/install.sh | sh"
    echo "      node:  sudo apt install nodejs"
    echo "      bun:   curl -fsSL https://bun.sh/install | bash"
fi

echo
echo "============================================================"
echo " Setup complete."
echo "============================================================"
echo
echo "IMPORTANT: detect-faces.py / spot-check-attribution.py also need the"
echo "dlib face-embedding engine. Run it once:"
echo "  bash scripts/tools/setup-face-embeddings.sh"
echo
echo "Next: see scripts/tools/VIDEO-PIPELINE.md for the four-step workflow."
echo
echo "Quick reference (each command is one line, see the doc for flags):"
echo "  download-video.py URL --slug NAME"
echo "  extract-frames.py anchor --video sources/video/NAME.mp4"
echo "  detect-faces.py detect --input /tmp/frames-NAME/anchor/"
echo "  detect-faces.py register --crop CROPS/... --identity SLUG ..."
