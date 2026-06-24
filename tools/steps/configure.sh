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

# Derive the correct env name from USER_ENV_MAP in utils.py
TOOL=$(id -un | sed 's/^tools\.//')
TOOL_FULL="tools.$TOOL"
ENV_NAME=$(python3 -c "
import sys, re
sys.path.insert(0, '$SRC')
try:
    from montage.utils import USER_ENV_MAP
    print(USER_ENV_MAP.get('$TOOL_FULL', 'dev'))
except Exception:
    content = open('$SRC/montage/utils.py').read()
    m = re.search(r\"'$TOOL_FULL'\\\\s*:\\\\s*'([^']+)'\", content)
    print(m.group(1) if m else 'dev')
" 2>/dev/null)

# Safety guard: config.default.yaml is the committed template and must never
# be used as a real config (it would get overwritten with credentials).
if [ "$ENV_NAME" = "default" ] || [ -z "$ENV_NAME" ]; then
    echo "WARNING: could not determine env name for $TOOL_FULL — defaulting to 'dev'"
    ENV_NAME="dev"
fi

# Use the provided path, or find the config automatically
if [ -n "$1" ]; then
    CONFIG="$1"
else
    CONFIG="$SRC/config.${ENV_NAME}.yaml"
    if [ ! -f "$CONFIG" ]; then
        echo "Config not found: $CONFIG"
        echo "Creating from default template..."
        cp "$SRC/config.default.yaml" "$CONFIG"
        chmod 600 "$CONFIG"
        echo "Created $CONFIG"
    fi
fi

echo "Checking $CONFIG..."
echo ""
python3 "$SRC/tools/steps/configure.py" "$CONFIG"
