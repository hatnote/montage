-- Production revert: remove file_id column from entry table.
-- Exact reverse of migrate_prod_db.sql.
-- Idempotent: safe to run more than once.
--
-- Run from Toolforge as the tool account, e.g.:
--   mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db> < tools/revert_prod_db.sql
--
-- Part of hatnote/montage#505 (image/oldimage → file/filerevision migration).

DROP INDEX IF EXISTS ix_entry_file_id ON entry;
ALTER TABLE entry DROP COLUMN IF EXISTS file_id;
