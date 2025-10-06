from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
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
import re
import asyncio
from functools import lru_cache
from passlib.context import CryptContext


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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

ALERT_CATEGORIES = [
    "Heavy Impact",
    "Light Sensor",
    "Out Of Country",
    "No Communication",
    "Over-turn",
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


class LoginRequest(BaseModel):
    username: str
    password: str

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
    
    db_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    logger.info("Database pool created")
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                email VARCHAR,
                name VARCHAR,
                picture VARCHAR,
                gmail_email VARCHAR,
                gmail_app_password VARCHAR,
                username VARCHAR UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        admin_exists = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE username = 'admin'"
        )
        
        if admin_exists == 0:
            admin_password_hash = pwd_context.hash("dimension")
            await conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, created_at)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                ON CONFLICT (username) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash
                """,
                "admin-user", "admin", "admin@tracker.com", admin_password_hash
            )
            logger.info("Admin user created/updated automatically")
        else:
            logger.info("Admin user already exists")
    
    background_task = asyncio.create_task(auto_sync_background())
    logger.info("Background sync task started (10 minute interval)")

async def auto_sync_background():
    """Background task to automatically sync alerts every 10 minutes"""
    while True:
        try:
            await asyncio.sleep(600)
            
            async with db_pool.acquire() as conn:
                user = await conn.fetchrow(
                    "SELECT * FROM users WHERE id = $1",
                    DEFAULT_USER_ID
                )
                
                if user and user['gmail_email'] and user['gmail_app_password']:
                    logger.info("Starting automatic background sync...")
                    
                    try:
                        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
                        imap.select("INBOX")
                        
                        checkpoint = await conn.fetchrow(
                            "SELECT * FROM sync_checkpoints WHERE user_id = $1",
                            DEFAULT_USER_ID
                        )
                        
                        _, message_numbers = imap.search(None, f'FROM "alerts-no-reply@tracking-update.com"')
                        email_ids = message_numbers[0].split()
                        
                        if checkpoint and checkpoint['last_email_id']:
                            try:
                                last_idx = email_ids.index(checkpoint['last_email_id'].encode())
                                email_ids = email_ids[last_idx + 1:]
                                logger.info(f"Background sync: processing {len(email_ids)} new emails")
                            except ValueError:
                                email_ids = email_ids[-100:]
                        else:
                            email_ids = email_ids[-100:]
                        
                        if email_ids:
                            async with db_pool.acquire() as conn2:
                                existing_ids = await conn2.fetch(
                                    "SELECT email_id FROM tracker_alerts WHERE user_id = $1",
                                    DEFAULT_USER_ID
                                )
                                existing_set = {row['email_id'] for row in existing_ids}
                                
                                email_data_list = []
                                for email_id in email_ids:
                                    email_id_str = email_id.decode()
                                    if email_id_str not in existing_set:
                                        try:
                                            _, msg_data = imap.fetch(email_id, "(RFC822)")
                                            email_body = msg_data[0][1]
                                            msg = email.message_from_bytes(email_body)
                                            body = get_email_body(msg)
                                            email_data_list.append((email_id_str, body))
                                        except Exception as e:
                                            logger.error(f"Error fetching email: {str(e)}")
                                
                                if email_data_list:
                                    processed = await process_email_batch(email_data_list)
                                    last_email_id = email_data_list[-1][0]
                                    await conn2.execute(
                                        """
                                        INSERT INTO sync_checkpoints (user_id, last_email_id, last_sync_at)
                                        VALUES ($1, $2, CURRENT_TIMESTAMP)
                                        ON CONFLICT (user_id) DO UPDATE
                                        SET last_email_id = $2, last_sync_at = CURRENT_TIMESTAMP
                                        """,
                                        DEFAULT_USER_ID, last_email_id
                                    )
                                    logger.info(f"Background sync completed: {processed} alerts processed")
                        
                        imap.logout()
                    except Exception as e:
                        logger.error(f"Background sync error: {str(e)}")
                else:
                    logger.debug("Background sync skipped: Gmail not connected")
                    
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


@api_router.post("/auth/login")
async def login(request: LoginRequest):
    """Login with database authentication"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, password_hash FROM users WHERE username = $1",
            request.username
        )
        
        if not user or not user['password_hash']:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not pwd_context.verify(request.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'] or f"{user['username']}@tracker.com"
            }
        }


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
async def connect_gmail(request: ConnectGmailRequest):
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
            DEFAULT_USER_ID, request.email, request.app_password
        )
    
    return {"success": True, "message": "Gmail connected successfully"}


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


