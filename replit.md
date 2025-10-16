# Motorcycle Tracker Alert Management System

## Overview
This project is a **Motorcycle Tracker Alert Management System** designed to monitor and manage alerts from motorcycle trackers. It exclusively processes emails from `alerts-no-reply@tracking-update.com` via Gmail IMAP, categorizes these alerts using AI, and presents them in a modern, user-friendly dashboard. The system's core purpose is to parse tracker emails, extract critical information (alert type, location, coordinates, device info), and display it in an organized interface, prioritizing important data. The goal is to provide real-time insights into motorcycle statuses and potential issues, offering a robust solution for vehicle monitoring and alert management.

## User Preferences
None specified yet.

## System Architecture
The system employs a client-server architecture with a Python FastAPI backend and a React frontend.

### UI/UX Decisions
- **Design**: Minimal, clean design with a grayscale color palette, accent colors, and clear typography.
- **Layout**: Collapsible sidebar navigation, professional table designs with hover states, and a responsive layout.
- **Branding**: Bike icon for branding, enhanced motorcycle icons, and color-coded status indicators.
- **Enhanced Device Display**: Prominent device identification, motorcycle badges in tables, and visible alert count badges.
- **Alert Modal Improvements**: Redesigned with clear visual hierarchy, prominent device header, status summary, individual alert cards with color-coded icons, improved information layout, and integrated Google Maps button.

### Technical Implementations
- **Authentication System**: Secure cookie-based JWT authentication with multi-user support, HttpOnly cookies, environment-aware cookie security, and role-based access control (Admin/Viewer).
- **Bikes Management System**: Tracks motorcycles with device serials, alert counts, latest alert times, and allows for adding notes to each bike. Auto-populates from tracker alerts.
- **Dashboard**: Features status cards for system health, total alerts, high priority, and acknowledged alerts.
- **Alert Grouping**: Alerts are grouped by `tracker_name` with a badge system showing actual count.
- **Priority System**: Categorizes alerts into Crash Detected (highest severity), High Priority, and Normal Priority based on alert types.
- **Alert Details Modal**: Provides comprehensive alert information, including location with Google Maps link, coordinates, device serial number, and all alerts for that specific motorcycle, along with "Record Action" button.
- **Timestamp Formatting**: All timestamps display in UK format (dd/mm/yyyy HH:MM).
- **Email Filtering & Parsing**: Processes only emails from `alerts-no-reply@tracking-update.com` using IMAP, includes deduplication, and extracts critical alert data using regex.
- **Email Reading System**: Emails are automatically read every 10 minutes in a background task and inserted into the database. A "Refresh Alerts" button reloads data from the database.
- **Alert Management**: Allows viewing, sorting, filtering, deleting, acknowledging, updating status, adding notes, assigning, and favoriting alerts.
- **Automatic Background Synchronization**: A background task fetches new emails incrementally every hour.
- **Progressive Email Sync**: Processes emails in batches with real-time progress tracking, parallel processing, and a non-blocking UI.
- **Silent Auto-Refresh System**: Automatically refreshes alert tables and system status every 60 seconds without user interaction or loading spinners.
- **Bikes Page Performance**: Optimized for instant loading using a single CTE query and bulk upserts.
- **Pagination System**: SQL-based pagination with LIMIT/OFFSET for efficient data loading.
- **Infinite Scroll**: Implemented with IntersectionObserver for seamless alert loading.
- **Date Filtering**: Quick filters (Today, Last Week, Last Month, All Time) and a single date picker.
- **CSV Export**: Exports filtered alerts to CSV with comprehensive data and user-scoped security.
- **Data Ordering**: All lists display newest-first.
- **Alert Table**: 
    - Simplified 6-column layout (Device, Type, Category, Message, Severity, Timestamp) with proper alignment
    - **Grouping**: Alerts grouped by motorcycle - 1 bike = 1 row in table (even if bike has 20+ alerts)
    - **Count Display**: "Showing" count reflects number of motorcycles, not individual alerts
    - Click on any row to see all alerts for that specific motorcycle in modal

### System Design Choices
- **Backend**: FastAPI (Port 8080) with Neon PostgreSQL.
- **Frontend**: React SPA (Port 5000) with Tailwind CSS and Lucide React icons.
- **Database**: Neon PostgreSQL, with a defined schema for `users`, `tracker_alerts`, `bikes`, `bike_notes`, `sync_checkpoints`, and `refresh_tokens` tables.
- **Deployment**: Configured for VM (always-on) deployment.

## External Dependencies
- **Email Service**: Gmail IMAP (for `alerts-no-reply@tracking-update.com`)
- **Database**: Neon PostgreSQL
- **AI**: Google Gemini (optional, for alert categorization)
- **Mapping**: Google Maps
- **Frontend Framework**: React
- **Styling**: Tailwind CSS
- **Icons**: Lucide React icons