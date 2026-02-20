from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import datetime

# Setup logging to see alerts in 'docker logs pfe_ai_engine'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI-Engine")

app = FastAPI(title="Zabbix AI Anomaly Detector")

# -------------------------
# Models
# -------------------------
class AlertData(BaseModel):
    host: str
    trigger: str
    severity: str
    value: float

class AnalysisResponse(BaseModel):
    host: str
    prediction: str
    score: float
    timestamp: str

# -------------------------
# Endpoints
# -------------------------

@app.get("/health")
def health():
    return {"status": "online", "engine": "FastAPI", "version": "1.0.0"}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(data: AlertData):
    try:
        # 1. Log the incoming data from Zabbix
        logger.info(f"Received alert from {data.host}: {data.trigger} (Value: {data.value})")

        # 2. AI Logic Placeholder 
        # In a real PFE, you would load a model here: model.predict([[data.value]])
        # For now, we simulate an anomaly score (0.0 to 1.0)
        anomaly_score = data.value / 100.0 
        
        if data.value > 85:
            prediction = "CRITICAL ANOMALY"
        elif data.value > 70:
            prediction = "WARNING: UNUSUAL PATTERN"
        else:
            prediction = "NORMAL"

        # 3. Prepare response
        result = {
            "host": data.host,
            "prediction": prediction,
            "score": round(anomaly_score, 2),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"Analysis Complete for {data.host}: Result = {prediction}")
        return result

    except Exception as e:
        logger.error(f"Error processing analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal AI Engine Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
