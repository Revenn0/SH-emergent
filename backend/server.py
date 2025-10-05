from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import asyncpg
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai


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

# Fixed user ID for all operations (no authentication)
DEFAULT_USER_ID = "default"


# ==================== MODELS ====================
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
    
    # Ensure default user exists
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email, name, picture)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO NOTHING
            """,
            DEFAULT_USER_ID, "user@localhost", "User", ""
        )


@app.on_event("shutdown")
async def shutdown_db():
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


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
async def connect_gmail(request: ConnectGmailRequest):
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
            DEFAULT_USER_ID, request.email, request.app_password
        )
    
    return {"success": True, "message": "Gmail connected successfully"}


@api_router.post("/gmail/sync")
async def sync_emails():
    """Fetch and categorize emails from Gmail"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            DEFAULT_USER_ID
        )
        
        if not user or not user['gmail_email'] or not user['gmail_app_password']:
            raise HTTPException(status_code=404, detail="Gmail not connected")
    
    try:
        # Connect to Gmail
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
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
                        WHERE user_id = $1 AND email_id = $2
                        LIMIT 1
                        """,
                        DEFAULT_USER_ID, email_id_str
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
                        INSERT INTO emails (user_id, email_id, subject, sender, date, body, category, confidence)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        DEFAULT_USER_ID, email_id_str, subject, sender, email_date, body[:200], category, 0.9
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
async def get_dashboard_stats():
    """Get dashboard statistics"""
    
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            DEFAULT_USER_ID
        )
        
        if not user or not user['gmail_email']:
            return DashboardStats(
                connected=False,
                email=None,
                total_emails=0,
                last_sync=None,
                categories={},
                recent_emails=[]
            )
        
        # Get all emails for this user
        all_emails = await conn.fetch(
            "SELECT * FROM emails WHERE user_id = $1",
            DEFAULT_USER_ID
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
            DEFAULT_USER_ID
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
            DEFAULT_USER_ID
        )
        
        last_sync = last_sync_row["last_sync"] if last_sync_row else None
    
    return DashboardStats(
        connected=True,
        email=user['gmail_email'],
        total_emails=len(all_emails),
        last_sync=last_sync,
        categories=categories,
        recent_emails=recent_list
    )


@api_router.delete("/gmail/disconnect")
async def disconnect_gmail():
    """Disconnect Gmail account"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET gmail_email = NULL, gmail_app_password = NULL
            WHERE id = $1
            """,
            DEFAULT_USER_ID
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
