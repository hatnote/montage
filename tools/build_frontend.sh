#!/bin/bash
set -e

FRONTEND="$HOME/www/python/src/frontend"
PROJECT=$(git rev-parse --show-toplevel)
TOOL=$(id -un | sed 's/^tools\.//')
OUTLOG="/data/project/$TOOL/npm-build.out"
ERRLOG="/data/project/$TOOL/npm-build.err"

# Get the esbuild JS version from the lock file so we install a matching binary
ESBUILD_VERSION=$(python3 -c "
import json, sys
d = json.load(open('$FRONTEND/package-lock.json'))
print(d['packages']['node_modules/esbuild']['version'])
")
echo "esbuild version: $ESBUILD_VERSION"
echo "Frontend: $FRONTEND"
echo ""

toolforge jobs delete npm-build 2>/dev/null || true
# The explicit @esbuild/linux-x64 install works around a version mismatch caused by
# the Toolforge node20 image shipping npm 9.2.0, while package-lock.json is generated
# on macOS with npm 10+. npm 9 does not install the correct platform binary for
# optional deps. Remove this step once the node20 image ships npm 10+.
toolforge jobs run npm-build --image node20 --mem 4Gi --wait \
  --command "bash -c 'cd $FRONTEND && npm install && npm install \"@esbuild/linux-x64@$ESBUILD_VERSION\" --no-save && npm run toolforge:build'"

echo ""
echo "--- stdout ---"
cat "$OUTLOG"
echo ""
echo "--- stderr ---"
cat "$ERRLOG"
