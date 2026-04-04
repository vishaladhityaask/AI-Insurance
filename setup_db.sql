-- ============================================================
-- GigShield Phase 2 — Database Setup
-- ============================================================

CREATE DATABASE IF NOT EXISTS gig_insurance;
USE gig_insurance;

-- Workers table (extended for Phase 2)
CREATE TABLE IF NOT EXISTS workers (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120)  NOT NULL,
    city          VARCHAR(80)   NOT NULL,
    platform      VARCHAR(80)   NOT NULL,
    daily_income  INT           NOT NULL,
    premium       INT           NOT NULL,
    hours_per_day FLOAT         DEFAULT 8.0,
    registered_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- Claims table (zero-touch auto claims)
CREATE TABLE IF NOT EXISTS claims (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    worker_id      INT          NOT NULL,
    claim_id       VARCHAR(30)  NOT NULL,
    trigger_type   VARCHAR(30)  NOT NULL,
    trigger_label  VARCHAR(80)  NOT NULL,
    payout_amount  INT          NOT NULL,
    coverage_pct   INT          NOT NULL,
    status         VARCHAR(20)  DEFAULT 'AUTO_APPROVED',
    processed_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
);

-- Verify
SHOW TABLES;
