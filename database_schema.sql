-- Tracker Alerts System - Database Schema
-- PostgreSQL (Neon) Database Tables
-- Run this script to create all required tables if they don't exist

-- Users table - Stores user accounts with authentication
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    gmail_email VARCHAR(255),
    gmail_app_password TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_interval_minutes INTEGER DEFAULT 10,
    email_limit_per_sync INTEGER DEFAULT 100,
    role VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('admin', 'viewer'))
);

-- Bikes table - Stores motorcycle/tracker device information
CREATE TABLE IF NOT EXISTS bikes (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    device_serial VARCHAR(255) UNIQUE NOT NULL,
    tracker_name VARCHAR(255),
    notes TEXT,
    alert_count INTEGER DEFAULT 0,
    latest_alert_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracker Alerts table - Stores all alerts from email parsing
CREATE TABLE IF NOT EXISTS tracker_alerts (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    email_subject TEXT,
    email_body TEXT,
    email_date TIMESTAMP,
    tracker_name VARCHAR(255),
    device_serial VARCHAR(255),
    alert_type VARCHAR(255),
    alert_message TEXT,
    location TEXT,
    coordinates VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    severity VARCHAR(50) DEFAULT 'normal',
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR,
    status VARCHAR(50) DEFAULT 'new',
    assigned_to VARCHAR(255),
    notes TEXT,
    favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_email_id VARCHAR(255) UNIQUE
);

-- Bike Notes table - Stores notes for each bike
CREATE TABLE IF NOT EXISTS bike_notes (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    bike_id VARCHAR REFERENCES bikes(id) ON DELETE CASCADE,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sync Checkpoints table - Tracks email synchronization progress
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    last_synced_email_id VARCHAR(255),
    last_synced_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Refresh Tokens table - Stores JWT refresh tokens for authentication
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email Sync Runs table - Tracks background email sync operations
CREATE TABLE IF NOT EXISTS email_sync_runs (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running',
    emails_processed INTEGER DEFAULT 0,
    alerts_created INTEGER DEFAULT 0,
    error_message TEXT
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_user_id ON tracker_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_device_serial ON tracker_alerts(device_serial);
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_created_at ON tracker_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_severity ON tracker_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_bikes_device_serial ON bikes(device_serial);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_user_id ON sync_checkpoints(user_id);
CREATE INDEX IF NOT EXISTS idx_bike_notes_bike_id ON bike_notes(bike_id);
