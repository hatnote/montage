#!/bin/bash
# Run test_beta_mariadb.py against the beta MariaDB instance.
# Edit DB_URL below before running. See hatnote/montage#514.
#
# Usage (from any folder on the server):
#   bash ~/www/python/src/tools/run_test.sh

set -e
source ~/www/python/venv/bin/activate

DB_URL="mysql+pymysql://USER:PASS@tools.db.svc.wikimedia.cloud/DB?charset=utf8mb4"
CATEGORY="Images_from_Wiki_Loves_Monuments_2015_in_France"
SCRIPT=~/www/python/src/tools/test_beta_mariadb.py

echo "Script : $SCRIPT"
echo "DB     : $DB_URL"
echo "Cat    : $CATEGORY"
echo ""

python3 "$SCRIPT" --db_url "$DB_URL" --category "$CATEGORY"
