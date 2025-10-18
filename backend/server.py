from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import csv
import io
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import imaplib
import email
from email.header import decode_header
import re
import asyncio
from functools import lru_cache
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import hashlib
import uuid


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)

# MongoDB setup
mongo_client: AsyncIOMotorClient = None
db = None

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
    
    await db.refresh_tokens.insert_one({
        "user_id": user_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "created_at": datetime.utcnow()
    })

async def validate_refresh_token(token: str) -> Optional[str]:
    """Validate refresh token against database and return user_id if valid"""
    token_hash = hash_token(token)
    
    result = await db.refresh_tokens.find_one({
        "token_hash": token_hash,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
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
    
    user = await db.users.find_one(
        {"id": user_id},
        {"password_hash": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


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
    global mongo_client, db, background_task
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/tracker_alerts')
    if not mongo_url:
        raise RuntimeError("MONGO_URL environment variable not set")
    
    mongo_client = AsyncIOMotorClient(mongo_url)
    db_name = mongo_url.split('/')[-1] or 'tracker_alerts'
    db = mongo_client[db_name]
    
    logger.info(f"MongoDB connected to database: {db_name}")
    
    # Create indexes
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)
    await db.tracker_alerts.create_index([("user_id", 1), ("email_id", 1)], unique=True)
    await db.tracker_alerts.create_index("user_id")
    await db.tracker_alerts.create_index("tracker_name")
    await db.tracker_alerts.create_index("created_at")
    await db.bikes.create_index([("user_id", 1), ("tracker_name", 1)], unique=True)
    await db.bikes.create_index("user_id")
    await db.sync_checkpoints.create_index("user_id", unique=True)
    await db.refresh_tokens.create_index("token_hash")
    await db.refresh_tokens.create_index("user_id")
    
    # Create default admin user
    admin_exists = await db.users.find_one({"username": "admin"})
    
    if not admin_exists:
        admin_id = str(uuid.uuid4())
        admin_password_hash = pwd_context.hash("dimension")
        await db.users.insert_one({
            "id": admin_id,
            "username": "admin",
            "email": "admin@tracker.com",
            "password_hash": admin_password_hash,
            "full_name": "Administrator",
            "role": "admin",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
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
            
            users = await db.users.find({
                "gmail_email": {"$exists": True, "$ne": None},
                "gmail_app_password": {"$exists": True, "$ne": None}
            }).to_list(None)
            
            for user in users:
                try:
                    new_count = await sync_emails_background(user, limit=30)
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
    global mongo_client, background_task
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        logger.info("Background sync task stopped")
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@api_router.post("/auth/register")
async def register(request: RegisterRequest, response: Response):
    """Register a new user"""
    logger.info(f"Registration attempt: username={request.username}, email={request.email}")
    
    existing = await db.users.find_one({
        "$or": [
            {"username": request.username},
            {"email": request.email}
        ]
    })
    
    if existing:
        logger.warning(f"Registration failed: Username or email already exists - {request.username}/{request.email}")
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(request.password)
    
    await db.users.insert_one({
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "password_hash": password_hash,
        "full_name": request.full_name,
        "role": "admin",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
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
    user = await db.users.find_one({"username": request.username})
    
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
    
    return {
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": user.get('full_name'),
            "role": user.get('role', 'admin')
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
    
    user = await db.users.find_one(
        {"id": user_id},
        {"password_hash": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    await db.refresh_tokens.delete_one({"token_hash": hash_token(refresh_token)})
    
    access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})
    
    await store_refresh_token(user_id, new_refresh_token)
    
    set_auth_cookie(response, "access_token", access_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    set_auth_cookie(response, "refresh_token", new_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    
    return {
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": user.get('full_name'),
            "role": user.get('role', 'admin')
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
        await db.refresh_tokens.delete_one({"token_hash": hash_token(refresh_token)})
    
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
    role = request.get('role', 'viewer')
    
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="Username, email, and password are required")
    
    if role not in ['admin', 'viewer']:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'viewer'")
    
    existing = await db.users.find_one({
        "$or": [
            {"username": username},
            {"email": email}
        ]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(password)
    
    await db.users.insert_one({
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    return {"success": True, "message": f"User '{username}' created successfully with role '{role}'"}


@api_router.get("/users/list")
async def list_users(admin_user: dict = Depends(get_admin_user)):
    """List all users (admin only)"""
    users = await db.users.find(
        {},
        {"password_hash": 0}
    ).sort("created_at", -1).to_list(None)
    
    return {"users": users}


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
    
    await db.users.update_one(
        {"id": current_user['id']},
        {
            "$set": {
                "gmail_email": request.email,
                "gmail_app_password": request.app_password,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"success": True, "message": "Gmail connected successfully"}


@api_router.delete("/gmail/disconnect")
async def disconnect_gmail(current_user: dict = Depends(get_current_user)):
    """Disconnect Gmail account"""
    await db.users.update_one(
        {"id": current_user['id']},
        {
            "$unset": {
                "gmail_email": "",
                "gmail_app_password": ""
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"success": True}


async def sync_emails_background(user: dict, limit: int = 100) -> int:
    """Simple email sync for background task - returns count of new emails"""
    try:
        if not user.get('gmail_email') or not user.get('gmail_app_password'):
            return 0
        
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        checkpoint = await db.sync_checkpoints.find_one({"user_id": user['id']})
        
        _, message_numbers = imap.search(None, f'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        
        if checkpoint and checkpoint.get('last_email_id'):
            try:
                last_idx = email_ids.index(checkpoint['last_email_id'].encode())
                email_ids = email_ids[last_idx + 1:]
            except ValueError:
                email_ids = email_ids[-limit:]
        else:
            email_ids = email_ids[-limit:]
        
        existing_ids = await db.tracker_alerts.find(
            {"user_id": user['id']},
            {"email_id": 1}
        ).to_list(None)
        existing_set = {doc['email_id'] for doc in existing_ids}
        
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
            await db.sync_checkpoints.update_one(
                {"user_id": user['id']},
                {
                    "$set": {
                        "last_email_id": last_email_id,
                        "last_sync_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        
        return total_processed
    
    except Exception as e:
        logger.error(f"Email sync error for {user.get('username', 'unknown')}: {str(e)}")
        return 0


async def process_email_batch(email_data_list: List[tuple], user_id: str):
    """Process a batch of emails"""
    processed_count = 0
    
    for email_id_str, body in email_data_list:
        try:
            parsed = parse_tracker_email(body)
            category = categorize_alert(parsed["alert_type"])
            
            result = await db.tracker_alerts.update_one(
                {"user_id": user_id, "email_id": email_id_str},
                {
                    "$setOnInsert": {
                        "user_id": user_id,
                        "email_id": email_id_str,
                        "alert_type": category,
                        "alert_time": parsed["time"],
                        "location": parsed["location"],
                        "latitude": parsed["latitude"],
                        "longitude": parsed["longitude"],
                        "device_serial": parsed["device_serial"],
                        "tracker_name": parsed["tracker_name"],
                        "account_name": parsed["account_name"],
                        "raw_body": body[:500],
                        "created_at": datetime.utcnow(),
                        "status": "New",
                        "acknowledged": False
                    }
                },
                upsert=True
            )
            
            if result.upserted_id:
                processed_count += 1
        except Exception as e:
            logger.error(f"Error processing email {email_id_str}: {str(e)}")
    
    return processed_count


@api_router.post("/sync/manual")
async def manual_sync(current_user: dict = Depends(get_current_user)):
    """Manually trigger email synchronization"""
    try:
        user = await db.users.find_one({"id": current_user['id']})
        
        if not user or not user.get('gmail_email') or not user.get('gmail_app_password'):
            raise HTTPException(status_code=400, detail="Gmail not configured")
        
        new_count = await sync_emails_background(user, limit=100)
        
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
        user = await db.users.find_one({"id": current_user['id']})
        
        if not user or not user.get('gmail_email') or not user.get('gmail_app_password'):
            raise HTTPException(status_code=400, detail="Gmail not configured")
        
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        _, message_numbers = imap.search(None, 'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        total_emails = len(email_ids)
        
        existing_ids = await db.tracker_alerts.find(
            {"user_id": user['id']},
            {"email_id": 1}
        ).to_list(None)
        existing_set = {doc['email_id'] for doc in existing_ids}
        
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
        user = await db.users.find_one({"id": current_user['id']})
        
        if not user or not user.get('gmail_email') or not user.get('gmail_app_password'):
            raise HTTPException(status_code=400, detail="Gmail not configured")
        
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        _, message_numbers = imap.search(None, 'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        
        existing_ids = await db.tracker_alerts.find(
            {"user_id": user['id']},
            {"email_id": 1}
        ).to_list(None)
        existing_set = {doc['email_id'] for doc in existing_ids}
        
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
            await db.sync_checkpoints.update_one(
                {"user_id": user['id']},
                {
                    "$set": {
                        "last_email_id": email_ids[-1].decode(),
                        "last_sync_at": datetime.utcnow()
                    }
                },
                upsert=True
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
    user = await db.users.find_one({"id": current_user['id']})
    
    query = {"user_id": current_user['id']}
    
    if category and category != "All":
        query["alert_type"] = category
    
    if start_date:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        query["created_at"] = {"$gte": start_datetime}
    
    if end_date:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        if "created_at" in query:
            query["created_at"]["$lt"] = end_datetime
        else:
            query["created_at"] = {"$lt": end_datetime}
    
    total_count = await db.tracker_alerts.count_documents(query)
    
    offset = (page - 1) * limit
    alerts = await db.tracker_alerts.find(query).sort("created_at", -1).skip(offset).limit(limit).to_list(None)
    
    # Get category statistics
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$alert_type", "count": {"$sum": 1}}}
    ]
    category_stats = await db.tracker_alerts.aggregate(pipeline).to_list(None)
    categories = {stat["_id"]: stat["count"] for stat in category_stats}
    
    # Get various counts
    unread_query = {**query, "$or": [{"acknowledged": {"$exists": False}}, {"acknowledged": False}]}
    unread_count = await db.tracker_alerts.count_documents(unread_query)
    
    acknowledged_query = {**query, "acknowledged": True}
    acknowledged_count = await db.tracker_alerts.count_documents(acknowledged_query)
    
    # Format alerts
    alert_list = []
    for a in alerts:
        alert_list.append({
            "id": str(a.get("_id")),
            "alert_type": a.get("alert_type"),
            "alert_time": a.get("alert_time"),
            "location": a.get("location"),
            "latitude": a.get("latitude"),
            "longitude": a.get("longitude"),
            "device_serial": a.get("device_serial"),
            "tracker_name": a.get("tracker_name"),
            "account_name": a.get("account_name"),
            "status": a.get("status", "New"),
            "acknowledged": a.get("acknowledged", False),
            "acknowledged_at": a.get("acknowledged_at").isoformat() if a.get("acknowledged_at") else None,
            "acknowledged_by": a.get("acknowledged_by"),
            "notes": a.get("notes"),
            "assigned_to": a.get("assigned_to"),
            "favorite": a.get("favorite", False)
        })
    
    total_pages = (total_count + limit - 1) // limit
    
    return {
        "alerts": alert_list,
        "stats": {
            "total": total_count,
            "unread": unread_count,
            "acknowledged": acknowledged_count,
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
        "connected": bool(user and user.get('gmail_email')),
        "email": user.get('gmail_email') if user else None,
        "activeFilter": category or "All"
    }


@api_router.delete("/alerts/clear-all/history")
async def clear_all_alerts(current_user: dict = Depends(get_current_user)):
    """Clear all alerts and sync checkpoint (reset system)"""
    await db.tracker_alerts.delete_many({"user_id": current_user['id']})
    await db.sync_checkpoints.delete_many({"user_id": current_user['id']})
    
    return {"success": True, "message": "All alerts and sync history cleared"}


@api_router.get("/bikes/list")
async def list_bikes(current_user: dict = Depends(get_current_user)):
    """Get all bikes for the current user with alert counts"""
    pipeline = [
        {"$match": {"user_id": current_user['id']}},
        {
            "$group": {
                "_id": "$tracker_name",
                "device_serial": {"$first": "$device_serial"},
                "latest_alert_at": {"$max": "$created_at"},
                "alert_count": {"$sum": 1}
            }
        },
        {"$sort": {"latest_alert_at": -1}}
    ]
    
    bikes_data = await db.tracker_alerts.aggregate(pipeline).to_list(None)
    
    result = []
    for bike in bikes_data:
        # Upsert bike
        bike_doc = await db.bikes.find_one_and_update(
            {"user_id": current_user['id'], "tracker_name": bike["_id"]},
            {
                "$set": {
                    "device_serial": bike["device_serial"],
                    "latest_alert_at": bike["latest_alert_at"],
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "user_id": current_user['id'],
                    "tracker_name": bike["_id"],
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True,
            return_document=True
        )
        
        # Count notes
        notes_count = await db.bike_notes.count_documents({"bike_id": str(bike_doc["_id"])})
        
        result.append({
            "id": str(bike_doc["_id"]),
            "tracker_name": bike["_id"],
            "device_serial": bike["device_serial"],
            "latest_alert_at": bike["latest_alert_at"].isoformat() if bike["latest_alert_at"] else None,
            "alert_count": bike["alert_count"],
            "notes_count": notes_count
        })
    
    return {"bikes": result}


# Mount API router
app.include_router(api_router)


# Root redirect
@app.get("/")
async def root():
    return RedirectResponse(url="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "mongodb"}
