#!/bin/bash
# Run test_beta_mariadb.py against the ToolsDB MariaDB instance.
# Reads credentials from ~/replica.my.cnf — no passwords in this file.
# Script: ~/www/python/src/tools/test_beta_mariadb.py
# Issue:  hatnote/montage#514
set -e
source ~/www/python/venv/bin/activate
DB_USER=$(awk -F'[= ]+' '/^user/{print $2}' ~/replica.my.cnf | head -1)
DB_PASS=$(awk -F'[= ]+' '/^password/{print $2}' ~/replica.my.cnf | head -1)
DB_URL="mysql+pymysql://$DB_USER:$DB_PASS@tools.db.svc.wikimedia.cloud/${DB_USER}__montage_beta?charset=utf8mb4"
CAT="Images_from_Wiki_Loves_Monuments_2015_in_France"
python3 ~/www/python/src/tools/test_beta_mariadb.py --db_url "$DB_URL" --category "$CAT"
