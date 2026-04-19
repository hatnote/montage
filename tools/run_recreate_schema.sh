#!/bin/bash
# Drop and recreate all tables in the MariaDB beta database from current models.
# Safe on beta only — no real data. Issue: hatnote/montage#514
set -e
SRC="$HOME/www/python/src"
source "$HOME/www/python/venv/bin/activate"
cd "$SRC"
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
print('Dropping all tables...')
Base.metadata.drop_all(engine)
print('Recreating all tables...')
Base.metadata.create_all(engine)
print('Done.')
EOF
