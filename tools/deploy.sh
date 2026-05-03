#!/bin/bash
# tools/deploy.sh — Routine update: pull latest code and restart the service.
#
# Run from the bastion as the tool account:
#   become montage-beta   (or montage-dev)
#   bash ~/www/python/src/tools/deploy.sh
#
# Options:
#   --no-frontend   Skip the frontend build (saves ~2 min; safe if no frontend changes)
#   --pip           Pause after pulling and prompt to run pip install in the webservice shell

set -e

if ! command -v toolforge >/dev/null 2>&1; then
    echo ""
    echo "################################################################"
    echo "#   ERROR: This script must run on Toolforge, not locally.    #"
    echo "#   SSH to the bastion first:                                 #"
    echo "#     ssh <user>@login.toolforge.org && become montage-dev    #"
    echo "################################################################"
    echo ""
    exit 1
fi

SRC="$HOME/www/python/src"

# Verify config file exists for this tool account
TOOL=$(id -un | sed 's/^tools\.//')
TOOL_FULL="tools.$TOOL"
ENV_NAME=$(python3 -c "
import re
content = open('$SRC/montage/utils.py').read()
m = re.search(r\"'$TOOL_FULL'\\\\s*:\\\\s*'([^']+)'\", content)
print(m.group(1) if m else 'default')
" 2>/dev/null)
CONFIG="$SRC/config.${ENV_NAME}.yaml"
if [ ! -f "$CONFIG" ]; then
    echo ""
    echo "   ERROR: config file not found: $CONFIG"
    echo "   Run: bash $SRC/tools/steps/configure.sh"
    exit 1
fi

FRONTEND=1
PIP_PROMPT=0

for arg in "$@"; do
    case "$arg" in
        --no-frontend) FRONTEND=0 ;;
        --pip) PIP_PROMPT=1 ;;
    esac
done

# ── 1. pull ───────────────────────────────────────────────────────────────────

echo ""
echo "── Pulling latest code..."
git -C "$SRC" pull
echo "   Done."

# ── 2. build frontend ─────────────────────────────────────────────────────────

if [ "$FRONTEND" -eq 1 ]; then
    echo ""
    echo "── Building frontend..."
    bash "$SRC/tools/build_frontend.sh"
fi

# ── 3. pip install (if requested) ─────────────────────────────────────────────

if [ "$PIP_PROMPT" -eq 1 ]; then
    echo ""
    echo "── Python packages need updating."
    echo "   Open a new terminal and run:"
    echo ""
    echo "     toolforge webservice python3.13 shell"
    echo "     bash ~/www/python/src/tools/steps/pip_install.sh"
    echo "     exit"
    echo ""
    read -r -p "   Press Enter once pip install is done..."
fi

# ── 4. venv health check ──────────────────────────────────────────────────────

echo ""
echo "── Checking venv..."
VENV="$HOME/www/python/venv"
if [ ! -f "$VENV/bin/python3" ]; then
    echo "   ERROR: venv not found at $VENV."
    echo "   Run inside the webservice shell:"
    echo "     toolforge webservice python3.13 shell"
    echo "     bash ~/www/python/src/tools/reinstall_venv.sh"
    echo "     exit"
    exit 1
fi
if ! "$VENV/bin/python3" -c "import urllib3" 2>/dev/null; then
    echo "   ERROR: Python packages not installed (urllib3 missing)."
    echo "   Run inside the webservice shell:"
    echo "     toolforge webservice python3.13 shell"
    echo "     bash ~/www/python/src/tools/steps/pip_install.sh"
    echo "     exit"
    exit 1
fi
echo "   OK."

# ── 5. restart ────────────────────────────────────────────────────────────────

echo ""
echo "── Restarting service..."
bash "$SRC/tools/steps/restart_service.sh"

echo ""
echo "── Done. Visit /meta to confirm restart time is recent."
echo ""
