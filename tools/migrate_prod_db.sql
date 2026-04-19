-- Production migration: add file_id column to entry table.
-- Companion to revert_prod_db.sql (exact reverse).
-- Idempotent: safe to run more than once.
--
-- Run from Toolforge as the tool account, e.g.:
--   mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db> < tools/migrate_prod_db.sql
--
-- Part of hatnote/montage#505 (image/oldimage → file/filerevision migration).

ALTER TABLE entry ADD COLUMN IF NOT EXISTS file_id BIGINT NULL;
CREATE INDEX IF NOT EXISTS ix_entry_file_id ON entry (file_id);
