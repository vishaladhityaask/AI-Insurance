-- ============================================================
-- GigShield – Phase 1 Database Setup
-- Run this in your MySQL client before starting the Flask app
-- ============================================================

-- 1. Create the database
CREATE DATABASE IF NOT EXISTS gig_insurance;

-- 2. Switch to it
USE gig_insurance;

-- 3. Create the workers table
CREATE TABLE IF NOT EXISTS workers (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120)  NOT NULL,
    city          VARCHAR(80)   NOT NULL,
    platform      VARCHAR(80)   NOT NULL,
    daily_income  INT           NOT NULL,
    premium       INT           NOT NULL,
    registered_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- 4. (Optional) Seed with demo data to see the admin page
INSERT INTO workers (name, city, platform, daily_income, premium) VALUES
  ('Ravi Kumar',   'Mumbai',    'Swiggy',  950,  30),
  ('Priya Sharma', 'Bengaluru', 'Zomato',  1350, 50),
  ('Ankit Verma',  'Delhi',     'Amazon',  680,  20);

-- Verify
SELECT * FROM workers;
