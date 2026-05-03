#!/bin/bash
# tools/steps/restart_service.sh — Restart the Toolforge webservice.
#
# Run from the bastion as the tool account:
#   bash ~/www/python/src/tools/steps/restart_service.sh

set -e

cd ~
toolforge webservice python3.13 restart
