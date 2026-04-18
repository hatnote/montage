"""
Apply migration for PR #505: add file_id column to entries table.
Run on montage-beta BEFORE deploying the new code.

Usage:
    python3 tools/migrate_beta_db.py
"""

import sqlite3
import os
import sys

DB_PATH = os.path.expanduser('/data/project/montage-beta/www/python/src/tmp_montage.db')

if not os.path.exists(DB_PATH):
    print(f'ERROR: DB not found at {DB_PATH}')
    sys.exit(1)

c = sqlite3.connect(DB_PATH)

# Check if already migrated
cols = [row[1] for row in c.execute("PRAGMA table_info(entries)")]
if 'file_id' in cols:
    print('Already migrated — file_id column exists. Nothing to do.')
    sys.exit(0)

print(f'Migrating {DB_PATH} ...')
c.execute("ALTER TABLE entries ADD COLUMN file_id INTEGER DEFAULT NULL")
c.execute("CREATE INDEX ix_entry_file_id ON entries (file_id)")
c.commit()
print('Done. file_id column and index created.')
