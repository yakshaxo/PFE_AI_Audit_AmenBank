import datetime
import logging
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from adapter import detect_anomaly, get_recommendation, load_model
from sla_calculator import calculate_sla

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI-Engine")

app = FastAPI(title="PFE AI Engine", version="2.4.0")
model = None

# AI audit database config
DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'ai_audit',
    'user': 'zabbix',
    'password': 'StrongPassword123'
}


def save_to_db(host, prediction, severity, score, issues, recommendations):
    """Save analysis result to ai_audit database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_results (host, prediction, severity, score, issues, recommendations, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            host,
            prediction,
            severity,
            score,
            issues,
            recommendations,
            datetime.datetime.now()
        ))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Result saved to database for host: {host}")
    except Exception as e:
        logger.error(f"Database save failed: {e}")


class AlertData(BaseModel):
    host: str
    trigger: Optional[str] = "Unknown"
    severity: Optional[Union[str, int, float]] = "Unknown"
    value: float
    item_key: Optional[str] = None
    metric: Optional[str] = None

    @field_validator("severity", mode="before")
    @classmethod
    def coerce_severity(cls, v):
        if v is None:
            return "Unknown"
        return str(v)


class AnalysisResponse(BaseModel):
    host: str
    prediction: str
    severity: str
    score: float
    issues: list
    recommendations: list
    timestamp: str


@app.on_event("startup")
async def startup_event():
    global model
    logger.info("Starting AI Engine...")
    try:
        model = load_model()
        if model:
            logger.info("Model loaded successfully")
        else:
            logger.warning("No model file found - running in statistical-only mode")
    except Exception as e:
        logger.error(f"Model error: {e}")


@app.get("/health")
def health():
    return {"status": "online", "model": model is not None}


@app.get("/sla/{host}")
async def get_sla(host: str, days: int = 30):
    """
    Calculate SLA for a given host over the last N days.
    Example: GET /sla/louay-pc?days=7
    """
    logger.info(f"SLA request for host: {host} over {days} days")
    return calculate_sla(host, days)


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(data: AlertData):
    try:
        item_key = data.item_key or data.metric or "unknown"
        logger.info(f"Processing: {data.host} | Key: {item_key} | Value: {data.value}")

        # 1. Run anomaly detection
        result = detect_anomaly(model, data.value, item_key)

        # 2. Read from result dict
        prediction = result.get("prediction", "NORMAL")
        severity   = result.get("severity", "LOW")
        raw_score  = result.get("anomaly_score") or 0.0
        issues     = result.get("issues", ["No specific issues detected"])

        # 3. Generate recommendations
        recs = get_recommendation(result)

        # 4. Save to database
        save_to_db(data.host, prediction, severity, round(float(raw_score), 2), issues, recs)

        return AnalysisResponse(
            host=data.host,
            prediction=prediction,
            severity=severity,
            score=round(float(raw_score), 2),
            issues=issues,
            recommendations=recs,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    except Exception as e:
        logger.error(f"CRASH in /analyze: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal AI Engine Error: {str(e)}")


@app.post("/webhook", response_model=AnalysisResponse)
async def webhook(data: AlertData):
    return await analyze(data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)