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
- Simple username/password authentication
- Clean, modern login page design
- Credentials: `admin` / `admin`

### 2. Dashboard with Sidebar
- Collapsible sidebar navigation
- Three main pages:
  - **Dashboard**: View all alerts with statistics
  - **Admin Panel**: Control sync settings
  - **Settings**: Configure Gmail connection

### 3. Email Filtering
- **Only reads emails from**: `alerts-no-reply@tracking-update.com`
- Uses IMAP search filter for efficiency
- Automatic deduplication (won't read same email twice)

### 4. Tracker Alert Categories
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

### 5. Email Parsing
Extracts important information from tracker emails:
- **Alert Type**: Type of alert triggered
- **Time**: When the alert occurred
- **Location**: Full address
- **Coordinates**: Latitude and Longitude
- **Device Serial Number**: Tracker device ID
- **Tracker Name**: Vehicle/motorcycle identifier
- **Account Name**: Owner account

### 6. Admin Panel
Control sync behavior:
- **Sync Interval**: How often to check for new emails (in minutes)
- **Email Limit**: Maximum emails to fetch per sync (1-200)

### 7. Alert Management
- View all alerts in organized cards
- Delete alerts from app (doesn't delete from Gmail)
- Color-coded categories
- Sortable by date

### 8. Gmail Settings
- Dedicated Settings page for Gmail configuration
- Connect/Disconnect Gmail
- Secure app password storage
- Connection status indicator

## Architecture

### Backend (Port 8080)
- FastAPI REST API
- PostgreSQL database with two tables:
  - `users`: User and Gmail configuration
  - `tracker_alerts`: Parsed alert data
- Email parser using regex patterns
- Alert categorization engine
- IMAP client for Gmail

### Frontend (Port 5000)
- React single-page application
- Responsive design with Tailwind CSS
- Lucide React icons
- Three main views: Dashboard, Admin, Settings
- Local storage for session management

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
1. Navigate to **Settings** page
2. Generate a Gmail App Password:
   - Go to myaccount.google.com/security
   - Enable 2-factor authentication
   - Search for "App passwords"
   - Generate password for "Mail"
3. Enter Gmail address and app password
4. Click "Connect Gmail"

### 6. Sync Alerts
1. Go to **Dashboard**
2. Click "Sync Now"
3. Alerts will be fetched and displayed

### 7. Admin Controls (Optional)
1. Go to **Admin Panel**
2. Adjust sync interval and email limit
3. Save settings

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
- `GET /api/alerts/list` - Get all alerts and statistics
- `POST /api/alerts/sync` - Sync new alerts from Gmail
- `DELETE /api/alerts/{id}` - Delete alert from app

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
- Click "Sync Now" to fetch emails
- Check that Gmail is connected in Settings
- Verify emails exist from tracker sender
- Review backend logs for sync errors

## Recent Changes

- **2025-10-05**: Complete System Redesign
  - Removed generic email categorization
  - Implemented motorcycle tracker alert system
  - Added login page (admin/admin)
  - Created dashboard with sidebar layout
  - Added email filtering for alerts-no-reply@tracking-update.com only
  - Implemented 14 tracker alert categories
  - Built email parser to extract alert details
  - Created admin panel for sync controls
  - Added delete functionality (app-only, doesn't affect Gmail)
  - Moved Gmail settings to dedicated Settings page
  - Removed "Made with Emergent" footer
  - Used Lucide React icons for modern UI

## User Preferences

None specified yet.
