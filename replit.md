# Motorcycle Tracker Alert Management System

## Overview
This project is a **Motorcycle Tracker Alert Management System** designed to monitor and manage alerts from motorcycle trackers. It exclusively processes emails from `alerts-no-reply@tracking-update.com` via Gmail IMAP, categorizes these alerts using AI, and presents them in a modern, user-friendly dashboard. The system's core purpose is to parse tracker emails, extract critical information (alert type, location, coordinates, device info), and display it in an organized interface, prioritizing important data. The goal is to provide real-time insights into motorcycle statuses and potential issues, offering a robust solution for vehicle monitoring and alert management.

## User Preferences
None specified yet.

## System Architecture
The system employs a client-server architecture with a Python FastAPI backend and a React frontend.

### UI/UX Decisions
- **Design**: Minimal, clean design with a grayscale color palette and accent colors.
- **Typography**: Clean typography with clear hierarchy, using system fonts.
- **Layout**: Collapsible sidebar navigation, professional table designs with hover states, and a responsive layout for all screen sizes.
- **Branding**: Bike icon for branding on the login page and enhanced motorcycle icons in the dashboard.
- **Status Indicators**: Color-coded indicators for quick scanning of alert severities.
- **Enhanced Device Display**: 
    - Motorcycle badge in table with prominent bike icon, larger bold text, and visible alert count badge
    - Larger, more prominent device identification in alert modals
- **Alert Modal Improvements**: 
    - Redesigned with clear visual hierarchy and sections
    - Prominent device header with motorcycle icon and alert count
    - Status summary section with visual indicators
    - Individual alert cards with color-coded icons
    - Improved information layout with icons for Location, Coordinates, Device Serial, and Account
    - Prominent Google Maps integration button
    - Better action button placement and styling

### Technical Implementations
- **Authentication System**: Secure cookie-based JWT authentication with multi-user support:
    - **HttpOnly Cookies**: Access and refresh tokens stored in secure HttpOnly cookies (not localStorage)
    - Access tokens (60min expiry) and refresh tokens (7 days expiry) using HS256 algorithm
    - Refresh tokens stored as SHA256 hashes in `refresh_tokens` database table with expiration tracking
    - Token revocation support via database-backed refresh token management
    - Argon2 password hashing for secure credential storage
    - User registration with email validation
    - Automatic token refresh on 401 responses with cookie-based flow
    - All API routes protected via JWT dependency injection from cookies
    - Admin user auto-created on startup (username: `admin`, password: `dimension`)
    - **Security**: HttpOnly, Secure, SameSite=lax cookies protect against XSS and CSRF attacks
- **Bikes Management System**: Complete bike tracking and history management:
    - **Bikes List**: View all motorcycles with device serial, alert count, and latest alert time
    - **Bike History**: Individual bike history showing all alerts and notes in chronological order (newest first)
    - **Note Taking**: Add notes for each bike (e.g., "called client, no issues with bike")
    - **Navigation**: Access bike history from Bikes page or by clicking bike name in alert modals
    - **Record Action**: Quick access button in alert modals to add notes to the bike
    - Auto-populated from tracker alerts with automatic bike record creation
- **Dashboard**: Features status cards for system health, total alerts, high priority, and acknowledged alerts (changed "Unread" to "High Priority").
- **Alert Grouping**: Alerts are grouped by `tracker_name` (motorcycle) with a badge system showing actual count (e.g., "5" or "99+" for 100+).
- **Priority System**:
    - **Crash Detected**: Crash detect (Over-turn + Heavy impact) + Tamper Alert combination (Highest severity - Red).
    - **Crash detect**: Over-turn + Heavy impact detected (Red).
    - **High Priority**: Other critical alert types (Orange).
    - **Normal Priority**: Standard alerts (Blue).
- **Alert Details Modal**: Provides comprehensive alert information, including location with Google Maps link, coordinates, device serial number, and all alerts for that specific motorcycle. Includes "Record Action" button and clickable bike name to access bike history.
- **Timestamp Formatting**: All timestamps display in UK format (dd/mm/yyyy HH:MM) consistently across the application.
- **Email Filtering**: Only processes emails from `alerts-no-reply@tracking-update.com` using IMAP search filters and includes automatic deduplication.
- **Email Parsing**: Extracts `Alert Type`, `Time`, `Location`, `Coordinates`, `Device Serial Number`, `Tracker Name`, and `Account Name` using regex patterns.
- **Email Reading System**:
    - **Background Task Only**: Emails are automatically read every 10 minutes and inserted directly into the database
    - **Refresh Alerts** button: Reloads alerts from database only (no manual email reading)
    - **Login Synchronization**: User login only synchronizes with the already-updated database
    - Simple, reliable architecture with automatic background processing
