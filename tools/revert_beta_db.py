"""
Revert migration for PR #505: remove file_id column from entries table.
SQLite does not support DROP COLUMN before version 3.35.0, so this
recreates the table without file_id.

Run on montage-beta to roll back the migration.

Usage:
    python3 tools/revert_beta_db.py
"""

import sqlite3
import os
import sys

DB_PATH = os.path.expanduser('/data/project/montage-beta/www/python/src/tmp_montage.db')

if not os.path.exists(DB_PATH):
    print(f'ERROR: DB not found at {DB_PATH}')
    sys.exit(1)

c = sqlite3.connect(DB_PATH)

# Check if file_id exists
cols = [row[1] for row in c.execute("PRAGMA table_info(entries)")]
if 'file_id' not in cols:
    print('file_id column does not exist. Nothing to revert.')
    sys.exit(0)

sqlite_version = tuple(int(x) for x in sqlite3.sqlite_version.split('.'))
if sqlite_version >= (3, 35, 0):
    print(f'SQLite {sqlite3.sqlite_version} supports DROP COLUMN.')
    c.execute("DROP INDEX IF EXISTS ix_entry_file_id")
    c.execute("ALTER TABLE entries DROP COLUMN file_id")
    c.commit()
    print('Done. file_id column removed.')
else:
    print(f'SQLite {sqlite3.sqlite_version} does not support DROP COLUMN (requires 3.35+).')
    print('Reverting via table rebuild...')
    keep_cols = [col for col in cols if col != 'file_id']
    cols_sql = ', '.join(keep_cols)
    c.execute("BEGIN")
    c.execute(f"CREATE TABLE entries_backup AS SELECT {cols_sql} FROM entries")
    c.execute("DROP TABLE entries")
    c.execute(f"ALTER TABLE entries_backup RENAME TO entries")
    c.execute("DROP INDEX IF EXISTS ix_entry_file_id")
    c.execute("COMMIT")
    print('Done. file_id column removed via table rebuild.')
