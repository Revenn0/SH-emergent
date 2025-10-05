# Email Categorizer - Replit Setup

## Project Overview

This is an **Email Categorizer** application that uses AI (Google Gemini) to automatically categorize emails from Gmail into different categories:
- Primary
- Social
- Promotions
- Updates
- Spam

### Tech Stack
- **Backend**: Python FastAPI with MongoDB and Google Gemini AI
- **Frontend**: React with Tailwind CSS
- **Authentication**: Google OAuth 2.0 direct integration
- **Email**: Gmail IMAP integration

## Architecture

The project consists of two main components:

1. **Backend** (Port 8080):
   - FastAPI server
   - MongoDB database for storing users, sessions, and categorized emails
   - Google Gemini AI for email categorization
   - Gmail IMAP integration for fetching emails

2. **Frontend** (Port 5000):
   - React application with Create React App
   - Tailwind CSS for styling
   - Axios for API communication
   - Proxy configured to communicate with backend

## Required Configuration

### 1. MongoDB Database

You need to provide a MongoDB connection URL. Update the file `backend/.env`:

```
MONGO_URL=your_mongodb_connection_url_here
DB_NAME=email_categorizer
```

**Options:**
- Use MongoDB Atlas (free tier available)
- Use any other MongoDB hosting service
- Use a local MongoDB instance (not recommended for Replit)

### 2. Google OAuth Credentials

Create OAuth 2.0 credentials in [Google Cloud Console](https://console.cloud.google.com/):

1. Go to "APIs & Services" > "Credentials"
2. Create "OAuth 2.0 Client ID"
3. Add authorized redirect URIs:
   - `https://c363f9ef-5f69-4abe-887f-60d877a4e2ce-00-25ix68esofxzf.riker.replit.dev/api/auth/google/callback`
   - `http://localhost:5000/api/auth/google/callback` (for development)
4. Update `backend/.env`:

```
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
```

### 3. Google Gemini API Key

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey) and update `backend/.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Frontend URL

Update `backend/.env` with your Replit domain:

```
FRONTEND_URL=https://your-repl-domain.replit.dev
```

## How to Use

1. **Configure Environment Variables**: Update `backend/.env` with your MongoDB URL and Gemini API key

2. **Start the Application**: The workflows will start automatically
   - Frontend will be available on port 5000
   - Backend will be available on port 8080 (internal)

3. **Access the App**: Open the web preview in Replit

4. **Login**: Click "Entrar com Google" to authenticate via Google OAuth

5. **Connect Gmail**:
   - Generate a Gmail App Password:
     - Go to myaccount.google.com/security
     - Enable 2-factor authentication
     - Search for "App passwords"
     - Generate a new password for "Mail"
   - Enter your Gmail address and app password in the app

6. **Sync Emails**: Click "Sincronizar" to fetch and categorize your emails

## Project Structure

```
├── backend/
│   ├── server.py          # FastAPI application
│   ├── .env               # Environment variables (needs configuration)
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main React component
│   │   └── components/   # UI components (shadcn/ui)
│   ├── package.json      # Node dependencies and proxy config
│   ├── craco.config.js   # Webpack configuration
│   └── .env              # Frontend environment variables
└── replit.md             # This file

```

## Important Notes

### Workflows

- **Frontend**: Runs on port 5000 (public)
- **Backend**: Runs on port 8080 (internal, proxied through frontend)

### Special Configuration

The backend workflow includes a special `LD_LIBRARY_PATH` configuration to support the grpcio library required by Google Gemini:

```bash
export LD_LIBRARY_PATH=/nix/store/.../gcc-lib/lib:$LD_LIBRARY_PATH
```

This is necessary for the grpcio C extension to find the required C++ standard library.

### CORS Configuration

The backend is configured to allow requests from:
- localhost (development)
- Replit domains

### Proxy Configuration

The frontend uses Create React App's proxy feature to forward API requests to the backend:
- Frontend makes requests to `/api/*`
- Webpack dev server forwards them to `http://localhost:8080/api/*`

## Deployment

The deployment is configured to use a VM (always-on) deployment since:
- The application needs to maintain connections to MongoDB
- Background email sync operations require persistent state
- Authentication sessions need to be maintained

To deploy:
1. Make sure all environment variables are configured
2. Click the "Publish" button in Replit
3. The app will be deployed with both frontend and backend running

## Security Notes

⚠️ **Important Security Considerations:**

1. **Gmail App Passwords**: The app currently stores Gmail app passwords in the database. In production, these should be encrypted.

2. **Environment Variables**: Never commit the `.env` files with real credentials to git. They are already in `.gitignore`.

3. **CORS**: The CORS configuration should be restricted to your specific domains in production.

4. **Session Management**: Sessions expire after 7 days by default.

## Troubleshooting

### Backend Won't Start
- Check that MongoDB URL is valid and accessible
- Verify Gemini API key is correct
- Check backend logs for detailed error messages

### Frontend Can't Connect to Backend
- Verify the proxy is configured in `frontend/package.json`
- Check that backend is running on port 8080
- Review browser console for CORS errors

### Email Sync Fails
- Verify Gmail app password is correct
- Check that 2-factor authentication is enabled on Gmail
- Ensure IMAP is enabled in Gmail settings

## Recent Changes

- **2025-10-05**: Initial Replit setup
  - Configured workflows for frontend and backend
  - Added grpcio library support with LD_LIBRARY_PATH fix
  - Configured proxy for frontend-backend communication
  - Set up CORS for Replit domains
  - Created environment variable templates
  - Replaced Emergent.sh authentication with Google OAuth 2.0 direct integration

## User Preferences

None specified yet.