- **Alert Management**: Allows viewing, sorting, filtering, and deleting alerts (within the app only), along with features for acknowledging, updating status, adding notes, assigning, and favoriting alerts.
- **Automatic Background Synchronization**: A background task runs every 10 minutes to fetch new emails incrementally (up to 100 emails per sync) and inserts them directly into the database.
- **Pagination System**: SQL-based pagination with LIMIT/OFFSET for efficient data loading (default 50 items/page, max 200). Includes aggregate queries for statistics without loading full dataset.
- **Data Ordering**: All lists display newest-first (ORDER BY created_at DESC) for alerts, notes, and bike history.

### Feature Specifications
- **Alert Categories**: 15 predefined alert types including Crash detect (Over-turn + Heavy impact), Light Sensor, Out Of Country, No Communication, Over-turn, Low Battery, Motion, New Positions, High Risk Area, Custom GeoFence, Rotation Stop, Temperature, Pressure, Humidity, and Tamper Alert.
- **Alert Categorization Rules**:
    - **Crash Detected**: Crash detect + Over-turn + Tamper Alert (Highest severity)
    - **Crash detect**: Replaces "Heavy Impact" - detects over-turn combined with heavy impact events
    - Previous rule (Light Sensor + Over-turn = Heavy Impact) has been removed
- **Alert Lifecycle Management**: Supports a workflow for alerts with statuses: New, In Progress, Resolved, Closed.

### System Design Choices
- **Backend (Port 8080)**: FastAPI with Neon PostgreSQL, handling email parsing, alert categorization, IMAP client operations, and alert grouping logic.
- **Frontend (Port 5000)**: React SPA with Tailwind CSS and Lucide React icons, providing a responsive user interface across "Bike Tracker", "Admin Dashboard", and "Service Tracker" views. Uses local storage for session management.
- **Database**: Neon PostgreSQL (cloud-hosted, managed database service)
    - Connection string stored securely in `DATABASE_URL` environment variable
    - Setup script available in `neon_database_setup.sql` for initial database configuration
- **Database Schema**:
    - `users` table: Stores user authentication and Gmail configuration (`id`, `username`, `password_hash`, `email`, `full_name`, `gmail_email`, `gmail_app_password`, `created_at`, `updated_at`).
    - `tracker_alerts` table: Stores parsed alert data (`id`, `user_id`, `email_id`, `alert_type`, `alert_time`, `location`, `latitude`, `longitude`, `device_serial`, `tracker_name`, `account_name`, `raw_body`, `created_at`, `status`, `acknowledged`, `acknowledged_at`, `acknowledged_by`, `notes`, `assigned_to`, `favorite`).
    - `bikes` table: Stores bike records (`id`, `user_id`, `tracker_name`, `device_serial`, `latest_alert_at`, `created_at`, `updated_at`). Auto-populated from tracker alerts with unique constraint on user_id + tracker_name.
    - `bike_notes` table: Stores notes for bikes (`id`, `bike_id`, `user_id`, `note`, `author`, `created_at`). All notes display newest-first.
    - `sync_checkpoints` table: For incremental email synchronization (per-user tracking).
    - `refresh_tokens` table: Stores hashed refresh tokens for secure session management and token revocation.
- **Database Migration**: `migration_to_production.sql` script available in project root for migrating development data to production database with complete instructions and validation steps.
- **Deployment**: Configured for VM (always-on) deployment due to persistent state, continuous uptime requirement for alert monitoring, and background synchronization.

## External Dependencies
- **Email Service**: Gmail IMAP (for `alerts-no-reply@tracking-update.com`)
- **Database**: Neon PostgreSQL (cloud-hosted managed database)
- **AI**: Google Gemini (for alert categorization, optional)
- **Mapping**: Google Maps (for displaying alert locations)
- **Frontend Framework**: React
- **Styling**: Tailwind CSS
- **Icons**: Lucide React icons

## Database Setup
To set up the Neon PostgreSQL database:
1. Create a Neon account and database at https://neon.tech
2. Copy the connection string provided by Neon
3. Add the connection string as `DATABASE_URL` in Replit Secrets
4. Run the SQL script in `neon_database_setup.sql` in the Neon SQL Editor to create all required tables and indexes
5. The application will automatically connect to Neon on startup and create the default admin user (username: `admin`, password: `dimension`)