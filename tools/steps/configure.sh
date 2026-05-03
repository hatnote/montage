#!/bin/bash
# tools/steps/configure.sh — Validate and interactively fix the Montage config YAML.
#
# Run from the bastion as the tool account:
#   bash ~/www/python/src/tools/steps/configure.sh
#
# Or pass a specific config file:
#   bash ~/www/python/src/tools/steps/configure.sh ~/www/python/src/config.dev.yaml

set -e

if ! command -v toolforge >/dev/null 2>&1; then
    echo "ERROR: This script must run on Toolforge, not locally." >&2
    exit 1
fi

SRC="$HOME/www/python/src"

# Use the provided path, or find the config automatically
if [ -n "$1" ]; then
    CONFIG="$1"
else
    CONFIG=$(ls "$SRC"/config.*.yaml 2>/dev/null | grep -v 'config.default.yaml' | head -1)
    if [ -z "$CONFIG" ]; then
        echo "No config.*.yaml found in $SRC (excluding default)."
        echo "Copy config.default.yaml first:"
        echo "  cp $SRC/config.default.yaml $SRC/config.dev.yaml"
        echo "  chmod 600 $SRC/config.dev.yaml"
        exit 1
    fi
fi

echo "Checking $CONFIG..."
echo ""
python3 "$SRC/tools/steps/configure.py" "$CONFIG"
