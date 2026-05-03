#!/bin/bash
# tools/steps/pip_install.sh — Install Python dependencies into the venv.
#
# Run INSIDE the webservice shell pod (not from the bastion):
#   toolforge webservice python3.13 shell
#   bash ~/www/python/src/tools/steps/pip_install.sh
#   exit

set -e

VENV="$HOME/www/python/venv"
SRC="$HOME/www/python/src"

echo "Installing Python packages..."
"$VENV/bin/pip" install -r "$SRC/requirements.txt"
echo "Done."
