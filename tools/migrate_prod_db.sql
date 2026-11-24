-- Production migration: add file_id column to entries table and the
-- campaign_requests table.
-- Companion to revert_prod_db.sql (exact reverse).
-- Idempotent: safe to run more than once.
--
-- Run from Toolforge as the tool account, e.g.:
--   mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud <db> < tools/migrate_prod_db.sql
--
-- Part of hatnote/montage#505 (image/oldimage → file/filerevision migration).

ALTER TABLE entries ADD COLUMN IF NOT EXISTS file_id BIGINT NULL;
CREATE INDEX IF NOT EXISTS ix_entries_file_id ON entries (file_id);

-- hatnote/montage#582: campaign creation requests.

CREATE TABLE IF NOT EXISTS campaign_requests (
    id INTEGER NOT NULL AUTO_INCREMENT,
    request_id VARCHAR(16) NOT NULL,
    submitter_username VARCHAR(255) NOT NULL,
    jury_coordinator_username TEXT NOT NULL,
    commons_category TEXT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    open_date DATETIME NOT NULL,
    close_date DATETIME NOT NULL,
    estimated_image_volume INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    create_date TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    submit_date TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    campaign_id INTEGER NULL,
    clarification_note TEXT NULL,
    is_resubmission BOOL NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
    CHECK (is_resubmission IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE UNIQUE INDEX IF NOT EXISTS ix_campaign_requests_request_id ON campaign_requests (request_id);
CREATE INDEX IF NOT EXISTS ix_campaign_requests_submitter_username ON campaign_requests (submitter_username);
CREATE INDEX IF NOT EXISTS ix_campaign_requests_status ON campaign_requests (status);
CREATE INDEX IF NOT EXISTS ix_campaign_requests_submit_date ON campaign_requests (submit_date);
