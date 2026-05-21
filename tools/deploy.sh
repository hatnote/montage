#!/usr/bin/env bash
# Deploy Montage on Toolforge using the buildservice.
# Run on the Toolforge bastion after `become <toolname>`.
#
# One-time setup (first deploy only):
#   git clone https://github.com/hatnote/montage.git ~/montage
#
# Usage:
#   bash ~/montage/tools/deploy.sh [--ref <branch-or-sha>]
#
# Defaults to the master branch. Pass --ref to override.

set -euo pipefail

REPO="https://github.com/hatnote/montage.git"
REF="master"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLL_INTERVAL=20   # seconds between build log checks
MAX_WAIT=600       # timeout in seconds (10 min)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ref) REF="$2"; shift 2 ;;
        *) echo "!! Unknown argument: $1"; exit 1 ;;
    esac
done

# ── 0. Self-update ───────────────────────────────────────────────────────────

echo "==> Updating local repo ..."
git -C "$SCRIPT_DIR/.." pull --ff-only || {
    echo "!! git pull failed — continuing with local version."
}

# Derive tool name and URL from the current account
TOOL_NAME=$(id -un | sed 's/^tools\.//')
TOOL_URL="https://${TOOL_NAME}.toolforge.org"

echo "==> Deploying Montage"
echo "    Tool:   $TOOL_NAME"
echo "    Ref:    $REF"
echo "    URL:    $TOOL_URL"
echo ""

# ── 1. Get expected SHA from GitHub ──────────────────────────────────────────

echo "==> Resolving ref $REF ..."
EXPECTED_SHA=$(git ls-remote "$REPO" "$REF" 2>/dev/null | awk '{print $1}' | cut -c1-7)
if [[ -z "$EXPECTED_SHA" ]]; then
    EXPECTED_SHA=$(echo "$REF" | cut -c1-7)
fi
echo "    Expected SHA: $EXPECTED_SHA"

# Check what's currently running
CURRENT_SHA=$(toolforge build logs 2>/dev/null | grep 'RESULT_SHA=' | grep -oE 'RESULT_SHA=[a-f0-9]+' | cut -d= -f2 | cut -c1-7 || true)
if [[ -n "$CURRENT_SHA" ]]; then
    echo "    Running SHA:  $CURRENT_SHA"
    if [[ "$CURRENT_SHA" == "$EXPECTED_SHA" ]]; then
        echo ""
        echo "!! WARNING: the running image already matches the expected SHA ($EXPECTED_SHA)."
        echo "   A rebuild will produce the same image. Continuing anyway ..."
        echo ""
    fi
fi

# ── 2. Start build ───────────────────────────────────────────────────────────

echo ""
echo "==> Starting build ..."
toolforge build start "$REPO" --ref "$REF"

# ── 3. Poll for completion ───────────────────────────────────────────────────

echo ""
echo "==> Waiting for build (timeout: ${MAX_WAIT}s, checking every ${POLL_INTERVAL}s) ..."
ELAPSED=0
BUILD_OK=false

while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    sleep "$POLL_INTERVAL"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))

    LOGS=$(toolforge build logs 2>&1)

    if echo "$LOGS" | grep -q '\[step-results\].*Built image'; then
        BUILD_OK=true
        break
    fi

    # Detect obvious failures
    if echo "$LOGS" | grep -qE '\[step-(build|clone)\].*[Ee]rror|build.*failed|exit code [^0]'; then
        echo ""
        echo "!! Build appears to have failed. Last 20 log lines:"
        echo "$LOGS" | tail -20
        exit 1
    fi

    printf "    Still building ... (%ds elapsed)\n" "$ELAPSED"
done

if [[ "$BUILD_OK" != true ]]; then
    echo "!! Build did not complete within ${MAX_WAIT}s. Check logs:"
    echo "   toolforge build logs | tail -30"
    exit 1
fi

echo "    Build completed."

# ── 4. Verify SHA and port ───────────────────────────────────────────────────

echo ""
echo "==> Verifying build ..."
LOGS=$(toolforge build logs 2>&1)

RESULT_SHA=$(echo "$LOGS" | grep 'RESULT_SHA=' | grep -oE 'RESULT_SHA=[a-f0-9]+' | cut -d= -f2 | cut -c1-7)
GUNICORN_LINE=$(echo "$LOGS" | grep 'gunicorn.*--bind' | tail -1)

if [[ -z "$RESULT_SHA" ]]; then
    echo "!! Could not find RESULT_SHA in build logs."
    exit 1
fi

echo "    Built SHA:    $RESULT_SHA"
echo "    Expected SHA: $EXPECTED_SHA"

if [[ "$RESULT_SHA" != "$EXPECTED_SHA" ]]; then
    echo "!! SHA mismatch — the build may have used a different commit."
    echo "   Built:    $RESULT_SHA"
    echo "   Expected: $EXPECTED_SHA"
    echo "   Aborting restart. Trigger a new build or check the ref."
    exit 1
fi

if ! echo "$GUNICORN_LINE" | grep -q '0\.0\.0\.0:8000'; then
    echo "!! gunicorn is not binding to port 8000:"
    echo "   $GUNICORN_LINE"
    echo "   Check the Procfile and rebuild."
    exit 1
fi

echo "    SHA match:    OK"
echo "    Port check:   OK (8000)"

# ── 5. Restart service ───────────────────────────────────────────────────────

echo ""
echo "==> Restarting service ..."
toolforge webservice buildservice restart --mount all

# ── 6. Smoke test ────────────────────────────────────────────────────────────

echo ""
echo "==> Waiting 15s for pod to start ..."
sleep 15

echo "==> Checking /meta/ ..."
META_RESPONSE=$(curl -sf "${TOOL_URL}/meta/" 2>&1 || true)

if echo "$META_RESPONSE" | grep -q 'Start time'; then
    START_TIME=$(echo "$META_RESPONSE" | grep -oE 'Start time.*?</td>' | sed 's/<[^>]*>//g' | head -1)
    echo "    Service is up. $START_TIME"
else
    echo "!! /meta/ did not return expected content. Response:"
    echo "$META_RESPONSE" | head -5
    echo "   The pod may still be starting — check again in a minute."
    exit 1
fi

echo ""
echo "==> Deploy complete: $TOOL_URL"
