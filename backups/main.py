import datetime
import logging
import os
import asyncio
import psycopg2
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import Optional, Union, List
from dotenv import load_dotenv
from passlib.context import CryptContext
import bcrypt

# --- INITIALIZATION ---
load_dotenv()

# Setup password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AmenBank-AI-Engine")

try:
    from adapter import detect_anomaly, get_recommendation, load_model
except ImportError as e:
    logger.error(f"Critical Module Import Error: {e}")

# --- INFRASTRUCTURE CONFIGURATION ---
DB_HOST = os.getenv('DB_HOST', 'pfe_postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ai_core_db')
DB_USER = os.getenv('DB_USER', 'zabbix')
DB_PASS = os.getenv('DB_PASSWORD')

app = FastAPI(
    title="PFE AI Audit Engine - Amen Bank",
    description="Automated AI auditing and anomaly detection for Zabbix infrastructure.",
    version="3.3.0"
)

# --- UI SETUP ---
templates = Jinja2Templates(directory="templates")
model = None

# --- DATABASE LOGIC ---

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        connect_timeout=5
    )

def verify_password(plain_password, hashed_password):
    
    try:
        
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Bcrypt verification error: {e}")
        return False

async def run_daily_maintenance():
    while True:
        logger.info("MAINTENANCE: Starting automated 3-month retention purge...")
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "DELETE FROM ai_results WHERE timestamp < NOW() - INTERVAL '3 months';"
            cursor.execute(query)
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            logger.info(f"MAINTENANCE: Success. Purged {deleted_count} old records.")
        except Exception as e:
            logger.error(f"MAINTENANCE: Retention purge failed: {e}")
        finally:
            if conn: conn.close()
        await asyncio.sleep(86400)

def save_to_db(host_name, prediction, severity, score, issues, recommendations):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO ai_results (host, prediction, severity, score, issues, recommendations, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (host_name, prediction, severity, score, issues, recommendations, datetime.datetime.now())
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        logger.info(f"Audit Persistence Success: {host_name} recorded.")
    except Exception as e:
        logger.error(f"Database Persistence Failure: {e}")
    finally:
        if conn: conn.close()

# --- SCHEMAS ---

class AlertData(BaseModel):
    host: str
    trigger: Optional[str] = "Manual Trigger"
    severity: Optional[Union[str, int, float]] = "Not Set"
    value: float
    item_key: Optional[str] = "system.cpu.util"

    @field_validator("severity", mode="before")
    @classmethod
    def coerce_severity(cls, v):
        return str(v) if v is not None else "Unknown"

class AnalysisResponse(BaseModel):
    host: str
    prediction: str
    severity: str
    score: float
    issues: List[str]
    recommendations: List[str]
    timestamp: str

# --- AUTH & UI ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT hashed_password, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        # FIXED: Argument order is (plain_password, hashed_password)
        if user and verify_password(password, user[0]):
            role = user[1]
            if role == "admin":
                return RedirectResponse(url="/admin_dashboard", status_code=303)
            return RedirectResponse(url="/user_dashboard", status_code=303)
        
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid Credentials"})
    except Exception as e:
        logger.error(f"Login Database Error: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Database error"})
    finally:
        if conn: conn.close()

@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_ui(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/user_dashboard", response_class=HTMLResponse)
async def user_ui(request: Request):
    return templates.TemplateResponse("user_dashboard.html", {"request": request})

# --- AI ENDPOINTS ---

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_metric(data: AlertData):
    try:
        result = detect_anomaly(model, data.value, data.item_key, data.severity)
        prediction = result.get("prediction", "NORMAL")
        severity = result.get("severity", "LOW")
        score = round(float(result.get("anomaly_score", 0.0)), 3)
        issues = result.get("issues", [])
        recommendations = get_recommendation(result)

        save_to_db(data.host, prediction, severity, score, issues, recommendations)

        return AnalysisResponse(
            host=data.host, prediction=prediction, severity=severity,
            score=score, issues=issues, recommendations=recommendations,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Engine Error")

@app.post("/webhook")
async def zabbix_webhook(data: AlertData):
    return await analyze_metric(data)

@app.get("/health")
def health_check():
    return {"status": "active", "database": DB_NAME, "ml_model_loaded": model is not None}

# --- STARTUP ---

@app.on_event("startup")
async def startup_event():
    global model
    logger.info("Waiting for Database system to stabilize...")
    await asyncio.sleep(5) 
    try:
        model = load_model()
        logger.info("Model loaded.")
    except Exception:
        logger.error("Model failed.")
    asyncio.create_task(run_daily_maintenance())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)