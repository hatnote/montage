"""
Revert migration for PR #505: remove file_id column from entries table.

SQLite < 3.35 does not support DROP COLUMN, so the slow path uses the
SQLite-recommended 12-step procedure (https://www.sqlite.org/lang_altertable.html):
  1. Disable foreign keys
  2. Begin transaction
  3. Read original schema from sqlite_master
  4. Create new table with correct schema (file_id removed)
  5. Copy data
  6. Drop old table (cascades to its indexes and triggers)
  7. Rename new table
  8. Recreate all indexes and triggers from sqlite_master
  9. Foreign key check
  10. Commit
  11. Re-enable foreign keys

Run on montage-beta to roll back the PR #505 migration.

Usage:
    python3 tools/revert_beta_db.py
"""

import sqlite3
import os
import re
import sys

DB_PATH = os.path.expanduser('/data/project/montage-beta/www/python/src/tmp_montage.db')

if not os.path.exists(DB_PATH):
    print(f'ERROR: DB not found at {DB_PATH}')
    sys.exit(1)

c = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit — we manage transactions manually
try:
    col_exists = 'file_id' in [row[1] for row in c.execute("PRAGMA table_info(entries)")]
    if not col_exists:
        print('file_id column does not exist. Nothing to revert.')
        sys.exit(0)

    sqlite_version = tuple(int(x) for x in sqlite3.sqlite_version.split('.'))

    if sqlite_version >= (3, 35, 0):
        # Fast path: DROP COLUMN supported natively
        print(f'SQLite {sqlite3.sqlite_version}: using DROP COLUMN.')
        c.execute("BEGIN")
        try:
            c.execute("DROP INDEX IF EXISTS ix_entry_file_id")
            c.execute("ALTER TABLE entries DROP COLUMN file_id")
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
        print('Done. file_id column removed.')

    else:
        # Slow path: 12-step SQLite schema-alteration procedure
        print(f'SQLite {sqlite3.sqlite_version}: using table-rebuild procedure.')

        # Step 1: get original CREATE TABLE SQL
        orig_sql = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='entries'"
        ).fetchone()[0]

        # Step 2: build new CREATE TABLE SQL with file_id removed.
        # file_id was added as a plain "file_id INTEGER DEFAULT NULL" with no
        # nested parens, so a simple comma-split is safe here.
        inner = re.search(r'\((.+)\)\s*$', orig_sql, re.DOTALL).group(1)
        definitions = [d.strip() for d in inner.split(',')]
        new_defs = [d for d in definitions if not re.match(r'file_id\b', d, re.IGNORECASE)]
        if len(new_defs) == len(definitions):
            print('ERROR: could not locate file_id in CREATE TABLE SQL — aborting.')
            sys.exit(1)
        new_create_sql = f"CREATE TABLE entries_new ({', '.join(new_defs)})"

        # Step 3: collect all indexes and triggers to recreate (excluding file_id index)
        objects_to_recreate = [
            row[0] for row in c.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE tbl_name='entries' AND type IN ('index','trigger') "
                "AND name != 'ix_entry_file_id' AND sql IS NOT NULL"
            )
        ]

        keep_cols = ', '.join([row[1] for row in c.execute("PRAGMA table_info(entries)")
                               if row[1] != 'file_id'])

        # Step 4: execute rebuild inside one transaction
        c.execute("PRAGMA foreign_keys = OFF")
        c.execute("BEGIN")
        try:
            c.execute(new_create_sql)
            c.execute(f"INSERT INTO entries_new SELECT {keep_cols} FROM entries")
            c.execute("DROP TABLE entries")
            c.execute("ALTER TABLE entries_new RENAME TO entries")
            for sql in objects_to_recreate:
                c.execute(sql)
            errors = c.execute("PRAGMA foreign_key_check").fetchall()
            if errors:
                raise RuntimeError(f'Foreign key check failed: {errors}')
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
        finally:
            c.execute("PRAGMA foreign_keys = ON")
        print('Done. file_id column removed via table rebuild.')

finally:
    c.close()
