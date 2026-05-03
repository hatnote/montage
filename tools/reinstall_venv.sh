#!/bin/bash
# tools/reinstall_venv.sh — Rebuild the Python venv from scratch.
#
# Must run INSIDE the webservice shell pod:
#   toolforge webservice python3.13 shell
#   bash ~/www/python/src/tools/reinstall_venv.sh
#   exit

set -e

VENV="$HOME/www/python/venv"
SRC="$HOME/www/python/src"

echo ""
echo "── Rebuilding venv at $VENV..."

# Wipe existing venv
rm -rf "$VENV"

# Create without pip — python3 -m venv with pip hangs in the webservice pod
python3 -m venv "$VENV" --without-pip
echo "   Created venv."

# Bootstrap pip via curl (avoids subprocess restriction in pod)
echo "   Bootstrapping pip..."
curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV/bin/python3"
echo "   pip installed."

# Install dependencies
echo "   Installing requirements..."
"$VENV/bin/pip" install -r "$SRC/requirements.txt"
echo "   Done."

echo ""
echo "Venv ready. You can now exit this shell and start the service:"
echo "  exit"
echo "  cd ~ && toolforge webservice python3.13 start"
echo ""
