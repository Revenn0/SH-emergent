from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, Header, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response
import asyncpg
import os
import logging
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai
import re
import asyncio
from functools import lru_cache
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import hashlib


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)  # Force override Replit's DATABASE_URL

db_pool: asyncpg.Pool = None  # type: ignore

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
IS_PRODUCTION = os.getenv("APP_ENV") == "production"
IS_REPLIT = os.getenv("REPLIT_DEV_DOMAIN") is not None
IS_HTTPS = IS_PRODUCTION or IS_REPLIT

security = HTTPBearer()

def set_auth_cookie(response: Response, key: str, value: str, max_age: int):
    """Set authentication cookie with appropriate settings for dev/prod/replit"""
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=IS_HTTPS,
        samesite="none" if IS_HTTPS else "lax",
        max_age=max_age
    )

ALERT_CATEGORIES = [
    "Crash Detected",
    "Heavy Impact",
    "Light Sensor",
    "Out Of Country",
    "No Communication",
    "Over-turn",
    "Tamper Alert",
    "Low Battery",
    "Motion",
    "New Positions",
    "High Risk Area",
    "Custom GeoFence",
    "Rotation Stop",
    "Temperature",
    "Pressure",
    "Humidity",
    "Other"
]


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ConnectGmailRequest(BaseModel):
    email: str
    app_password: str

class SyncRequest(BaseModel):
    limit: int = 100

class AcknowledgeRequest(BaseModel):
    acknowledged_by: str

class UpdateStatusRequest(BaseModel):
    status: str

class AddNoteRequest(BaseModel):
    notes: str

class AssignRequest(BaseModel):
    assigned_to: str

class AddBikeNoteRequest(BaseModel):
    note: str

async def sync_emails_background(user: dict, limit: int = 100) -> int:
    """Simple email sync for background task - returns count of new emails"""
    try:
        if not user.get('gmail_email') or not user.get('gmail_app_password'):
            return 0
        
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        async with db_pool.acquire() as conn:
            checkpoint = await conn.fetchrow(
                "SELECT * FROM sync_checkpoints WHERE user_id = $1",
                user['id']
            )
        
        _, message_numbers = imap.search(None, f'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        
        if checkpoint and checkpoint['last_email_id']:
            try:
                last_idx = email_ids.index(checkpoint['last_email_id'].encode())
                email_ids = email_ids[last_idx + 1:]
            except ValueError:
                email_ids = email_ids[-limit:]
        else:
            email_ids = email_ids[-limit:]
        
        async with db_pool.acquire() as conn:
            existing_ids = await conn.fetch(
                "SELECT email_id FROM tracker_alerts WHERE user_id = $1",
                user['id']
            )
            existing_set = {row['email_id'] for row in existing_ids}
            
            email_data_list = []
            for email_id in email_ids:
                email_id_str = email_id.decode()
                
                if email_id_str in existing_set:
                    continue
                
                try:
                    _, msg_data = imap.fetch(email_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)
                    body = get_email_body(msg)
                    email_data_list.append((email_id_str, body))
                except Exception as e:
                    logger.error(f"Error fetching email {email_id_str}: {str(e)}")
            
            imap.logout()
            
            if not email_data_list:
                return 0
            
            batch_size = 10
            total_processed = 0
            
            for i in range(0, len(email_data_list), batch_size):
                batch = email_data_list[i:i + batch_size]
                processed = await process_email_batch(batch, user['id'])
                total_processed += processed
            
            if email_data_list:
                last_email_id = email_data_list[-1][0]
                await conn.execute(
                    """
                    INSERT INTO sync_checkpoints (user_id, last_email_id, last_sync_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE
                    SET last_email_id = $2, last_sync_at = CURRENT_TIMESTAMP
                    """,
                    user['id'], last_email_id
                )
            
            return total_processed
    
    except Exception as e:
        logger.error(f"Email sync error for {user.get('username', 'unknown')}: {str(e)}")
        return 0


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def hash_token(token: str) -> str:
    """Create SHA256 hash of token"""
    return hashlib.sha256(token.encode()).hexdigest()

async def store_refresh_token(user_id: str, token: str):
    """Store refresh token hash in database"""
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES ($1, $2, $3)
            """,
            user_id, token_hash, expires_at
        )

async def validate_refresh_token(token: str) -> Optional[str]:
    """Validate refresh token against database and return user_id if valid"""
    token_hash = hash_token(token)
    
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            SELECT user_id, expires_at FROM refresh_tokens 
            WHERE token_hash = $1 AND expires_at > CURRENT_TIMESTAMP
            """,
            token_hash
        )
        
        if result:
            return result['user_id']
        return None

async def get_current_user(request: Request):
    """Dependency to get current authenticated user from cookie"""
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = verify_token(token, "access")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, full_name, role, created_at FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return dict(user)