async def process_email_batch(email_data_list: List[tuple]):
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
                    DEFAULT_USER_ID, email_id_str, category, 
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


@api_router.post("/alerts/sync")
async def sync_alerts(request: SyncRequest):
    """Fetch and categorize tracker alerts from Gmail with parallel processing and checkpoint"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            DEFAULT_USER_ID
        )
        
        if not user or not user['gmail_email'] or not user['gmail_app_password']:
            raise HTTPException(status_code=404, detail="Gmail not connected")
        
        checkpoint = await conn.fetchrow(
            "SELECT * FROM sync_checkpoints WHERE user_id = $1",
            DEFAULT_USER_ID
        )
    
    try:
        imap = connect_imap(user['gmail_email'], user['gmail_app_password'])
        imap.select("INBOX")
        
        _, message_numbers = imap.search(None, f'FROM "alerts-no-reply@tracking-update.com"')
        email_ids = message_numbers[0].split()
        
        if checkpoint and checkpoint['last_email_id']:
            try:
                last_idx = email_ids.index(checkpoint['last_email_id'].encode())
                email_ids = email_ids[last_idx + 1:]
                logger.info(f"Incremental sync: processing {len(email_ids)} new emails since last checkpoint")
            except ValueError:
                logger.warning("Checkpoint email not found, processing latest emails")
                email_ids = email_ids[-request.limit:]
        else:
            email_ids = email_ids[-request.limit:]
        
        logger.info(f"Found {len(email_ids)} emails to process")
        
        async with db_pool.acquire() as conn:
            existing_ids = await conn.fetch(
                """
                SELECT email_id FROM tracker_alerts 
                WHERE user_id = $1
                """,
                DEFAULT_USER_ID
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
                return {"success": True, "categorized": 0, "message": "No new emails to process"}
            
            logger.info(f"Processing {len(email_data_list)} new emails in parallel")
            
            batch_size = 10
            total_processed = 0
            
            for i in range(0, len(email_data_list), batch_size):
                batch = email_data_list[i:i + batch_size]
                processed = await process_email_batch(batch)
                total_processed += processed
            
            logger.info(f"Successfully processed {total_processed} emails")
            
            if email_data_list:
                last_email_id = email_data_list[-1][0]
                await conn.execute(
                    """
                    INSERT INTO sync_checkpoints (user_id, last_email_id, last_sync_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE
                    SET last_email_id = $2, last_sync_at = CURRENT_TIMESTAMP
                    """,
                    DEFAULT_USER_ID, last_email_id
                )
                logger.info(f"Checkpoint saved: {last_email_id}")
            
            return {"success": True, "categorized": total_processed}
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@api_router.get("/alerts/categories")
async def get_categories():
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
            DEFAULT_USER_ID
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
async def list_alerts(category: Optional[str] = Query(None)):
    """Get all tracker alerts with optional category filter"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            DEFAULT_USER_ID
        )
        
        if category and category != "All":
            alerts = await conn.fetch(
                """
                SELECT * FROM tracker_alerts 
                WHERE user_id = $1 AND alert_type = $2
                ORDER BY created_at DESC
                """,
                DEFAULT_USER_ID, category
            )
        else:
            alerts = await conn.fetch(
                """
                SELECT * FROM tracker_alerts 
                WHERE user_id = $1 
                ORDER BY created_at DESC
                """,
                DEFAULT_USER_ID
            )
        
        categories = {}
        for alert in alerts:
            cat = alert["alert_type"] or "Other"
            categories[cat] = categories.get(cat, 0) + 1
        
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
        
        over_turn_count = 0
        no_communication_count = 0
        heavy_impact_count = 0
        
        device_alerts = {}
        for alert in alerts:
            device = alert["tracker_name"] or "Unknown"
            alert_type = alert["alert_type"] or "Other"
            
            if device not in device_alerts:
                device_alerts[device] = set()
            device_alerts[device].add(alert_type)
            
            if alert_type == "Over-turn":
                over_turn_count += 1
            elif "No Communication" in alert_type:
                no_communication_count += 1
            elif "Heavy Impact" in alert_type:
                heavy_impact_count += 1
        
        high_priority_count = 0
        heavy_impact_bikes_count = 0
        
        for device, alert_types in device_alerts.items():
            has_light_sensor = "Light Sensor" in alert_types
            has_over_turn = "Over-turn" in alert_types
            has_heavy_impact = any("Heavy Impact" in t for t in alert_types)
            has_no_comm = any("No Communication" in t for t in alert_types)
            
            if has_light_sensor and has_over_turn:
                heavy_impact_bikes_count += 1
            elif has_over_turn or has_heavy_impact or has_no_comm:
                high_priority_count += 1
        
        return {
            "alerts": alert_list,
            "stats": {
                "total": len(alert_list),
                "unread": len(alert_list),
                "highPriority": high_priority_count,
                "heavyImpact": heavy_impact_bikes_count,
                "acknowledged": 0,
                "overTurn": over_turn_count,
                "noCommunication": no_communication_count,
                "heavyImpactAlerts": heavy_impact_count,
                "categories": categories
            },
            "connected": bool(user and user['gmail_email']),
            "email": user['gmail_email'] if user else None,
            "activeFilter": category or "All"
        }


