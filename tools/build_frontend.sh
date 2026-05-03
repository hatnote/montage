#!/bin/bash
set -e
#
# Build the Montage frontend and copy assets to montage/static/.
#
# KNOWN WORKAROUNDS
# -----------------
# 1. --ignore-scripts + explicit @esbuild/linux-x64 install [TEMPORARY]
#    Root cause: package-lock.json is generated on macOS with npm 10+, but the
#    Toolforge node20 image ships npm 9.2.0. npm 9 does not correctly install
#    platform-specific optional binaries from a cross-platform lock file, so
#    @esbuild/linux-x64 ends up at the wrong version. esbuild's post-install
#    script (install.js) then catches the mismatch and aborts.
#    Workaround: skip all post-install scripts (--ignore-scripts), then install
#    the correct linux-x64 binary explicitly at the version from the lock file.
#    Long-term fix: switch to --image node22, which ships npm 10+, OR regenerate
#    package-lock.json on Linux and commit it. See: T393437.
#
# 2. VITE_API_ENDPOINT='' in frontend/.env.production [PERMANENT]
#    Required so production builds use a relative base URL (/v1/) instead of
#    the localhost URL from .env.default. This file must stay in the repo.

FRONTEND="$HOME/www/python/src/frontend"
PROJECT="$HOME/www/python/src"
TOOL=$(id -un | sed 's/^tools\.//')
OUTLOG="/data/project/$TOOL/npm-build.out"
ERRLOG="/data/project/$TOOL/npm-build.err"

# Restore package-lock.json to the repo version so npm install runs cleanly
# regardless of local modifications left by previous npm runs in the container.
git -C "$PROJECT" checkout -- frontend/package-lock.json

# Derive esbuild version dynamically so the explicit binary install stays in
# sync whenever esbuild is upgraded in package-lock.json.
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
