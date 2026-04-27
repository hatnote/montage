#!/bin/bash
set -e

echo "Script: $0"
echo "Frontend: $HOME/www/python/src/frontend"
echo ""

toolforge jobs delete npm-build 2>/dev/null || true

toolforge jobs run npm-build --image node20 --mem 4Gi --command "cd $HOME/www/python/src/frontend && npm install && npm run toolforge:build"

echo "Job submitted. Waiting for it to start..."
sleep 15

for i in $(seq 1 40); do
    echo "--- attempt $i / 40 ---"
    if toolforge jobs logs npm-build 2>&1; then
        break
    fi
    sleep 15
done

echo ""
echo "Done. Check above for build errors."
