-- Revert: drop the import_jobs table. Exact reverse of migrate_import_jobs.sql.
-- Idempotent: safe to run more than once.
--
-- Deploy code WITHOUT the ImportJob model first: the web app exits at startup
-- if a model table is missing, but runs fine with an extra table. Stop the
-- import-worker job before reverting.
--
-- Part of hatnote/montage#621 (background import job; origin #618).

DROP TABLE IF EXISTS import_jobs;
