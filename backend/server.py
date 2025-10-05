from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GmailConnection(BaseModel):
    user_id: str
    email: str
    app_password: str
    status: str = "connected"
    last_sync: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategorizedEmail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    email_id: str
    subject: str
    sender: str
    date: datetime
    category: str
    snippet: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    
    # Check session
    session = await db.user_sessions.find_one({"session_token": session_token})
    if not session:
        return None
    
    # Check expiry
    expires_at = session["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if datetime.now(timezone.utc) >= expires_at:
        return None
    
    # Get user
    user_doc = await db.users.find_one({"id": session["user_id"]})
    if not user_doc:
        return None
    
    return User(**user_doc)


async def require_auth(request: Request) -> User:
    """Require authentication"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ==================== GOOGLE OAUTH ====================
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5000')

@api_router.get("/auth/login")
async def auth_login():
    """Redirect to Google OAuth"""
    redirect_uri = f"{FRONTEND_URL}/api/auth/google/callback"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline"
    )
    return {"auth_url": auth_url}


@api_router.get("/auth/google/callback")
async def google_callback(code: str, response: Response):
    """Handle Google OAuth callback"""
    import httpx
    
    redirect_uri = f"{FRONTEND_URL}/api/auth/google/callback"
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_info_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_info_response.json()
    
    existing_user = await db.users.find_one({"email": user_data["email"]})
    
    if not existing_user:
        user = User(
            email=user_data["email"],
            name=user_data.get("name", ""),
            picture=user_data.get("picture", "")
        )
        await db.users.insert_one(user.dict())
        user_id = user.id
    else:
        user_id = existing_user["id"]
    
    session_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    await db.user_sessions.insert_one(session.dict())
    
    response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
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
        await db.user_sessions.delete_one({"session_token": session_token})
    
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
    return body[:500]  # First 500 chars


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
        
        return "Primary"  # Default
        
    except Exception as e:
        logger.error(f"Gemini categorization error: {str(e)}")
        return "Primary"  # Default on error


@api_router.post("/gmail/connect")
async def connect_gmail(request: ConnectGmailRequest, user: User = Depends(require_auth)):
    """Connect Gmail account via IMAP"""
    # Test connection
    imap = connect_imap(request.email, request.app_password)
    imap.logout()
    
    # Store credentials (in production, encrypt this!)
    connection = GmailConnection(
        user_id=user.id,
        email=request.email,
        app_password=request.app_password
    )
    
    # Remove old connection
    await db.gmail_connections.delete_many({"user_id": user.id})
    
    # Save new connection
    await db.gmail_connections.insert_one(connection.dict())
    
    return {"success": True, "message": "Gmail connected successfully"}


@api_router.post("/gmail/sync")
async def sync_emails(user: User = Depends(require_auth)):
    """Fetch and categorize emails from Gmail"""
    # Get connection
    connection = await db.gmail_connections.find_one({"user_id": user.id})
    if not connection:
        raise HTTPException(status_code=404, detail="Gmail not connected")
    
    try:
        # Connect to Gmail
        imap = connect_imap(connection["email"], connection["app_password"])
        imap.select("INBOX")
        
        # Search for recent emails (last 50)
        _, message_numbers = imap.search(None, "ALL")
        email_ids = message_numbers[0].split()
        
        # Get last 50 emails
        email_ids = email_ids[-50:]
        
        categorized_count = 0
        
        for email_id in email_ids:
            try:
                # Check if already categorized
                existing = await db.categorized_emails.find_one({
                    "user_id": user.id,
                    "email_id": email_id.decode()
                })
                
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
                categorized_email = CategorizedEmail(
                    user_id=user.id,
                    email_id=email_id.decode(),
                    subject=subject,
                    sender=sender,
                    date=email_date,
                    category=category,
                    snippet=body[:200]
                )
                
                await db.categorized_emails.insert_one(categorized_email.dict())
                categorized_count += 1
                
            except Exception as e:
                logger.error(f"Error processing email {email_id}: {str(e)}")
                continue
        
        # Update last sync
        await db.gmail_connections.update_one(
            {"user_id": user.id},
            {"$set": {"last_sync": datetime.now(timezone.utc)}}
        )
        
        imap.logout()
        
        return {"success": True, "categorized": categorized_count}
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: User = Depends(require_auth)):
    """Get dashboard statistics"""
    # Check Gmail connection
    connection = await db.gmail_connections.find_one({"user_id": user.id})
    
    if not connection:
        return DashboardStats(
            connected=False,
            email=None,
            total_emails=0,
            last_sync=None,
            categories={},
            recent_emails=[]
        )
    
    # Get all categorized emails
    all_emails = await db.categorized_emails.find({"user_id": user.id}).to_list(1000)
    
    # Calculate category counts
    categories = {"Primary": 0, "Social": 0, "Promotions": 0, "Updates": 0, "Spam": 0}
    for email_doc in all_emails:
        cat = email_doc.get("category", "Primary")
        if cat in categories:
            categories[cat] += 1
    
    # Get recent emails (last 10)
    recent_emails = await db.categorized_emails.find(
        {"user_id": user.id}
    ).sort("date", -1).limit(10).to_list(10)
    
    recent_list = [
        {
            "subject": e["subject"],
            "sender": e["sender"],
            "category": e["category"],
            "date": e["date"].isoformat() if e.get("date") else None,
            "snippet": e.get("snippet", "")
        }
        for e in recent_emails
    ]
    
    return DashboardStats(
        connected=True,
        email=connection["email"],
        total_emails=len(all_emails),
        last_sync=connection.get("last_sync"),
        categories=categories,
        recent_emails=recent_list
    )


@api_router.delete("/gmail/disconnect")
async def disconnect_gmail(user: User = Depends(require_auth)):
    """Disconnect Gmail account"""
    await db.gmail_connections.delete_many({"user_id": user.id})
    return {"success": True}


# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "https://mail-categorizer-1.preview.emergentagent.com",
        "http://localhost:3000",
        "http://localhost:5000",
        "https://c363f9ef-5f69-4abe-887f-60d877a4e2ce-00-25ix68esofxzf.riker.replit.dev",
        "https://*.replit.dev",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()