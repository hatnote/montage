-- Migration: widen round_sources.params from TEXT (64 KB) to MEDIUMTEXT (16 MB).
-- Companion to revert_round_sources_params.sql.
-- Idempotent: safe to run more than once (MODIFY to the same type is a no-op).
--
-- Why: a 'selected' import stores its whole file list in round_sources.params;
-- a few thousand long file names pass 64 KB, which strict mode rejects (the
-- import then fails). The model uses LongJSONEncodedDict for this column.
-- Part of hatnote/montage#621 (background import job, Phase 2).
--
-- Order: any. The schema check (montage/check_rdb.py) does not compare column
-- types, so code with or without this change runs on either column type.
-- Run from Toolforge as the tool account, e.g.:
--   mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db> < tools/migrate_round_sources_params.sql
-- On a large round_sources table the ALTER copies the table; run it when no
-- import is running.

ALTER TABLE round_sources MODIFY params MEDIUMTEXT NULL;
