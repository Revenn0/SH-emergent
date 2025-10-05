from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import asyncpg
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai
import json
import re
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import jwt


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PostgreSQL connection pool
db_pool: Optional[asyncpg.Pool] = None

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== MODELS ====================
class User(BaseModel):
    id: str
    email: str
    name: str
    picture: str = ""
    gmail_email: Optional[str] = None
    gmail_app_password: Optional[str] = None
    created_at: Optional[datetime] = None

class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: Optional[datetime] = None

class ConnectGmailRequest(BaseModel):
    email: str
    app_password: str

class DashboardStats(BaseModel):
    connected: bool
    email: Optional[str]
    total_emails: int
    last_sync: Optional[datetime]
    categories: dict
    recent_emails: List[dict]


# ==================== DATABASE STARTUP/SHUTDOWN ====================
@app.on_event("startup")
async def startup_db():
    global db_pool
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    
    db_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    logger.info("Database pool created")


@app.on_event("shutdown")
async def shutdown_db():
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


# ==================== AUTH HELPER ====================
async def get_current_user(request: Request) -> Optional[User]:
    """Get current user from session_token in cookies or Authorization header"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
    
    if not session_token:
        return None
    
    async with db_pool.acquire() as conn:
        # Check session
        session = await conn.fetchrow(
            "SELECT * FROM user_sessions WHERE session_token = $1",
            session_token
        )
        
        if not session:
            return None
        
        # Check expiry
        expires_at = session["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) >= expires_at:
            return None
        
        # Get user
        user_row = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            session["user_id"]
        )
        
        if not user_row:
            return None
        
        return User(
            id=str(user_row["id"]),
            email=user_row["email"],
            name=user_row["name"] or "",
            picture=user_row["picture"] or "",
            gmail_email=user_row["gmail_email"],
            gmail_app_password=user_row["gmail_app_password"],
            created_at=user_row["created_at"]
        )


async def require_auth(request: Request) -> User:
    """Require authentication"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ==================== REPLIT AUTH ====================
REPL_ID = os.environ.get('REPL_ID', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5000')
ISSUER_URL = "https://replit.com/oidc"

pkce_verifiers = {}

def generate_pkce():
    """Generate PKCE code verifier and challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

@api_router.get("/auth/login")
async def auth_login():
    """Redirect to Replit Auth"""
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce()
    
    pkce_verifiers[state] = code_verifier
    
    redirect_uri = f"{FRONTEND_URL}/api/auth/callback"
    
    params = {
        "client_id": REPL_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login consent"
    }
    
    auth_url = f"{ISSUER_URL}/auth?{urlencode(params)}"
    return {"auth_url": auth_url}


@api_router.get("/auth/callback")
async def auth_callback(code: str, state: str, response: Response):
    """Handle Replit Auth callback"""
    import httpx
    
    code_verifier = pkce_verifiers.pop(state, None)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid state")
    
    redirect_uri = f"{FRONTEND_URL}/api/auth/callback"
    
    async with httpx.AsyncClient() as http_client:
        token_response = await http_client.post(
            f"{ISSUER_URL}/token",
            data={
                "code": code,
                "client_id": REPL_ID,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        token_data = token_response.json()
        id_token = token_data.get("id_token")
        
        user_data = jwt.decode(id_token, options={"verify_signature": False})
    
    user_id = user_data["sub"]
    
    async with db_pool.acquire() as conn:
        existing_user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
        
        user_email = user_data.get("email", "")
        user_name = user_data.get("first_name", "") or user_email.split("@")[0]
        user_picture = user_data.get("profile_image_url", "")
        
        if not existing_user:
            await conn.execute(
                """
                INSERT INTO users (id, email, name, picture)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, user_email, user_name, user_picture
            )
        else:
            await conn.execute(
                """
                UPDATE users
                SET email = $2, name = $3, picture = $4
                WHERE id = $1
                """,
                user_id, user_email, user_name, user_picture
            )
        
        # Create session
        session_token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await conn.execute(
            """
            INSERT INTO user_sessions (user_id, session_token, expires_at)
            VALUES ($1, $2, $3)
            """,
            user_id, session_token, expires_at
        )
    
    response = RedirectResponse(url=FRONTEND_URL)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    
    return response


@api_router.get("/auth/me")
async def get_me(user: User = Depends(require_auth)):
    """Get current user info"""
    return user


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM user_sessions WHERE session_token = $1",
                session_token
            )
    
    response.delete_cookie(key="session_token", path="/")
    return {"success": True}


# ==================== GMAIL IMAP ====================
def connect_imap(email_addr: str, app_password: str):
    """Connect to Gmail via IMAP"""
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(email_addr, app_password)
        return imap
    except Exception as e:
        logger.error(f"IMAP connection error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to connect to Gmail: {str(e)}")


def decode_email_subject(subject):
    """Decode email subject"""
    if subject:
        decoded = decode_header(subject)
        subject_parts = []
        for content, encoding in decoded:
            if isinstance(content, bytes):
                subject_parts.append(content.decode(encoding or 'utf-8', errors='ignore'))
            else:
                subject_parts.append(content)
        return ''.join(subject_parts)
    return ""


def get_email_body(msg):
    """Extract email body"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    return body[:500]


def categorize_with_gemini(subject: str, sender: str, body: str) -> str:
    """Categorize email using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""Categorize this email into ONE of these categories: Primary, Social, Promotions, Updates, or Spam.

Email Details:
From: {sender}
Subject: {subject}
Body Preview: {body}