@api_router.delete("/alerts/clear-all/history")
async def clear_all_alerts():
    """Clear all alerts and sync checkpoint (reset system)"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM tracker_alerts WHERE user_id = $1",
            DEFAULT_USER_ID
        )
        await conn.execute(
            "DELETE FROM sync_checkpoints WHERE user_id = $1",
            DEFAULT_USER_ID
        )
    
    return {"success": True, "message": "All alerts and sync history cleared"}


@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    """Delete an alert (only from app, not from Gmail)"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM tracker_alerts WHERE id = $1 AND user_id = $2",
            alert_id, DEFAULT_USER_ID
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, request: AcknowledgeRequest):
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
            request.acknowledged_by, alert_id, DEFAULT_USER_ID
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/status")
async def update_alert_status(alert_id: int, request: UpdateStatusRequest):
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
            request.status, alert_id, DEFAULT_USER_ID
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/notes")
async def add_alert_note(alert_id: int, request: AddNoteRequest):
    """Add notes to an alert"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET notes = $1
            WHERE id = $2 AND user_id = $3
            """,
            request.notes, alert_id, DEFAULT_USER_ID
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/assign")
async def assign_alert(alert_id: int, request: AssignRequest):
    """Assign alert to a team member"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET assigned_to = $1
            WHERE id = $2 AND user_id = $3
            """,
            request.assigned_to, alert_id, DEFAULT_USER_ID
        )
    
    return {"success": True}


@api_router.post("/alerts/{alert_id}/favorite")
async def toggle_favorite(alert_id: int):
    """Toggle favorite status"""
    async with db_pool.acquire() as conn:
        current = await conn.fetchrow(
            "SELECT favorite FROM tracker_alerts WHERE id = $1 AND user_id = $2",
            alert_id, DEFAULT_USER_ID
        )
        
        new_value = not current['favorite'] if current else True
        
        await conn.execute(
            """
            UPDATE tracker_alerts 
            SET favorite = $1
            WHERE id = $2 AND user_id = $3
            """,
            new_value, alert_id, DEFAULT_USER_ID
        )
    
    return {"success": True, "favorite": new_value}


app.include_router(api_router)

app.add_middleware(GZipMiddleware, minimum_size=1000)

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