def parse_tracker_email(body: str) -> dict:
    """Parse tracker email to extract important information"""
    data = {
        "alert_type": "",
        "time": "",
        "location": "",
        "latitude": "",
        "longitude": "",
        "device_serial": "",
        "tracker_name": "",
        "account_name": ""
    }
    
    try:
        alert_type_match = re.search(r'Alert type:\s*(.+)', body)
        if alert_type_match:
            data["alert_type"] = alert_type_match.group(1).strip()
        
        time_match = re.search(r'Time:\s*(.+?)(?:\(|$)', body)
        if time_match:
            data["time"] = time_match.group(1).strip()
        
        location_match = re.search(r'Location:\s*(.+)', body)
        if location_match:
            data["location"] = location_match.group(1).strip()
        
        coords_match = re.search(r'Latitude, Longitude:\s*([-\d.]+),\s*([-\d.]+)', body)
        if coords_match:
            data["latitude"] = coords_match.group(1).strip()
            data["longitude"] = coords_match.group(2).strip()
        
        device_match = re.search(r'Device Serial Number:\s*(.+)', body)
        if device_match:
            data["device_serial"] = device_match.group(1).strip()
        
        tracker_match = re.search(r'Tracker Name:\s*(.+)', body)
        if tracker_match:
            data["tracker_name"] = tracker_match.group(1).strip()
        
        account_match = re.search(r'Account name:\s*(.+)', body)
        if account_match:
            data["account_name"] = account_match.group(1).strip()
    except Exception as e:
        logger.error(f"Error parsing email: {str(e)}")
    
    return data


def categorize_alert(alert_type: str) -> str:
    """Categorize alert based on type"""
    alert_lower = alert_type.lower()
    
    # Heavy Impact alone is NOT crash detect - needs Over-turn too (checked later)
    if "heavy impact" in alert_lower:
        return "Heavy Impact"
    elif "light sensor" in alert_lower:
        return "Light Sensor"
    elif "out of country" in alert_lower:
        return "Out Of Country"
    elif "no communication" in alert_lower:
        return "No Communication"
    elif "over-turn" in alert_lower or "overturn" in alert_lower:
        return "Over-turn"
    elif "tamper" in alert_lower:
        return "Tamper Alert"
    elif "low battery" in alert_lower:
        return "Low Battery"
    elif "motion" in alert_lower:
        return "Motion"
    elif "new position" in alert_lower:
        return "New Positions"
    elif "high risk" in alert_lower:
        return "High Risk Area"
    elif "geofence" in alert_lower:
        return "Custom GeoFence"
    elif "rotation" in alert_lower:
        return "Rotation Stop"
    elif "temperature" in alert_lower:
        return "Temperature"
    elif "pressure" in alert_lower:
        return "Pressure"
    elif "humidity" in alert_lower:
        return "Humidity"
    else:
        return "Other"


background_task = None

@app.on_event("startup")
async def startup_db():
    global db_pool, background_task
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    
    database_url = database_url.strip("'\"")
    
    # Disable statement caching to avoid InvalidCachedStatementError with Neon
    db_pool = await asyncpg.create_pool(
        database_url, 
        min_size=2, 
        max_size=10,
        statement_cache_size=0  # Disable statement caching
    )
    logger.info("Database pool created")
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                username VARCHAR UNIQUE NOT NULL,
                email VARCHAR UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name VARCHAR,
                gmail_email VARCHAR,
                gmail_app_password VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracker_alerts (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                email_id VARCHAR NOT NULL,
                alert_type VARCHAR,
                alert_time VARCHAR,
                location VARCHAR,
                latitude VARCHAR,
                longitude VARCHAR,
                device_serial VARCHAR,
                tracker_name VARCHAR,
                account_name VARCHAR,
                raw_body TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR DEFAULT 'New',
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_at TIMESTAMP,
                acknowledged_by VARCHAR,
                notes TEXT,
                assigned_to VARCHAR,
                favorite BOOLEAN DEFAULT FALSE,
                UNIQUE(user_id, email_id)
            )
            """
        )
        
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_checkpoints (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL UNIQUE,
                last_email_id VARCHAR,
                last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bikes (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                tracker_name VARCHAR NOT NULL,
                device_serial VARCHAR,
                latest_alert_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, tracker_name)
            )
            """
        )
        
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bikes_user_id ON bikes(user_id)
            """
        )
        
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bikes_tracker_name ON bikes(tracker_name)
            """
        )
        
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bike_notes (
                id SERIAL PRIMARY KEY,
                bike_id INTEGER NOT NULL,
                user_id VARCHAR NOT NULL,
                note TEXT NOT NULL,
                author VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bike_id) REFERENCES bikes(id) ON DELETE CASCADE
            )
            """
        )
        
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bike_notes_bike_id ON bike_notes(bike_id)
            """
        )
        
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_sync_runs (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP NOT NULL,
                source VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                emails_read INTEGER DEFAULT 0,
                emails_new INTEGER DEFAULT 0,
                error_summary TEXT,
                log_json TEXT
            )
            """
        )
        
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                token_hash VARCHAR NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        
        # Add sync configuration and role columns if they don't exist
        try:
            await conn.execute(
                """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS sync_interval_minutes INTEGER DEFAULT 10,
                ADD COLUMN IF NOT EXISTS email_limit_per_sync INTEGER DEFAULT 100,
                ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'admin'
                """
            )
        except Exception as e:
            logger.warning(f"Error adding config columns (may already exist): {str(e)}")
        
        admin_exists = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE username = 'admin'"
        )
        
        if admin_exists == 0:
            import uuid
            admin_id = str(uuid.uuid4())
            admin_password_hash = pwd_context.hash("dimension")
            await conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, full_name)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (username) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash
                """,
                admin_id, "admin", "admin@tracker.com", admin_password_hash, "Administrator"
            )
            logger.info("Default admin user created (username: admin, password: dimension)")
        else:
            logger.info("Admin user already exists")
    
    background_task = asyncio.create_task(auto_sync_background())
    logger.info("Background sync task started (1 hour interval, 30 email limit)")

