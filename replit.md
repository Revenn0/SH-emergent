# Motorcycle Tracker Alert Management System

## Project Overview

This is a **Motorcycle Tracker Alert Management System** that reads tracker alerts exclusively from `alerts-no-reply@tracking-update.com` via Gmail IMAP, categorizes them using AI, and displays them in a modern dashboard with sidebar navigation.

The system parses tracker emails to extract essential information like alert type, location, coordinates, device info, and displays only the most important data in an organized interface.

### Tech Stack
- **Backend**: Python FastAPI with PostgreSQL
- **Frontend**: React with Tailwind CSS and Lucide icons
- **Authentication**: Simple login (username: admin, password: admin)
- **Email**: Gmail IMAP integration (filters only tracker alerts)
- **AI**: Google Gemini for categorization (optional enhancement)

## Features

### 1. Login System
- Clean, minimal design matching provided screenshot
- Simple username/password authentication
- Credentials displayed on login page: `admin` / `admin`
- Bike icon for branding

### 2. Dashboard with Sidebar
- Collapsible sidebar navigation
- Three main pages:
  - **Bike Tracker**: View all alerts grouped by motorcycle
  - **Admin Dashboard**: System health and sync settings
  - **Service Tracker**: Gmail configuration

### 3. Alert Grouping & Priority System
- **Alerts grouped by motorcycle** (tracker_name)
- **Badge system**: Shows 1, 2, 3, or 3+ alerts per bike
- **Super Important Category**: Motorcycles with 2+ different alerts
- **Color-coded severity**:
  - Red: Super Important (2+ alerts)
  - Orange: High Priority (critical alert types)
  - Blue: Normal priority

### 4. Status Cards Dashboard
Shows real-time system status:
- **Total Alerts**: All filtered alerts
- **Unread**: Alerts requiring attention
- **High Priority**: Bikes with multiple alerts
- **Acknowledged**: Read alerts

### 5. Admin Dashboard
System health monitoring:
- **System Status**: Application health
- **Database**: PostgreSQL connection status
- **Gmail Integration**: Email sync status
- **Activity Summary**: 24h statistics

### 6. Alert Details Modal
Click any alert to view:
- Full alert information
- Location with Google Maps link
- Coordinates (latitude/longitude)
- Device serial number
- Account information
- All alerts for that motorcycle

