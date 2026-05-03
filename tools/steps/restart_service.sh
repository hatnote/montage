#!/bin/bash
# tools/steps/restart_service.sh — Restart the Toolforge webservice.
#
# Run from the bastion as the tool account:
#   bash ~/www/python/src/tools/steps/restart_service.sh

set -e

if ! command -v toolforge >/dev/null 2>&1; then
    echo "ERROR: This script must run on Toolforge, not locally." >&2
    exit 1
fi

cd ~
toolforge webservice python3.13 restart