async def auto_sync_background():
    """Background task to automatically sync alerts every 1 hour for all users with 30 email limit"""
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            
            async with db_pool.acquire() as conn:
                users = await conn.fetch(
                    "SELECT * FROM users WHERE gmail_email IS NOT NULL AND gmail_app_password IS NOT NULL"
                )
                
                for user in users:
                    try:
                        new_count = await sync_emails_background(dict(user), limit=30)
                        logger.info(f"Background sync completed for {user['username']}: {new_count} new emails processed")
                    except Exception as e:
                        logger.error(f"Background sync error for {user['username']}: {str(e)}")
                    
        except asyncio.CancelledError:
            logger.info("Background sync task cancelled")
            break
        except Exception as e:
            logger.error(f"Background sync error: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db():
    global db_pool, background_task
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        logger.info("Background sync task stopped")
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


@api_router.post("/auth/register")
async def register(request: RegisterRequest, response: Response):
    """Register a new user"""
    logger.info(f"Registration attempt: username={request.username}, email={request.email}")
    
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1 OR email = $2",
            request.username, request.email
        )
        
        if existing:
            logger.warning(f"Registration failed: Username or email already exists - {request.username}/{request.email}")
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        import uuid
        user_id = str(uuid.uuid4())
        password_hash = pwd_context.hash(request.password)
        
        await conn.execute(
            """
            INSERT INTO users (id, username, email, password_hash, full_name)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id, request.username, request.email, password_hash, request.full_name
        )
        
        access_token = create_access_token({"sub": user_id})
        refresh_token = create_refresh_token({"sub": user_id})
        
        await store_refresh_token(user_id, refresh_token)
        
        set_auth_cookie(response, "access_token", access_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        set_auth_cookie(response, "refresh_token", refresh_token, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
        
        logger.info(f"New user registered: {request.username}")
        
        return {
            "user": {
                "id": user_id,
                "username": request.username,
                "email": request.email,
                "full_name": request.full_name
            }
        }


@api_router.post("/auth/login")
async def login(request: LoginRequest, response: Response):
    """Login with JWT authentication using HttpOnly cookies"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, password_hash, full_name, role FROM users WHERE username = $1",
            request.username
        )
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {request.username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not pwd_context.verify(request.password, user['password_hash']):
            logger.warning(f"Invalid password for user: {request.username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token({"sub": user['id']})
        refresh_token = create_refresh_token({"sub": user['id']})
        
        await store_refresh_token(user['id'], refresh_token)
        
        set_auth_cookie(response, "access_token", access_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        set_auth_cookie(response, "refresh_token", refresh_token, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
        
        logger.info(f"User logged in: {request.username}")
        
        user_dict = dict(user)
        return {
            "user": {
                "id": user_dict['id'],
                "username": user_dict['username'],
                "email": user_dict['email'],
                "full_name": user_dict['full_name'],
                "role": user_dict.get('role', 'admin')
            }
        }


@api_router.post("/auth/refresh")
async def refresh_token_endpoint(req: Request, response: Response):
    """Refresh access token using refresh token from cookie"""
    refresh_token = req.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    
    user_id = await validate_refresh_token(refresh_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, full_name, role FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        await conn.execute(
            "DELETE FROM refresh_tokens WHERE token_hash = $1",
            hash_token(refresh_token)
        )
    
    access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})
    
    await store_refresh_token(user_id, new_refresh_token)
    
    set_auth_cookie(response, "access_token", access_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    set_auth_cookie(response, "refresh_token", new_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    
    user_dict = dict(user)
    return {
        "user": {
            "id": user_dict['id'],
            "username": user_dict['username'],
            "email": user_dict['email'],
            "full_name": user_dict['full_name'],
            "role": user_dict.get('role', 'admin')
        }
    }


@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user"""
    return current_user


@api_router.post("/auth/logout")
async def logout(req: Request, response: Response):
    """Logout user by clearing cookies and removing refresh token from DB"""
    refresh_token = req.cookies.get("refresh_token")
    
    if refresh_token:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM refresh_tokens WHERE token_hash = $1",
                hash_token(refresh_token)
            )
    
    set_auth_cookie(response, "access_token", "", 0)
    set_auth_cookie(response, "refresh_token", "", 0)
    
    return {"success": True, "message": "Logged out successfully"}


async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user is admin"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@api_router.post("/users/create")
async def create_user(request: dict, admin_user: dict = Depends(get_admin_user)):
    """Create a new user (admin only)"""
    username = request.get('username')
    email = request.get('email')
    password = request.get('password')
    role = request.get('role', 'viewer')  # Default to viewer
    
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="Username, email, and password are required")
    
    if role not in ['admin', 'viewer']:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'viewer'")
    
    async with db_pool.acquire() as conn:
        # Check if username or email already exists
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE username = $1 OR email = $2",
            username, email
        )
        
        if existing > 0:
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        import uuid
        user_id = str(uuid.uuid4())
        password_hash = pwd_context.hash(password)
        
        await conn.execute(
            """
            INSERT INTO users (id, username, email, password_hash, role)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id, username, email, password_hash, role
        )
    
    return {"success": True, "message": f"User '{username}' created successfully with role '{role}'"}


@api_router.get("/users/list")
async def list_users(admin_user: dict = Depends(get_admin_user)):
    """List all users (admin only)"""
    async with db_pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC"
        )
        
        return {"users": [dict(u) for u in users]}


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
    return body


@api_router.post("/gmail/connect")
async def connect_gmail(request: ConnectGmailRequest, current_user: dict = Depends(get_current_user)):
    """Connect Gmail account via IMAP"""
    imap = connect_imap(request.email, request.app_password)
    imap.logout()
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET gmail_email = $2, gmail_app_password = $3
            WHERE id = $1
            """,
            current_user['id'], request.email, request.app_password
        )
    
    return {"success": True, "message": "Gmail connected successfully"}


@api_router.delete("/gmail/disconnect")
async def disconnect_gmail(current_user: dict = Depends(get_current_user)):
    """Disconnect Gmail account"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET gmail_email = NULL, gmail_app_password = NULL
            WHERE id = $1
            """,
            current_user['id']
        )
    
    return {"success": True}


@api_router.post("/sync/manual")
async def manual_sync(current_user: dict = Depends(get_current_user)):
    """Manually trigger email synchronization"""
    try:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                current_user['id']
            )
        
        if not user or not user.get('gmail_email') or not user.get('gmail_app_password'):
            raise HTTPException(status_code=400, detail="Gmail not configured")
        
        new_count = await sync_emails_background(dict(user), limit=100)
        
        return {
            "success": True, 
            "message": f"Sync completed: {new_count} new emails processed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@api_router.post("/sync/progressive")
async def sync_progressive(current_user: dict = Depends(get_current_user)):
    """Sync emails progressively - 10 at a time with progress tracking"""
    try:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                current_user['id']
            )
        
        if not user or not user.get('gmail_email') or not user.get('gmail_app_password'):
            raise HTTPException(status_code=400, detail="Gmail not configured")
        
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        _, message_numbers = imap.search(None, 'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        total_emails = len(email_ids)
        
        async with db_pool.acquire() as conn:
            existing_ids = await conn.fetch(
                "SELECT email_id FROM tracker_alerts WHERE user_id = $1",
                user['id']
            )
            existing_set = {row['email_id'] for row in existing_ids}
            
            # Process only first 10 new emails
            email_data_list = []
            processed_count = 0
            
            for email_id in email_ids:
                email_id_str = email_id.decode()
                
                if email_id_str in existing_set:
                    processed_count += 1
                    continue
                
                if len(email_data_list) >= 10:
                    break
                
                try:
                    _, msg_data = imap.fetch(email_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)
                    body = get_email_body(msg)
                    email_data_list.append((email_id_str, body))
                except Exception as e:
                    logger.error(f"Error fetching email {email_id_str}: {str(e)}")
            
            imap.logout()
            
            new_processed = 0
            if email_data_list:
                new_processed = await process_email_batch(email_data_list, user['id'])
                processed_count += new_processed
            
            remaining = total_emails - processed_count
            
            return {
                "success": True,
                "total": total_emails,
                "processed": processed_count,
                "remaining": remaining,
                "batch_size": len(email_data_list),
                "new_alerts": new_processed,
                "completed": remaining == 0
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Progressive sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progressive sync failed: {str(e)}")


@api_router.post("/sync/today")
async def sync_today_emails(current_user: dict = Depends(get_current_user)):
    """Sync ALL emails from alerts sender (excluding already read ones)"""
    try:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                current_user['id']
            )
        
        if not user or not user.get('gmail_email') or not user.get('gmail_app_password'):
            raise HTTPException(status_code=400, detail="Gmail not configured")
        
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        _, message_numbers = imap.search(None, 'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        
        async with db_pool.acquire() as conn:
            existing_ids = await conn.fetch(
                "SELECT email_id FROM tracker_alerts WHERE user_id = $1",
                user['id']
            )
            existing_set = {row['email_id'] for row in existing_ids}
            
            email_data_list = []
            for email_id in email_ids:
                email_id_str = email_id.decode()
                
                if email_id_str in existing_set:
                    continue
                
                try:
                    _, msg_data = imap.fetch(email_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)
                    body = get_email_body(msg)
                    email_data_list.append((email_id_str, body))
                except Exception as e:
                    logger.error(f"Error fetching email {email_id_str}: {str(e)}")
            
            imap.logout()
            
            if not email_data_list:
                return {
                    "success": True,
                    "message": f"No new emails from today ({len(email_ids)} already processed)"
                }
            
            batch_size = 10
            total_processed = 0
            
            for i in range(0, len(email_data_list), batch_size):
                batch = email_data_list[i:i + batch_size]
                processed = await process_email_batch(batch, user['id'])
                total_processed += processed
            
            if email_data_list and email_ids:
                await conn.execute(
                    """
                    INSERT INTO sync_checkpoints (user_id, last_email_id, last_sync_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET last_email_id = $2, last_sync_at = CURRENT_TIMESTAMP
                    """,
                    user['id'], email_ids[-1].decode()
                )
            
            return {
                "success": True,
                "message": f"Full sync completed: {total_processed} new emails processed (total found: {len(email_ids)})"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Today sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Today sync failed: {str(e)}")


async def process_email_batch(email_data_list: List[tuple], user_id: str):
    """Process a batch of emails in parallel with individual connections"""
    async def process_single_email(email_id_str, body):
        try:
            parsed = parse_tracker_email(body)
            category = categorize_alert(parsed["alert_type"])
            
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO tracker_alerts (
                        user_id, email_id, alert_type, alert_time, location, 
                        latitude, longitude, device_serial, tracker_name, 
                        account_name, raw_body
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (user_id, email_id) DO NOTHING
                    """,
                    user_id, email_id_str, category, 
                    parsed["time"], parsed["location"], 
                    parsed["latitude"], parsed["longitude"],
                    parsed["device_serial"], parsed["tracker_name"],
                    parsed["account_name"], body[:500]
                )
            return True
        except Exception as e:
            logger.error(f"Error processing email {email_id_str}: {str(e)}")
            return False
    
    tasks = [process_single_email(email_id, body) for email_id, body in email_data_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)


@api_router.get("/alerts/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    """Get all available alert categories"""
    async with db_pool.acquire() as conn:
        alerts = await conn.fetch(
            """
            SELECT alert_type, COUNT(*) as count 
            FROM tracker_alerts 
            WHERE user_id = $1 
            GROUP BY alert_type
            ORDER BY count DESC
            """,
            current_user['id']
        )
        
        category_stats = {
            cat: 0 for cat in ALERT_CATEGORIES
        }
        
        for alert in alerts:
            cat = alert["alert_type"] or "Other"
            if cat in category_stats:
                category_stats[cat] = alert["count"]
        
        return {
            "categories": ALERT_CATEGORIES,
            "stats": category_stats
        }


@api_router.get("/alerts/list")
async def list_alerts(
    category: Optional[str] = Query(None), 
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get tracker alerts with pagination and optional category filter"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            current_user['id']
        )
        
        offset = (page - 1) * limit
        where_clause = "WHERE user_id = $1 AND (acknowledged IS NULL OR acknowledged = FALSE)"
        params = [current_user['id']]
        
        if category and category != "All":
            where_clause += f" AND alert_type = ${len(params) + 1}"
            params.append(category)
        
        if start_date:
            from datetime import datetime
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            where_clause += f" AND created_at >= ${len(params) + 1}"
            params.append(start_datetime)
        
        if end_date:
            from datetime import datetime, timedelta
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            where_clause += f" AND created_at < ${len(params) + 1}"
            params.append(end_datetime)
        
        total_count = await conn.fetchval(
            f"SELECT COUNT(*) FROM tracker_alerts {where_clause}",
            *params
        )
        
        alerts = await conn.fetch(
            f"""
            SELECT * FROM tracker_alerts 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """,
            *params, limit, offset
        )
        
        category_stats = await conn.fetch(
            f"""
            SELECT alert_type, COUNT(*) as count 
            FROM tracker_alerts 
            {where_clause}
            GROUP BY alert_type
            """,
            *params
        )
        
        categories = {row["alert_type"] or "Other": row["count"] for row in category_stats}
        
        unread_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND (acknowledged IS NULL OR acknowledged = FALSE)
            """,
            *params
        ) or 0
        
        acknowledged_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND acknowledged = TRUE
            """,
            *params
        ) or 0
        
        over_turn_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND alert_type = 'Over-turn'
            """,
            *params
        ) or 0
        
        no_communication_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND alert_type LIKE '%No Communication%'
            """,
            *params
        ) or 0
        
        heavy_impact_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND alert_type LIKE '%Crash detect%'
            """,
            *params
        ) or 0
        
        device_alerts_data = await conn.fetch(
            f"""
            SELECT tracker_name, array_agg(DISTINCT alert_type) as alert_types
            FROM tracker_alerts 
            {where_clause}
            GROUP BY tracker_name
            """,
            *params
        )
        
        high_priority_count = 0
        heavy_impact_bikes_count = 0
        
        for row in device_alerts_data:
            alert_types = set(row["alert_types"] or [])
            has_light_sensor = "Light Sensor" in alert_types
            has_over_turn = "Over-turn" in alert_types
            has_heavy_impact = any("Crash detect" in str(t) for t in alert_types if t)
            has_no_comm = any("No Communication" in str(t) for t in alert_types if t)
            
            if has_light_sensor and has_over_turn:
                heavy_impact_bikes_count += 1
            elif has_over_turn or has_heavy_impact or has_no_comm:
                high_priority_count += 1
        
        alert_list = [
            {
                "id": a["id"],
                "alert_type": a["alert_type"],
                "alert_time": a["alert_time"],
                "location": a["location"],
                "latitude": a["latitude"],
                "longitude": a["longitude"],
                "device_serial": a["device_serial"],
                "tracker_name": a["tracker_name"],
                "account_name": a["account_name"],
                "status": a.get("status", "New"),
                "acknowledged": a.get("acknowledged", False),
                "acknowledged_at": str(a["acknowledged_at"]) if a.get("acknowledged_at") else None,
                "acknowledged_by": a.get("acknowledged_by"),
                "notes": a.get("notes"),
                "assigned_to": a.get("assigned_to"),
                "favorite": a.get("favorite", False)
            }
            for a in alerts
        ]
        
        total_pages = (total_count + limit - 1) // limit
        
        return {
            "alerts": alert_list,
            "stats": {
                "total": total_count,
                "unread": unread_count,
                "highPriority": high_priority_count,
                "heavyImpact": heavy_impact_bikes_count,
                "acknowledged": acknowledged_count,
                "overTurn": over_turn_count,
                "noCommunication": no_communication_count,
                "heavyImpactAlerts": heavy_impact_count,
                "categories": categories
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "connected": bool(user and user['gmail_email']),
            "email": user['gmail_email'] if user else None,
            "activeFilter": category or "All"
        }


@api_router.get("/alerts/export")
async def export_alerts_csv(
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Export alerts to CSV with optional category/date filters"""
    async with db_pool.acquire() as conn:
        where_clause = "WHERE user_id = $1"
        params = [current_user['id']]
        
        if category and category != "All":
            where_clause += f" AND alert_type = ${len(params) + 1}"
            params.append(category)
        
        if date_from:
            where_clause += f" AND created_at >= ${len(params) + 1}::timestamp"
            params.append(date_from)
        
        if date_to:
            where_clause += f" AND created_at <= ${len(params) + 1}::timestamp + interval '1 day'"
            params.append(date_to)
        
        alerts = await conn.fetch(
            f"""
            SELECT * FROM tracker_alerts 
            {where_clause}
            ORDER BY created_at DESC
            """,
            *params
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'ID', 'Alert Type', 'Alert Time', 'Location', 'Latitude', 'Longitude',
            'Device Serial', 'Tracker Name', 'Account Name', 'Status', 
            'Acknowledged', 'Notes', 'Created At'
        ])
        
        for alert in alerts:
            writer.writerow([
                alert['id'],
                alert['alert_type'],
                alert['alert_time'],
                alert['location'],
                alert['latitude'],
                alert['longitude'],
                alert['device_serial'],
                alert['tracker_name'],
                alert['account_name'],
                alert.get('status', 'New'),
                'Yes' if alert.get('acknowledged') else 'No',
                alert.get('notes', ''),
                alert['created_at']
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=alerts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )


@api_router.get("/alerts/stats-only")
async def get_stats_only(
    category: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get only statistics without alert list (for auto-refresh)"""
    async with db_pool.acquire() as conn:
        where_clause = "WHERE user_id = $1"
        params = [current_user['id']]
        
        if category and category != "All":
            where_clause += " AND alert_type = $2"
            params.append(category)
        
        total_count = await conn.fetchval(
            f"SELECT COUNT(*) FROM tracker_alerts {where_clause}",
            *params
        )
        
        category_stats = await conn.fetch(
            f"""
            SELECT alert_type, COUNT(*) as count 
            FROM tracker_alerts 
            {where_clause}
            GROUP BY alert_type
            """,
            *params
        )
        
        categories = {row["alert_type"] or "Other": row["count"] for row in category_stats}
        
        acknowledged_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND acknowledged = TRUE
            """,
            *params
        ) or 0
        
        over_turn_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND alert_type = 'Over-turn'
            """,
            *params
        ) or 0
        
        no_communication_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND alert_type LIKE '%No Communication%'
            """,
            *params
        ) or 0
        
        heavy_impact_count = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM tracker_alerts 
            {where_clause} AND alert_type LIKE '%Crash detect%'
            """,
            *params
        ) or 0
        
        device_alerts_data = await conn.fetch(
            f"""
            SELECT tracker_name, array_agg(DISTINCT alert_type) as alert_types
            FROM tracker_alerts 
            {where_clause}
            GROUP BY tracker_name
            """,
            *params
        )
        
        high_priority_count = 0
        heavy_impact_bikes_count = 0
        
        for row in device_alerts_data:
            alert_types = set(row["alert_types"] or [])
            has_light_sensor = "Light Sensor" in alert_types
            has_over_turn = "Over-turn" in alert_types
            has_heavy_impact = any("Crash detect" in str(t) for t in alert_types if t)
            has_no_comm = any("No Communication" in str(t) for t in alert_types if t)
            
            if has_light_sensor and has_over_turn:
                heavy_impact_bikes_count += 1
            elif has_over_turn or has_heavy_impact or has_no_comm:
                high_priority_count += 1
        
        return {
            "stats": {
                "total": total_count,
                "highPriority": high_priority_count,
                "heavyImpact": heavy_impact_bikes_count,
                "acknowledged": acknowledged_count,
                "overTurn": over_turn_count,
                "noCommunication": no_communication_count,
                "heavyImpactAlerts": heavy_impact_count,
                "categories": categories
            }
        }


@api_router.delete("/alerts/clear-all/history")
async def clear_all_alerts(current_user: dict = Depends(get_current_user)):
    """Clear all alerts and sync checkpoint (reset system)"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM tracker_alerts WHERE user_id = $1",
            current_user['id']
        )
        await conn.execute(
            "DELETE FROM sync_checkpoints WHERE user_id = $1",
            current_user['id']
        )
    
    return {"success": True, "message": "All alerts and sync history cleared"}


@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, current_user: dict = Depends(get_current_user)):
    """Delete an alert (only from app, not from Gmail)"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM tracker_alerts WHERE id = $1 AND user_id = $2",
            alert_id, current_user['id']
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, request: AcknowledgeRequest, current_user: dict = Depends(get_current_user)):
    """Acknowledge an alert"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET acknowledged = TRUE, 
                acknowledged_at = CURRENT_TIMESTAMP,
                acknowledged_by = $1
            WHERE id = $2 AND user_id = $3
            """,
            request.acknowledged_by, alert_id, current_user['id']
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/status")
async def update_alert_status(alert_id: int, request: UpdateStatusRequest, current_user: dict = Depends(get_current_user)):
    """Update alert status"""
    valid_statuses = ["New", "In Progress", "Resolved", "Closed"]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET status = $1
            WHERE id = $2 AND user_id = $3
            """,
            request.status, alert_id, current_user['id']
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/notes")
async def add_alert_note(alert_id: int, request: AddNoteRequest, current_user: dict = Depends(get_current_user)):
    """Add notes to an alert"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET notes = $1
            WHERE id = $2 AND user_id = $3
            """,
            request.notes, alert_id, current_user['id']
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/assign")
async def assign_alert(alert_id: int, request: AssignRequest, current_user: dict = Depends(get_current_user)):
    """Assign alert to a team member"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET assigned_to = $1
            WHERE id = $2 AND user_id = $3
            """,
            request.assigned_to, alert_id, current_user['id']
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/favorite")
async def toggle_favorite(alert_id: int, current_user: dict = Depends(get_current_user)):
    """Toggle favorite status"""
    async with db_pool.acquire() as conn:
        current = await conn.fetchrow(
            "SELECT favorite FROM tracker_alerts WHERE id = $1 AND user_id = $2",
            alert_id, current_user['id']
        )
        
        new_value = not current['favorite'] if current else True
        
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET favorite = $1
            WHERE id = $2 AND user_id = $3
            """,
            new_value, alert_id, current_user['id']
        )
    
    return {"success": True, "favorite": new_value}


