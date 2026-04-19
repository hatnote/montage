#!/bin/bash
# Drop and recreate the MariaDB beta database from current models.
# Drops the whole database to avoid FK constraint ordering issues.
# Safe on beta only — no real data. Issue: hatnote/montage#514
set -e
SRC="$HOME/www/python/src"
source "$HOME/www/python/venv/bin/activate"
cd "$SRC"
DB_USER=$(awk -F'[= ]+' '/^user/{print $2}' ~/replica.my.cnf | head -1)
DB="${DB_USER}__montage_beta"
HOST="tools.db.svc.wikimedia.cloud"
echo "Dropping and recreating database: $DB"
mysql --defaults-file=~/replica.my.cnf -h "$HOST" \
    -e "DROP DATABASE IF EXISTS \`$DB\`; CREATE DATABASE \`$DB\` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"
echo "Creating schema from current models..."
python3 - <<'EOF'
import sys
sys.path.insert(0, '.')
from montage.utils import load_env_config
from montage.rdb import Base
from sqlalchemy import create_engine
config = load_env_config()
db_url = config['db_url']
print('Database:', db_url.split('@')[-1])
engine = create_engine(db_url)
Base.metadata.create_all(engine)
print('Done.')
EOF
