-- Revert: round_sources.params back to TEXT. Reverse of
-- migrate_round_sources_params.sql.
--
-- CAUTION: rows whose params are longer than 65,535 bytes make this fail
-- (strict mode) or get truncated, which corrupts their JSON. Check first:
--   SELECT id, LENGTH(params) FROM round_sources WHERE LENGTH(params) > 65535;
-- Part of hatnote/montage#621 (background import job, Phase 2).

ALTER TABLE round_sources MODIFY params TEXT NULL;
