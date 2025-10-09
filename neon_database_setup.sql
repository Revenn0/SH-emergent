-- ==========================================
-- NEON DATABASE SETUP SCRIPT
-- Tracker Alert Management System
-- ==========================================

-- Table: users
-- Stores user authentication and Gmail configuration
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR,
    gmail_email VARCHAR,
    gmail_app_password VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: tracker_alerts
-- Stores parsed alert data from email notifications
CREATE TABLE IF NOT EXISTS tracker_alerts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    email_id VARCHAR NOT NULL,
    alert_type VARCHAR,
    alert_time VARCHAR,
    location VARCHAR,
    latitude VARCHAR,
    longitude VARCHAR,
    device_serial VARCHAR,
    tracker_name VARCHAR,
    account_name VARCHAR,
    raw_body TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR DEFAULT 'New',
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR,
    notes TEXT,
    assigned_to VARCHAR,
    favorite BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, email_id)
);

-- Table: sync_checkpoints
-- Tracks last synchronized email for incremental syncing
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL UNIQUE,
    last_email_id VARCHAR,
    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: bikes
-- Stores motorcycle/tracker device information
CREATE TABLE IF NOT EXISTS bikes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    tracker_name VARCHAR NOT NULL,
    device_serial VARCHAR,
    latest_alert_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tracker_name)
);

-- Index: bikes by user_id
CREATE INDEX IF NOT EXISTS idx_bikes_user_id ON bikes(user_id);

-- Index: bikes by tracker_name
CREATE INDEX IF NOT EXISTS idx_bikes_tracker_name ON bikes(tracker_name);

-- Table: bike_notes
-- Stores notes/comments associated with bikes
CREATE TABLE IF NOT EXISTS bike_notes (
    id SERIAL PRIMARY KEY,
    bike_id INTEGER NOT NULL,
    user_id VARCHAR NOT NULL,
    note TEXT NOT NULL,
    author VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bike_id) REFERENCES bikes(id) ON DELETE CASCADE
);

-- Index: bike_notes by bike_id
CREATE INDEX IF NOT EXISTS idx_bike_notes_bike_id ON bike_notes(bike_id);

-- Table: email_sync_runs
-- Logs email synchronization runs for debugging and monitoring
CREATE TABLE IF NOT EXISTS email_sync_runs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    source VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    emails_read INTEGER DEFAULT 0,
    emails_new INTEGER DEFAULT 0,
    error_summary TEXT,
    log_json TEXT
);

-- Table: refresh_tokens
-- Stores hashed refresh tokens for session management
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    token_hash VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==========================================
-- DEFAULT ADMIN USER
-- Username: admin
-- Password: dimension
-- ==========================================
-- Note: You can insert the admin user manually or let the application create it on first startup
-- INSERT INTO users (id, username, email, password_hash, full_name)
-- VALUES (
--     'admin-default-uuid',
--     'admin',
--     'admin@tracker.com',
--     '$argon2id$v=19$m=65536,t=3,p=4$...',  -- Hash for 'dimension'
--     'Administrator'
-- );

-- ==========================================
-- VERIFICATION QUERIES
-- ==========================================
-- Check all tables created
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check all indexes created
-- SELECT indexname FROM pg_indexes WHERE schemaname = 'public';