Rules:
- Primary: Personal emails, important messages
- Social: Social networks, forums, community
- Promotions: Offers, marketing, advertisements
- Updates: Notifications, receipts, automated messages
- Spam: Unwanted or suspicious emails

Respond with ONLY the category name (one word)."""

        response = model.generate_content(prompt)
        category = response.text.strip()
        
        # Validate category
        valid_categories = ["Primary", "Social", "Promotions", "Updates", "Spam"]
        for cat in valid_categories:
            if cat.lower() in category.lower():
                return cat
        
        return "Primary"
        
    except Exception as e:
        logger.error(f"Gemini categorization error: {str(e)}")
        return "Primary"


@api_router.post("/gmail/connect")
async def connect_gmail(request: ConnectGmailRequest, user: User = Depends(require_auth)):
    """Connect Gmail account via IMAP"""
    # Test connection
    imap = connect_imap(request.email, request.app_password)
    imap.logout()
    
    # Store credentials in user record
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET gmail_email = $2, gmail_app_password = $3
            WHERE id = $1
            """,
            user.id, request.email, request.app_password
        )
    
    return {"success": True, "message": "Gmail connected successfully"}


@api_router.post("/gmail/sync")
async def sync_emails(user: User = Depends(require_auth)):
    """Fetch and categorize emails from Gmail"""
    if not user.gmail_email or not user.gmail_app_password:
        raise HTTPException(status_code=404, detail="Gmail not connected")
    
    try:
        # Connect to Gmail
        imap = connect_imap(user.gmail_email, user.gmail_app_password)
        imap.select("INBOX")
        
        # Search for recent emails (last 50)
        _, message_numbers = imap.search(None, "ALL")
        email_ids = message_numbers[0].split()
        
        # Get last 50 emails
        email_ids = email_ids[-50:]
        
        categorized_count = 0
        
        async with db_pool.acquire() as conn:
            for email_id in email_ids:
                try:
                    email_id_str = email_id.decode()
                    
                    # Check if already categorized
                    existing = await conn.fetchrow(
                        """
                        SELECT id FROM emails 
                        WHERE user_id = $1 AND subject = $2
                        LIMIT 1
                        """,
                        uuid.UUID(user.id), email_id_str
                    )
                    
                    if existing:
                        continue
                    
                    # Fetch email
                    _, msg_data = imap.fetch(email_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)
                    
                    # Extract details
                    subject = decode_email_subject(msg.get("Subject", ""))
                    sender = msg.get("From", "")
                    date_str = msg.get("Date", "")
                    body = get_email_body(msg)
                    
                    # Parse date
                    try:
                        from email.utils import parsedate_to_datetime
                        email_date = parsedate_to_datetime(date_str)
                    except:
                        email_date = datetime.now(timezone.utc)
                    
                    # Categorize with Gemini
                    category = categorize_with_gemini(subject, sender, body)
                    
                    # Save to database
                    await conn.execute(
                        """
                        INSERT INTO emails (user_id, subject, sender, date, body, category, confidence)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        uuid.UUID(user.id), subject, sender, email_date, body[:200], category, 0.9
                    )
                    
                    categorized_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {str(e)}")
                    continue
        
        imap.logout()
        
        return {"success": True, "categorized": categorized_count}
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: User = Depends(require_auth)):
    """Get dashboard statistics"""
    
    if not user.gmail_email:
        return DashboardStats(
            connected=False,
            email=None,
            total_emails=0,
            last_sync=None,
            categories={},
            recent_emails=[]
        )
    
    async with db_pool.acquire() as conn:
        # Get all emails for this user
        all_emails = await conn.fetch(
            "SELECT * FROM emails WHERE user_id = $1",
            uuid.UUID(user.id)
        )
        
        # Calculate category counts
        categories = {"Primary": 0, "Social": 0, "Promotions": 0, "Updates": 0, "Spam": 0}
        for email_row in all_emails:
            cat = email_row["category"] or "Primary"
            if cat in categories:
                categories[cat] += 1
        
        # Get recent emails (last 10)
        recent_emails = await conn.fetch(
            """
            SELECT * FROM emails 
            WHERE user_id = $1 
            ORDER BY date DESC 
            LIMIT 10
            """,
            uuid.UUID(user.id)
        )
        
        recent_list = [
            {
                "subject": e["subject"],
                "sender": e["sender"],
                "category": e["category"],
                "date": e["date"].isoformat() if e.get("date") else None,
                "snippet": e.get("body", "")[:200]
            }
            for e in recent_emails
        ]
        
        # Get last sync time (most recent email created_at)
        last_sync_row = await conn.fetchrow(
            """
            SELECT MAX(created_at) as last_sync 
            FROM emails 
            WHERE user_id = $1
            """,
            uuid.UUID(user.id)
        )
        
        last_sync = last_sync_row["last_sync"] if last_sync_row else None
    
    return DashboardStats(
        connected=True,
        email=user.gmail_email,
        total_emails=len(all_emails),
        last_sync=last_sync,
        categories=categories,
        recent_emails=recent_list
    )


@api_router.delete("/gmail/disconnect")
async def disconnect_gmail(user: User = Depends(require_auth)):
    """Disconnect Gmail account"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET gmail_email = NULL, gmail_app_password = NULL
            WHERE id = $1
            """,
            user.id
        )
    
    return {"success": True}


# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
        "https://c363f9ef-5f69-4abe-887f-60d877a4e2ce-00-25ix68esofxzf.riker.replit.dev",
        "https://*.replit.dev",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
