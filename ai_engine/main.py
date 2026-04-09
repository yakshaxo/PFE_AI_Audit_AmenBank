import datetime
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from adapter import detect_anomaly, get_recommendation, load_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI-Engine")

app = FastAPI(title="PFE AI Engine", version="2.2.0")
model = None


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


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(data: AlertData):
    try:
        
        item_key = data.item_key or "unknown"
        logger.info(f"📨 Requête reçue pour l'hôte : {data.host}")

        if model is None:
            raise ValueError("Le modèle IA n'est pas chargé.")

        # Exécution de la détection
        result = detect_anomaly(model, data.value, item_key)
        
        # Récupération des recommandations (résultat est un dict, donc .get() est OK ici)
        recs = get_recommendation(result)
        
        return AnalysisResponse(
            host=data.host,
            prediction=result.get("prediction", "NORMAL"),
            severity=result.get("severity", "LOW"),
            score=round(float(result.get("anomaly_score", 0.0)), 2),
            issues=result.get("issues", []),
            recommendations=recs,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"💥 Erreur dans /analyze: {str(e)}")
        # Renvoie l'erreur exacte à PowerShell pour le debug
        raise HTTPException(status_code=500, detail=f"Internal AI Engine Error: {str(e)}")

@app.post("/webhook", response_model=AnalysisResponse)
async def webhook(data: AlertData):
    return await analyze(data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
