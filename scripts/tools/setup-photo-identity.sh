#!/bin/bash
# scripts/tools/setup-photo-identity.sh
#
# One-time install of system dependencies for scripts/tools/detect-faces.py
# (the speaker-identity face-detection / baseline-tracking tool).
#
# Two apt packages on Debian / Ubuntu / Kali:
#   - python3-opencv  : the Python cv2 module
#   - opencv-data     : the Haar cascade XML files cv2 reads at runtime
#
# Debian's python3-opencv package omits cv2.data so the cascades live at
# /usr/share/opencv4/haarcascades/ rather than a path cv2 reports itself.
# detect-faces.py knows the Debian path; if cv2.data exists at runtime it
# uses that path first.
#
# Requires sudo for the apt invocations.

set -e

echo "Installing python3-opencv + opencv-data via apt..."
sudo apt update
sudo apt install -y python3-opencv opencv-data

echo
echo "Verifying install..."
python3 -c "import cv2; print(f'  opencv {cv2.__version__} OK')"
python3 -c "from PIL import Image; print(f'  Pillow OK')"

CASCADE=/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml
if [ -f "$CASCADE" ]; then
    echo "  Haar cascade found at $CASCADE"
else
    echo "  WARNING: Haar cascade not at expected Debian path:"
    echo "    $CASCADE"
    echo "  detect-faces.py will probe other standard locations at runtime."
fi

echo
echo "Setup complete. detect-faces.py --help for usage."