@api_router.get("/bikes/list")
async def list_bikes(current_user: dict = Depends(get_current_user)):
    """Get all bikes for the current user with alert counts - OPTIMIZED & SECURE"""
    async with db_pool.acquire() as conn:
        # Single optimized query with proper user_id scoping
        bikes = await conn.fetch(
            """
            WITH bike_data AS (
                SELECT 
                    user_id,
                    tracker_name,
                    device_serial,
                    MAX(created_at) as latest_alert_at,
                    COUNT(*) as alert_count
                FROM tracker_alerts
                WHERE user_id = $1
                GROUP BY user_id, tracker_name, device_serial
            ),
            bike_ids AS (
                INSERT INTO bikes (user_id, tracker_name, device_serial, latest_alert_at)
                SELECT user_id, tracker_name, device_serial, latest_alert_at FROM bike_data
                ON CONFLICT (user_id, tracker_name) 
                DO UPDATE SET 
                    latest_alert_at = EXCLUDED.latest_alert_at,
                    device_serial = EXCLUDED.device_serial
                RETURNING id, user_id, tracker_name
            )
            SELECT 
                bi.id,
                bd.tracker_name,
                bd.device_serial,
                bd.latest_alert_at,
                bd.alert_count,
                COALESCE(COUNT(bn.id), 0) as notes_count
            FROM bike_data bd
            JOIN bike_ids bi ON bi.user_id = bd.user_id AND bi.tracker_name = bd.tracker_name
            LEFT JOIN bike_notes bn ON bn.bike_id = bi.id
            WHERE bd.user_id = $1
            GROUP BY bi.id, bd.tracker_name, bd.device_serial, bd.latest_alert_at, bd.alert_count
            ORDER BY bd.latest_alert_at DESC
            """,
            current_user['id']
        )
        
        result = []
        for bike in bikes:
            result.append({
                "id": bike['id'],
                "tracker_name": bike['tracker_name'],
                "device_serial": bike['device_serial'],
                "latest_alert_at": bike['latest_alert_at'].isoformat() if bike['latest_alert_at'] else None,
                "alert_count": bike['alert_count'],
                "notes_count": bike['notes_count']
            })
        
        return {"bikes": result}


