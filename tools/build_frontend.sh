#!/bin/bash
set -e

FRONTEND="$HOME/www/python/src/frontend"
TOOL=$(id -un | sed 's/^tools\.//')
OUTLOG="/data/project/$TOOL/npm-build.out"
ERRLOG="/data/project/$TOOL/npm-build.err"

# Get the esbuild JS version from the lock file so we install a matching binary.
# Workaround: the Toolforge node20 image ships npm 9.2.0, which does not install
# the correct platform-specific optional binary when the lock file was generated
# on macOS with npm 10+. We skip post-install scripts (--ignore-scripts) to
# prevent esbuild's install.js from failing on the wrong binary, then install
# the correct linux-x64 binary explicitly. Remove once node20 ships npm 10+.
ESBUILD_VERSION=$(python3 -c "
import json
d = json.load(open('$FRONTEND/package-lock.json'))
print(d['packages']['node_modules/esbuild']['version'])
")

echo "Building frontend (esbuild $ESBUILD_VERSION)..."

# Clear logs from previous runs so output only reflects this run
> "$OUTLOG"
> "$ERRLOG"

toolforge jobs delete npm-build 2>/dev/null || true
toolforge jobs run npm-build --image node20 --mem 4Gi --wait \
  --command "bash -c 'cd $FRONTEND && npm install --ignore-scripts && npm install \"@esbuild/linux-x64@$ESBUILD_VERSION\" --no-save && npm run toolforge:build'"

echo ""
cat "$OUTLOG"

# Show stderr only if there are real errors (ignore EBADENGINE npm engine warnings)
ERRORS=$(grep -v "EBADENGINE\|WARN\|^$\|npm fund\|npm audit\|vulnerabilities\|packages are looking" "$ERRLOG" || true)
if [ -n "$ERRORS" ]; then
  echo ""
  echo "--- errors ---"
  echo "$ERRORS"
fi
