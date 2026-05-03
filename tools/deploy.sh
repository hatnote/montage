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

SRC="$HOME/www/python/src"
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

# ── 4. restart ────────────────────────────────────────────────────────────────

echo ""
echo "── Restarting service..."
bash "$SRC/tools/steps/restart_service.sh"

echo ""
echo "── Done. Visit /meta to confirm restart time is recent."
echo ""