@api_router.get("/bikes/{bike_id}/history")
async def get_bike_history(bike_id: int, current_user: dict = Depends(get_current_user)):
    """Get bike details with alerts and notes history"""
    async with db_pool.acquire() as conn:
        bike = await conn.fetchrow(
            """
            SELECT * FROM bikes
            WHERE id = $1 AND user_id = $2
            """,
            bike_id, current_user['id']
        )
        
        if not bike:
            raise HTTPException(status_code=404, detail="Bike not found")
        
        alerts = await conn.fetch(
            """
            SELECT * FROM tracker_alerts
            WHERE user_id = $1 AND tracker_name = $2
            ORDER BY created_at DESC
            LIMIT 50
            """,
            current_user['id'], bike['tracker_name']
        )
        
        notes = await conn.fetch(
            """
            SELECT * FROM bike_notes
            WHERE bike_id = $1
            ORDER BY created_at DESC
            """,
            bike_id
        )
        
        return {
            "bike": {
                "id": bike['id'],
                "tracker_name": bike['tracker_name'],
                "device_serial": bike['device_serial'],
                "latest_alert_at": bike['latest_alert_at'].isoformat() if bike['latest_alert_at'] else None
            },
            "alerts": [dict(alert) for alert in alerts],
            "notes": [dict(note) for note in notes]
        }


