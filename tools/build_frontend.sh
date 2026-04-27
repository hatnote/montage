#!/bin/bash
set -e

echo "Script: $0"
echo "Frontend: $HOME/www/python/src/frontend"
echo ""

toolforge jobs delete npm-build 2>/dev/null || true

FRONTEND="$HOME/www/python/src/frontend"
PROJECT=$(git rev-parse --show-toplevel)
TOOL=$(id -un | sed 's/^tools\.//')

# Restore the lock file to repo state so npm ci gets the correct binary versions
git -C "$PROJECT" checkout -- frontend/package-lock.json

toolforge jobs run npm-build --image node20 --mem 4Gi --command "bash -c 'cd $FRONTEND && rm -rf node_modules && npm ci && npm run toolforge:build'"

OUTLOG="/data/project/$TOOL/npm-build.out"
ERRLOG="/data/project/$TOOL/npm-build.err"

echo "Job submitted. Waiting for it to start..."
for i in $(seq 1 30); do
    STATUS=$(toolforge jobs show npm-build 2>/dev/null | grep "Status:" | head -1)
    echo "--- $STATUS"
    if echo "$STATUS" | grep -qE "Running|Succeeded|Failed|Error"; then
        break
    fi
    sleep 5
done

echo ""
echo "--- stdout ---"
tail -f "$OUTLOG" &
TAIL_PID=$!

while toolforge jobs show npm-build 2>/dev/null | grep -q "Running"; do
    sleep 5
done
kill "$TAIL_PID" 2>/dev/null
wait "$TAIL_PID" 2>/dev/null

echo ""
echo "--- stderr ---"
cat "$ERRLOG"
echo ""
toolforge jobs show npm-build | grep "Status:"
