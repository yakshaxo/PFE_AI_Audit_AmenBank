import datetime
import logging
import os
import asyncio
import psycopg2
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
from typing import Optional, Union, List
from dotenv import load_dotenv

# --- INITIALIZATION ---
load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AmenBank-AI-Engine")

try:
    from adapter import detect_anomaly, get_recommendation, load_model
    from sla_calculator import calculate_sla
except ImportError as e:
    logger.error(f"Critical Module Import Error: {e}")

# --- INFRASTRUCTURE CONFIGURATION ---
DB_HOST = os.getenv('DB_HOST', 'pfe_postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ai_audit')
DB_USER = os.getenv('DB_USER', 'zabbix')
DB_PASS = os.getenv('DB_PASSWORD')

# --- GRAFANA CONFIGURATION ---
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")

app = FastAPI(
    title="PFE AI Audit Engine - Amen Bank",
    description="Automated AI auditing and anomaly detection for Zabbix infrastructure.",
    version="3.3.0"
)

model = None

# --- DATABASE LOGIC ---

def get_db_connection():
    """Establishes a TCP connection to the PostgreSQL container."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        connect_timeout=5
    )

async def run_daily_maintenance():
  
    while True:
        logger.info("MAINTENANCE: Starting automated 3-month retention purge...")
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # The Bank's Retention Policy
            query = "DELETE FROM ai_results WHERE timestamp < NOW() - INTERVAL '3 months';"
            cursor.execute(query)
            
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            logger.info(f"MAINTENANCE: Success. Purged {deleted_count} old records.")
            
        except Exception as e:
            logger.error(f"MAINTENANCE: Retention purge failed: {e}")
        finally:
            if conn:
                conn.close()
        
        # Sleep for 24 hours
        await asyncio.sleep(86400)

def save_to_db(host_name, prediction, severity, score, issues, recommendations):
    """Persists AI results to the audit layer."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO ai_results (host, prediction, severity, score, issues, recommendations, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            host_name, prediction, severity, score, 
            issues, recommendations, datetime.datetime.now()
        )
        
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        logger.info(f"Audit Persistence Success: {host_name} recorded.")
        
    except Exception as e:
        logger.error(f"Database Persistence Failure: {e}")
    finally:
        if conn:
            conn.close()

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

# --- STARTUP EVENT ---

@app.on_event("startup")
async def startup_event():
    """Initializes the ML model and activates automated maintenance."""
    global model
    logger.info("Initializing Amen Bank AI Engine...")
    
    # 1. Load ML Model
    try:
        model = load_model()
        logger.info("Machine Learning Model loaded successfully.")
    except Exception as e:
        logger.error(f"Model Load Failure: {e}")

    # 2. Verify Database
    try:
        test_conn = get_db_connection()
        test_conn.close()
        logger.info(f"Database Connectivity Verified: {DB_NAME}")
    except Exception as e:
        logger.error(f"DB Connectivity Failure: {e}")

    # 3. Launch Automated Maintenance (Retention)
    asyncio.create_task(run_daily_maintenance())
    logger.info("Background Service: Automated 3-Month Retention is ACTIVE.")

#endpoints

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
            host=data.host,
            prediction=prediction,
            severity=severity,
            score=score,
            issues=issues,
            recommendations=recommendations,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Pipeline Execution Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Engine Error")

@app.get("/health")
def health_check():
    return {
        "status": "active",
        "engine": "PFE-AmenBank-V3.3",
        "maintenance": "Automated Retention Active (90 Days)",
        "database": {"target": DB_HOST, "name": DB_NAME},
        "ml_model_loaded": model is not None
    }

@app.post("/webhook")
async def zabbix_webhook(data: AlertData):
    return await analyze_metric(data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)