@api_router.post("/bikes/{bike_id}/notes")
async def add_bike_note(
    bike_id: int, 
    request: AddBikeNoteRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Add a note to a bike"""
    async with db_pool.acquire() as conn:
        bike = await conn.fetchrow(
            """
            SELECT * FROM bikes
            WHERE id = $1 AND user_id = $2
            """,
            bike_id, current_user['id']
        )
        
        if not bike:
            raise HTTPException(status_code=404, detail="Bike not found")
        
        note = await conn.fetchrow(
            """
            INSERT INTO bike_notes (bike_id, user_id, note, author, created_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            RETURNING *
            """,
            bike_id, current_user['id'], request.note, current_user.get('username', 'User')
        )
        
        return {"success": True, "note": dict(note)}


@api_router.delete("/bikes/notes/{note_id}")
async def delete_bike_note(note_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a bike note"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM bike_notes
            WHERE id = $1 AND user_id = $2
            """,
            note_id, current_user['id']
        )
    
    return {"success": True}


@api_router.get("/bikes/by-tracker/{tracker_name}")
async def get_bike_by_tracker_name(tracker_name: str, current_user: dict = Depends(get_current_user)):
    """Get bike ID by tracker name"""
    async with db_pool.acquire() as conn:
        bike = await conn.fetchrow(
            """
            SELECT id FROM bikes
            WHERE user_id = $1 AND tracker_name = $2
            """,
            current_user['id'], tracker_name
        )
        
        if not bike:
            bike_from_alert = await conn.fetchrow(
                """
                SELECT DISTINCT ON (tracker_name) 
                    tracker_name, device_serial,
                    MAX(created_at) as latest_alert_at
                FROM tracker_alerts
                WHERE user_id = $1 AND tracker_name = $2
                GROUP BY tracker_name, device_serial
                """,
                current_user['id'], tracker_name
            )
            
            if bike_from_alert:
                bike = await conn.fetchrow(
                    """
                    INSERT INTO bikes (user_id, tracker_name, device_serial, latest_alert_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, tracker_name) 
                    DO UPDATE SET 
                        latest_alert_at = EXCLUDED.latest_alert_at,
                        device_serial = EXCLUDED.device_serial
                    RETURNING id
                    """,
                    current_user['id'], bike_from_alert['tracker_name'], 
                    bike_from_alert['device_serial'], bike_from_alert['latest_alert_at']
                )
        
        if not bike:
            raise HTTPException(status_code=404, detail="Bike not found")
        
        return {"bike_id": bike['id']}


@api_router.get("/sync/config")
async def get_sync_config(current_user: dict = Depends(get_current_user)):
    """Get sync configuration for current user - Fixed values: 5 min interval, 30 email limit"""
    return {
        "sync_interval_minutes": 5,
        "email_limit_per_sync": 30
    }


@api_router.post("/sync/config")
async def update_sync_config(request: dict, current_user: dict = Depends(get_current_user)):
    """Update sync configuration for current user - Fixed values: 5 min, 30 emails"""
    # Fixed values - ignore request parameters
    sync_interval = 5
    email_limit = 30
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users 
            SET sync_interval_minutes = $1, 
                email_limit_per_sync = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $3
            """,
            sync_interval, email_limit, current_user['id']
        )
    
    return {"success": True, "message": "Sync configuration updated successfully"}


@api_router.get("/system/status")
async def get_system_status(current_user: dict = Depends(get_current_user)):
    """Get system status information"""
    try:
        async with db_pool.acquire() as conn:
            # Check database connection
            db_connected = True
            
            # Check Gmail connection
            gmail_connected = bool(current_user and current_user.get('gmail_email') and current_user.get('gmail_app_password'))
            
            # Get last sync info
            sync_checkpoint = await conn.fetchrow(
                "SELECT last_email_id, last_sync_at FROM sync_checkpoints WHERE user_id = $1",
                current_user['id']
            )
            
            last_sync_at = str(sync_checkpoint['last_sync_at']) if sync_checkpoint and sync_checkpoint['last_sync_at'] else None
            last_email_id = sync_checkpoint['last_email_id'] if sync_checkpoint else None
            
            # Get total alerts count
            total_alerts = await conn.fetchval(
                "SELECT COUNT(*) FROM tracker_alerts WHERE user_id = $1",
                current_user['id']
            ) or 0
            
            return {
                "database_connected": db_connected,
                "gmail_connected": gmail_connected,
                "gmail_email": current_user.get('gmail_email') if gmail_connected else None,
                "last_sync_at": last_sync_at,
                "last_email_id": last_email_id,
                "total_alerts": total_alerts,
                "system_healthy": db_connected and gmail_connected
            }
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return {
            "database_connected": False,
            "gmail_connected": False,
            "gmail_email": None,
            "last_sync_at": None,
            "last_email_id": None,
            "total_alerts": 0,
            "system_healthy": False
        }


app.include_router(api_router)

app.add_middleware(GZipMiddleware, minimum_size=1000)

allowed_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add Replit URL if running on Replit
replit_domain = os.getenv("REPLIT_DEV_DOMAIN")
if replit_domain:
    allowed_origins.append(f"https://{replit_domain}")
    logger.info(f"Added Replit domain to CORS: https://{replit_domain}")

# Add custom allowed origins from environment variable
# Format: ALLOWED_ORIGINS=https://yourdomain.com,https://app.vercel.app
custom_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
for origin in custom_origins:
    if origin.strip():
        allowed_origins.append(origin.strip())

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
