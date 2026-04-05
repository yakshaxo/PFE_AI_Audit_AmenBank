#!/usr/bin/env python3
"""
AI Engine - Amen Bank Monitoring System
FastAPI application integrating Hakim's ML model
"""

import datetime
import logging
import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Import Hakim's adapter
from adapter import detect_anomaly, get_recommendation, load_model

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai_engine")

# Audit logger
audit_logger = logging.getLogger('audit')
os.makedirs('/logs', exist_ok=True)
audit_handler = logging.FileHandler('/logs/audit.log')
audit_handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="PFE AI Engine - Amen Bank",
    version="2.0.0",
    description="AI-powered anomaly detection for server monitoring"
)

# Global model variable
model = None

# Pydantic models for request/response
class AlertData(BaseModel):
    host: str
    trigger: Optional[str] = "Unknown Trigger"
    severity: Optional[str] = "Unknown"
    value: float
    item_key: Optional[str] = None
    metric: Optional[str] = None  # Alternative field name
    event_id: Optional[str] = None

class AnalysisResponse(BaseModel):
    host: str
    prediction: str
    severity: str
    score: float
    issues: list[str]
    recommendations: list[str]
    timestamp: str

def log_audit(action: str, data: dict):
    """Log to audit trail"""
    audit_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": action,
        "data": data
    }
    audit_logger.info(json.dumps(audit_entry))

@app.on_event("startup")
async def startup_event():
    """Load Hakim's ML model at startup"""
    global model
    
    logger.info("="*60)
    logger.info("🚀 AI Engine starting up...")
    logger.info("🏦 Bank: Amen Bank")
    logger.info("📊 Project: PFE - Intelligent Monitoring")
    logger.info("🤖 ML Model: Hakim's Isolation Forest + Statistical Analyzer")
    logger.info("="*60)
    
    try:
        model = load_model()
        logger.info("✅ ML Model loaded successfully")
        logger.info(f"✅ Model type: {type(model).__name__}")
    except Exception as e:
        logger.error(f"❌ Failed to load ML model: {e}")
        logger.warning("⚠️ Starting without ML model - will use statistical fallback")
        model = None
    
    log_audit("SYSTEM_STARTUP", {
        "timestamp": datetime.datetime.now().isoformat(),
        "model_loaded": model is not None
    })

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 AI Engine shutting down...")
    log_audit("SYSTEM_SHUTDOWN", {"timestamp": datetime.datetime.now().isoformat()})

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PFE AI Engine - Amen Bank",
        "version": "2.0.0",
        "status": "running",
        "ml_model": type(model).__name__ if model else "Not loaded",
        "developer": "Louay (Infrastructure) + Hakim (ML)"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "online",
        "model_loaded": model is not None,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(data: AlertData):
    """
    Main analysis endpoint - Uses Hakim's ML + Statistical Analyzer
    
    Expected input from Zabbix:
    {
        "host": "LOUAY-PC",
        "trigger": "High CPU usage",
        "severity": "High",
        "value": 92.5,
        "item_key": "system.cpu.util"
    }
    """
    
    try:
        # 1. Extract and validate data
        item_key = data.item_key or data.metric or "unknown"
        value = data.value
        
        if value is None:
            raise HTTPException(
                status_code=400, 
                detail="Missing 'value' in request data"
            )
        
        logger.info(f"📨 Alert from {data.host}: {data.trigger} | Value: {value}")
        
        # Log incoming alert
        log_audit("ALERT_RECEIVED", {
            "host": data.host,
            "trigger": data.trigger,
            "severity": data.severity,
            "value": value,
            "item_key": item_key
        })
        
        # 2. Detect anomaly using Hakim's adapter
        #    This calls BOTH the ML model AND statistical analyzer
        anomaly_result = detect_anomaly(model, value, item_key)
        
        prediction = anomaly_result.get("prediction", "UNKNOWN")
        severity = anomaly_result.get("severity", "LOW")
        anomaly_score = anomaly_result.get("anomaly_score", 0.0)
        issues = anomaly_result.get("issues", [])
        
        # 3. Get recommendations from Hakim's recommender
        recommendations = get_recommendation(anomaly_result, alert=data.dict())
        
        # 4. Build response
        result = AnalysisResponse(
                host=data.get("host", "unknown"),
                prediction=anomaly_result["prediction"],
                severity=anomaly_result["severity"],
                score=anomaly_result["anomaly_score"],
                issues=anomaly_result["issues"],
                recommendations=recommendations,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 5. Log result
        logger.info(
            f"✅ {data.host}: {prediction} | "
            f"Severity: {severity} | Score: {anomaly_score:.2f}"
        )
        
        log_audit("AI_PREDICTION", {
            "host": data.host,
            "prediction": prediction,
            "severity": severity,
            "score": anomaly_score,
            "issues": issues,
            "recommendations": recommendations
        })
        
        return result

    except HTTPException as http_err:
        logger.error(f"HTTP error: {str(http_err)}")
        raise http_err
    
    except Exception as e:
        logger.error(f"❌ Error processing analysis: {str(e)}")
        log_audit("ERROR", {"error": str(e), "alert_data": data.dict()})
        raise HTTPException(
            status_code=500, 
            detail=f"Internal AI Engine Error: {str(e)}"
        )

@app.post("/webhook", response_model=AnalysisResponse)
async def webhook(data: AlertData):
    """Webhook endpoint (alias for /analyze) - Used by Zabbix"""
    return await analyze(data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")