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
- **Branding**: Bike icon for branding on the login page.
- **Status Indicators**: Color-coded indicators for quick scanning of alert severities.

### Technical Implementations
- **Authentication System**: JWT-based authentication with multi-user support:
    - Access tokens (60min expiry) and refresh tokens (7 days expiry) using HS256 algorithm
    - Argon2 password hashing for secure credential storage
    - User registration with email validation
    - Automatic token refresh via axios interceptors on 401 responses
    - All API routes protected via JWT dependency injection
    - Admin user auto-created on startup (username: `admin`, password: `dimension`)
    - **Security Note**: Current implementation stores refresh tokens in localStorage (XSS vulnerability). For production, migrate to httpOnly cookies for enhanced security.
- **Dashboard**: Features status cards for system health, total alerts, unread, high priority, and acknowledged alerts.
- **Alert Grouping**: Alerts are grouped by `tracker_name` (motorcycle) with a badge system indicating the number of alerts per bike.
- **Priority System**:
    - **Super Important**: Motorcycles with 2+ different alerts (Red).
    - **High Priority**: Critical alert types (Orange).
    - **Normal Priority**: Standard alerts (Blue).
- **Alert Details Modal**: Provides comprehensive alert information, including location with Google Maps link, coordinates, device serial number, and all alerts for that specific motorcycle.
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

### Feature Specifications
- **Alert Categories**: 14 predefined alert types including Heavy Impact, Light Sensor, Out Of Country, No Communication, Over-turn, Low Battery, Motion, New Positions, High Risk Area, Custom GeoFence, Rotation Stop, Temperature, Pressure, and Humidity.
- **Alert Lifecycle Management**: Supports a workflow for alerts with statuses: New, In Progress, Resolved, Closed.

### System Design Choices
- **Backend (Port 8080)**: FastAPI with PostgreSQL, handling email parsing, alert categorization, IMAP client operations, and alert grouping logic.
- **Frontend (Port 5000)**: React SPA with Tailwind CSS and Lucide React icons, providing a responsive user interface across "Bike Tracker", "Admin Dashboard", and "Service Tracker" views. Uses local storage for session management.
- **Database Schema**:
    - `users` table: Stores user authentication and Gmail configuration (`id`, `username`, `password_hash`, `email`, `full_name`, `gmail_email`, `gmail_app_password`, `created_at`, `updated_at`).
    - `tracker_alerts` table: Stores parsed alert data (`id`, `user_id`, `email_id`, `alert_type`, `alert_time`, `location`, `latitude`, `longitude`, `device_serial`, `tracker_name`, `account_name`, `raw_body`, `created_at`, `status`, `acknowledged`, `acknowledged_at`, `acknowledged_by`, `notes`, `assigned_to`, `favorite`).
    - `sync_checkpoints` table: For incremental email synchronization (per-user tracking).
- **Deployment**: Configured for VM (always-on) deployment due to persistent state, continuous uptime requirement for alert monitoring, and background synchronization.

## External Dependencies
- **Email Service**: Gmail IMAP (for `alerts-no-reply@tracking-update.com`)
- **Database**: PostgreSQL
- **AI**: Google Gemini (for alert categorization, optional)
- **Mapping**: Google Maps (for displaying alert locations)
- **Frontend Framework**: React
- **Styling**: Tailwind CSS
- **Icons**: Lucide React icons