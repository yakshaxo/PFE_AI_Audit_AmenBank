import datetime
import logging
import os
import time
import psycopg2
from fastapi import FastAPI, HTTPException
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

# --- GRAFANA CONFIGURATION (SECURE FETCH) ---
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")

app = FastAPI(
    title="PFE AI Audit Engine - Amen Bank",
    description="Automated AI auditing and anomaly detection for Zabbix infrastructure.",
    version="3.2.0"
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

def save_to_db(host_name, prediction, severity, score, issues, recommendations):
    """Securely persists AI results to the audit layer."""
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
        logger.info(f"Audit Persistence Success: {host_name} recorded at {score}")
        
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

# --- ENDPOINTS ---

@app.on_event("startup")
async def startup_event():
    """Initializes the ML model and verifies connectivity dependencies."""
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
        logger.info(f"Database Connectivity Verified: {DB_NAME} at {DB_HOST}")
    except Exception as e:
        logger.error(f"DB Connectivity Failure: {e}")

    # 3. Verify Grafana Config (Environment only)
    if GRAFANA_URL and GRAFANA_TOKEN:
        logger.info(f"Grafana Integration: Configured for {GRAFANA_URL}")
    else:
        logger.warning("Grafana Integration: Missing URL or Token in environment.")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_metric(data: AlertData):
    """Primary pipeline for processing Zabbix alerts through the AI Audit layer."""
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
    """Detailed health check for PFE defense demonstration."""
    return {
        "status": "active",
        "engine": "PFE-AmenBank-V3",
        "database": {
            "target": DB_HOST,
            "name": DB_NAME
        },
        "grafana": {
            "configured": bool(GRAFANA_URL and GRAFANA_TOKEN),
            "endpoint": GRAFANA_URL if GRAFANA_URL else "Not Set"
        },
        "ml_model_loaded": model is not None
    }

@app.post("/webhook")
async def zabbix_webhook(data: AlertData):
    return await analyze_metric(data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)