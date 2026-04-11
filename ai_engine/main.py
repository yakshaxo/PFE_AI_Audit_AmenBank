import datetime
import logging
import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Union, List
from dotenv import load_dotenv


try:
    from adapter import detect_anomaly, get_recommendation, load_model
    from sla_calculator import calculate_sla
except ImportError as e:
    print(f"Error importing local modules: {e}")


load_dotenv()

# --- CONFIGURATION FROM ENVIRONMENT ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AmenBank-AI-Engine")

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}


GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")

app = FastAPI(
    title="PFE AI Audit Engine - Amen Bank",
    description="Automated AI auditing and anomaly detection for Zabbix infrastructure.",
    version="3.0.0"
)


model = None


def save_to_db(host, prediction, severity, score, issues, recommendations):
    """Securely saves the AI audit results to PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_results (host, prediction, severity, score, issues, recommendations, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            host, prediction, severity, score, 
            issues, recommendations, datetime.datetime.now()
        ))
        conn.commit()
        cursor.close()
        logger.info(f"Audit Logged: {host} is {prediction}")
    except Exception as e:
        logger.error(f"Database Persistence Error: {e}")
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
    """Initializes the ML model on startup."""
    global model
    logger.info("Initializing PFE AI Engine...")
    try:
        model = load_model()
        logger.info("Machine Learning model loaded from disk.")
    except Exception as e:
        logger.error(f"Failed to load AI model: {e}. Fallback mode active.")

@app.get("/health")
def health_check():
    """Check system status and environment variable connectivity."""
    return {
        "status": "online",
        "model_ready": model is not None,
        "database_target": DB_CONFIG['host'],
        "grafana_auth": "Token-based" if GRAFANA_TOKEN else "Missing"
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_metric(data: AlertData):
    """The main AI pipeline: Analyze -> Audit -> Respond."""
    try:
        # 1. Run AI Detection
        result = detect_anomaly(model, data.value, data.item_key)
        
        # 2. Extract results
        prediction = result.get("prediction", "NORMAL")
        severity = result.get("severity", "LOW")
        score = round(float(result.get("anomaly_score", 0.0)), 2)
        issues = result.get("issues", [])
        recommendations = get_recommendation(result)

        # 3. Save to Audit Database
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
        logger.error(f"Analysis Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail="Internal AI Engine Error")

@app.get("/sla/{host}")
async def get_host_sla(host: str, days: int = 30):
    """Calculate availability percentage for the bank's SLA reports."""
    return calculate_sla(host, days)

@app.post("/webhook")
async def zabbix_webhook(data: AlertData):
    """Direct integration point for Zabbix HTTP Media Types."""
    return await analyze_metric(data)

if __name__ == "__main__":
    import uvicorn
    app_port = int(os.getenv("APP_PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=app_port)