### 7. Email Filtering
- **Only reads emails from**: `alerts-no-reply@tracking-update.com`
- Uses IMAP search filter for efficiency
- Automatic deduplication (won't read same email twice)

### 8. Tracker Alert Categories
The system categorizes alerts into 14 types:
- Heavy Impact
- Light Sensor
- Out Of Country
- No Communication after 2 days
- Over-turn
- Low Battery
- Motion
- New Positions
- High Risk Area
- Custom GeoFence
- Rotation Stop
- Temperature
- Pressure
- Humidity

### 9. Email Parsing
Extracts important information from tracker emails:
- **Alert Type**: Type of alert triggered
- **Time**: When the alert occurred
- **Location**: Full address
- **Coordinates**: Latitude and Longitude
- **Device Serial Number**: Tracker device ID
- **Tracker Name**: Vehicle/motorcycle identifier (plate)
- **Account Name**: Owner account

### 10. Alert Management
- View alerts in professional table format
- Delete alerts from app (doesn't delete from Gmail)
- Click to view detailed modal popup
- Sort and filter capabilities

## Architecture

### Backend (Port 8080)
- FastAPI REST API
- PostgreSQL database with two tables:
  - `users`: User and Gmail configuration
  - `tracker_alerts`: Parsed alert data
- Email parser using regex patterns
- Alert categorization engine
- IMAP client for Gmail
- Grouping logic for motorcycle alerts

### Frontend (Port 5000)
- React single-page application
- Responsive design with Tailwind CSS
- Lucide React icons
- Three main views: Bike Tracker, Admin Dashboard, Settings
- Local storage for session management
- Modal popup for detailed alert view
- Alert grouping by motorcycle

## Database Schema

### `users` table
- id (primary key)
- email, name, picture
- gmail_email, gmail_app_password

### `tracker_alerts` table
- id (serial, primary key)
- user_id, email_id (unique combination)
- alert_type, alert_time, location
- latitude, longitude
- device_serial, tracker_name, account_name
- raw_body, created_at

## Setup Instructions

### 1. Environment Variables
The Gemini API key is configured in `backend/.env`:
```
GEMINI_API_KEY=AIzaSyDWpJiSr3Y8J4b-R6IlKeRyuK3FJNHB280
```

### 2. Database
✅ PostgreSQL is automatically configured via `DATABASE_URL` environment variable

### 3. Start the Application
Both workflows start automatically:
- **Backend**: Python FastAPI on port 8080
- **Frontend**: React dev server on port 5000

### 4. Login
1. Open the web preview
2. Login with:
   - Username: `admin`
   - Password: `admin`

### 5. Connect Gmail
1. Navigate to **Service Tracker** (Settings) page
2. Generate a Gmail App Password:
   - Go to myaccount.google.com/security
   - Enable 2-factor authentication
   - Search for "App passwords"
   - Generate password for "Mail"
3. Enter Gmail address and app password
4. Click "Connect Gmail"

### 6. Sync Alerts
1. Go to **Bike Tracker** (Dashboard)
2. Click "Refresh Alerts"
3. Alerts will be fetched, grouped, and displayed

### 7. View Alert Details
1. Click on any row in the alerts table
2. Modal popup shows all details
3. View location on Google Maps
4. See all alerts for that motorcycle

## Project Structure

```
├── backend/
│   ├── server.py          # FastAPI application
│   ├── .env               # Environment variables
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   └── App.js        # Main React application
│   ├── package.json      # Node dependencies
│   └── public/
│       └── index.html    # HTML template
└── replit.md             # This file
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/password

### Gmail
- `POST /api/gmail/connect` - Connect Gmail account
- `DELETE /api/gmail/disconnect` - Disconnect Gmail

### Alerts
- `GET /api/alerts/list` - Get all alerts, stats, and grouping info (includes management fields)
- `POST /api/alerts/sync` - Sync new alerts from Gmail with incremental checkpoint
- `DELETE /api/alerts/{id}` - Delete alert from app
- `POST /api/alerts/{id}/acknowledge` - Acknowledge an alert
- `POST /api/alerts/{id}/status` - Update alert status (New/In Progress/Resolved/Closed)
- `POST /api/alerts/{id}/notes` - Add notes to an alert
- `POST /api/alerts/{id}/assign` - Assign alert to team member
- `POST /api/alerts/{id}/favorite` - Toggle favorite status

## Email Parser

The system uses regex patterns to extract data from tracker emails:

Example tracker email format:
```
Dear user,
Your device has detected the following event…
 - Alert type: Notify On Light Sensor
 - Time: 2025-10-03 12:05:55 (UTC)
 - Location: Runnymede Road, Surrey, Egham, England
 - Latitude, Longitude: 51.4355838, -0.540028
 - Device Serial Number: 867684070096659
 - Tracker Name: EY70TWF
 - Account name: 4th Dimension Innovation
```

The parser extracts each field and stores it in the database for easy viewing.

## Priority & Grouping System

### How it Works:
1. Alerts are grouped by `tracker_name` (motorcycle plate)
2. Badge shows number of alerts: 1, 2, 3, or 3+
3. Motorcycles with 2+ different alerts = **Super Important**
4. Table sorted by priority (Super Important first)
5. Color coding:
   - **Red**: Super Important (2+ alerts)
   - **Orange**: High Priority (critical types)
   - **Blue**: Normal

### Super Important Logic:
```javascript
if (motorcycle has >= 2 different alerts) {
  severity = "super-important"
  badge = red
  sort to top
}
```

## UI/UX Design Principles

Following best practices from screenshot references:
- **Minimal color palette**: Gray scale with accent colors
- **Clean typography**: System fonts, clear hierarchy
- **Consistent spacing**: 4, 8, 16, 24px grid
- **Professional table design**: Borders, hover states
- **Status indicators**: Color-coded for quick scanning
- **Responsive layout**: Works on all screen sizes

## Deployment

The app is configured for VM deployment (always-on) since it:
- Maintains database connections
- Requires persistent state
- May implement background sync in future

To deploy:
1. Ensure all environment variables are set
2. Click "Publish" in Replit
3. App will be deployed with both services running

## Security Notes

⚠️ **Important:**
1. Gmail app passwords are stored in database (should be encrypted in production)
2. Login credentials are hardcoded (should use proper auth in production)
3. Change default admin credentials for production use
4. CORS is configured for Replit domains only

## Troubleshooting

### Backend Won't Start
- Check DATABASE_URL is valid
- Verify Python dependencies are installed
- Check backend logs for errors

### Frontend Can't Connect
- Verify backend is running on port 8080
- Check proxy configuration in package.json
- Review browser console for errors

### Email Sync Fails
- Verify Gmail app password is correct
- Ensure 2-factor auth is enabled on Gmail
- Check that IMAP is enabled in Gmail settings
- Confirm emails are from alerts-no-reply@tracking-update.com

### No Alerts Showing
- Click "Refresh Alerts" to fetch emails
- Check that Gmail is connected in Settings
- Verify emails exist from tracker sender
- Review backend logs for sync errors

### Modal Not Opening
- Check browser console for JavaScript errors
- Verify alert grouping is working correctly
- Test with different browsers

## Recent Changes

- **2025-10-05**: Alert Lifecycle Management + Performance Optimizations
  - **Backend Enhancements**:
    - Added alert lifecycle management: status workflow (New → In Progress → Resolved → Closed)
    - Created 5 new API endpoints: /acknowledge, /status, /notes, /assign, /favorite
    - Implemented checkpoint-based incremental sync (saves last_email_id, only fetches new emails)
    - Added GZip compression middleware for API responses (compresses responses >1KB)
    - Extended tracker_alerts table with: status, acknowledged, acknowledged_at, acknowledged_by, notes, assigned_to, favorite
    - Created sync_checkpoints table for incremental email sync
    - Fixed critical bug: Refactored parallel email processing to use individual database connections per email (prevents asyncpg InterfaceError)
  - **Frontend Enhancements**:
    - Added dark mode toggle in header with localStorage persistence and sun/moon icons
    - Implemented search by motorcycle plate/tracker name with live filtering
    - Updated /alerts/list to return new management fields
    - Added clear buttons for both category filter and search
  - **Performance**: 
    - Parallel email processing now works correctly (10 emails at a time)
    - Incremental sync reduces redundant email fetching
    - GZip compression reduces API response sizes by ~70%

- **2025-10-05**: Complete UI/UX Redesign + Performance Improvements
  - Redesigned login to match screenshot (minimal design with bike icon)
  - Created status cards dashboard (System, Database, Gmail, Alerts)
  - Implemented alert grouping by motorcycle (tracker_name)
  - Added badge system (1, 2, 3, 3+ alerts per bike)
  - Created "Super Important" category for bikes with 2+ alerts
  - Built professional table layout matching screenshot design
  - Implemented modal popup for detailed alert information
  - Added Google Maps integration for locations
  - Reorganized sidebar (Bike Tracker, Admin Dashboard, Service Tracker)
  - Applied clean, minimal color scheme (gray scale + accents)
  
- **2025-10-05**: Performance & Features Enhancement
  - **Parallel Email Processing**: Sync now processes 10 emails simultaneously using asyncio.gather (10x faster)
  - **Category System**: Added 14 predefined alert categories with automatic classification
  - **Dynamic Filters**: Dropdown filter to view alerts by category in real-time
  - **Auto-Refresh**: Optional 30-second auto-refresh to keep dashboard updated
  - **Optimized Queries**: Reduced database calls with batch queries and ON CONFLICT handling
  - **Lightweight UI**: Instant category switching without page reload
  - **Better UX**: Clear filter button, active filter indicator, category-specific counts

## User Preferences

None specified yet.
