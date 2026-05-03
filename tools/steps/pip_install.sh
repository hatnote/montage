#!/bin/bash
# tools/steps/pip_install.sh — Install Python dependencies into the venv.
#
# Run INSIDE the webservice shell pod (not from the bastion):
#   toolforge webservice python3.13 shell
#   bash ~/www/python/src/tools/steps/pip_install.sh
#   exit

set -e

if ! command -v toolforge >/dev/null 2>&1; then
    echo "ERROR: This script must run inside the Toolforge webservice shell, not locally." >&2
    exit 1
fi

VENV="$HOME/www/python/venv"
SRC="$HOME/www/python/src"

echo "Installing Python packages..."
"$VENV/bin/pip" install -r "$SRC/requirements.txt"
echo "Done."
