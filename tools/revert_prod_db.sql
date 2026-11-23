-- Production revert: remove file_id column from entries table and drop the
-- campaign_requests table.
-- Exact reverse of migrate_prod_db.sql.
-- Idempotent: safe to run more than once.
--
-- Run from Toolforge as the tool account, e.g.:
--   mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db> < tools/revert_prod_db.sql
--
-- Part of hatnote/montage#505 (image/oldimage → file/filerevision migration)
-- and hatnote/montage#582 (campaign creation requests).

DROP TABLE IF EXISTS campaign_requests;

DROP INDEX IF EXISTS ix_entries_file_id ON entries;
ALTER TABLE entries DROP COLUMN IF EXISTS file_id;
