# Deployment Guide - Motorcycle Tracker Alert System

## 🚀 Platform-Independent Deployment

This system can be deployed to any platform that supports:
- **Backend**: Python 3.10+ (FastAPI)
- **Frontend**: Node.js 16+ (React)
- **Database**: PostgreSQL (we use Neon)

---

## ⚠️ SECURITY SETUP (REQUIRED)

### 1. Environment Variables

**NEVER commit `.env` files to Git!** They are ignored by `.gitignore`.

#### Backend Setup (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and fill in:

```bash
# Database - Get from Neon dashboard
DATABASE_URL=postgresql://user:password@host/database?sslmode=require&channel_binding=require

# JWT Secret - Generate new one:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=your_generated_secret_here

# Gemini API (optional) - Get from Google AI Studio
GEMINI_API_KEY=your_key_here

# CORS - Add your frontend domains
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://yourdomain.com

# Environment
APP_ENV=production
```

#### Frontend Setup (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

```bash
REACT_APP_BACKEND_URL=https://your-backend-api.com
PORT=5000
HOST=0.0.0.0
```

---

## 📦 Deployment Platforms

### Vercel (Recommended)

**Frontend:**
```bash
cd frontend
vercel deploy
```

**Backend:**
```bash
cd backend
vercel deploy
```

Set environment variables in Vercel dashboard.

### Railway

1. Create new project
2. Connect GitHub repo
3. Deploy backend and frontend separately
4. Add environment variables in settings

### Render

1. Create Web Service
2. Build command: `pip install -r requirements.txt` (backend) or `yarn build` (frontend)
3. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT` (backend)
4. Add environment variables

### AWS / DigitalOcean / Other VPS

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8080

# Frontend
cd frontend
yarn install
yarn build
yarn start
```

---

## 🔒 Security Checklist

- [ ] Rotate JWT_SECRET_KEY (generate new one)
- [ ] Rotate GEMINI_API_KEY if exposed
- [ ] Never commit `.env` files
- [ ] Use HTTPS in production (set `APP_ENV=production`)
- [ ] Add frontend domains to `ALLOWED_ORIGINS`
- [ ] Enable secure cookies in production

---

## 🗄️ Database Setup

1. Create Neon PostgreSQL database: https://neon.tech
2. Copy connection string to `DATABASE_URL`
3. Tables are created automatically on first run

---

## 📧 Gmail Setup

1. Enable 2FA on Gmail account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Add credentials in Settings page of the app

---

## ✅ Testing Deployment

1. Check backend health: `https://your-backend.com/docs`
2. Login to frontend with admin credentials
3. Test email sync in Settings page

---

## 🆘 Support

For deployment issues, check:
- Backend logs for database connection errors
- Frontend console for CORS issues
- Environment variables are set correctly
