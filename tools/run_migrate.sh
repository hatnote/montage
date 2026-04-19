#!/bin/bash
# Run migrate_prod_db.sql against the ToolsDB MariaDB instance.
# Reads credentials from ~/replica.my.cnf — no passwords in this file.
# Issue: hatnote/montage#514
set -e
SQL="$HOME/www/python/src/tools/migrate_prod_db.sql"
DB_USER=$(awk -F'[= ]+' '/^user/{print $2}' ~/replica.my.cnf | head -1)
DB="${DB_USER}__montage_beta"
echo "Running: $SQL"
echo "Database: $DB"
mysql --defaults-file=~/replica.my.cnf \
    -h tools.db.svc.wikimedia.cloud "$DB" < "$SQL"
echo "Done."
