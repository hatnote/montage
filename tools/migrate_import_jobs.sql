-- Migration: add the import_jobs table (background imports).
-- Companion to revert_import_jobs.sql (exact reverse).
-- Idempotent: safe to run more than once.
--
-- Run from Toolforge as the tool account BEFORE deploying code that has the
-- ImportJob model (the web app and the import worker exit at startup if the
-- table is missing), e.g.:
--   mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db> < tools/migrate_import_jobs.sql
--
-- Part of hatnote/montage#621 (background import job; origin #618).
-- Times are DATETIME (naive UTC set by the application), not TIMESTAMP:
-- MariaDB can give the first TIMESTAMP column an implicit ON UPDATE.
-- claim_token is nullable and deliberately not UNIQUE.

CREATE TABLE IF NOT EXISTS import_jobs (
    id                    INTEGER      NOT NULL AUTO_INCREMENT,
    round_id              INTEGER      NOT NULL,
    user_id               INTEGER      NOT NULL,
    status                VARCHAR(32)  NOT NULL,
    method                VARCHAR(255) NOT NULL,
    params                MEDIUMTEXT   NULL,
    attempts              INTEGER      NOT NULL DEFAULT 0,
    claimed_by            VARCHAR(255) NULL,
    claim_token           VARCHAR(64)  NULL,
    entry_count           INTEGER      NULL,
    new_entry_count       INTEGER      NULL,
    new_round_entry_count INTEGER      NULL,
    disqualified_count    INTEGER      NULL,
    warnings              MEDIUMTEXT   NULL,
    error                 TEXT         NULL,
    create_date           DATETIME     NOT NULL,
    start_date            DATETIME     NULL,
    heartbeat_date        DATETIME     NULL,
    finish_date           DATETIME     NULL,
    dismiss_date          DATETIME     NULL,
    dismiss_user_id       INTEGER      NULL,
    flags                 MEDIUMTEXT   NULL,
    PRIMARY KEY (id),
    KEY ix_import_jobs_round_id (round_id),
    KEY ix_import_jobs_user_id (user_id),
    KEY ix_import_jobs_status (status),
    FOREIGN KEY (round_id) REFERENCES rounds (id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (dismiss_user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
