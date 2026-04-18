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
try:
    col_exists = 'file_id' in [row[1] for row in c.execute("PRAGMA table_info(entries)")]
    idx_exists = 'ix_entry_file_id' in [row[1] for row in c.execute("PRAGMA index_list(entries)")]

    if col_exists and idx_exists:
        print('Already migrated — file_id column and index exist. Nothing to do.')
        sys.exit(0)

    print(f'Migrating {DB_PATH} ...')
    # Both DDL steps inside one transaction — atomic, rollback on failure.
    # SQLite DDL is transactional; both steps succeed or neither does.
    with c:
        if not col_exists:
            c.execute("ALTER TABLE entries ADD COLUMN file_id INTEGER DEFAULT NULL")
        if not idx_exists:
            c.execute("CREATE INDEX ix_entry_file_id ON entries (file_id)")
    print('Done. file_id column and index created.')
finally:
    c.close()
