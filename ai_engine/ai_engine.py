import logging
from adapter import detect_anomaly, get_recommendation, load_model
from database import save_audit_result 

logger = logging.getLogger("NEXUS-AI-Engine")

class AILogicCenter:
    def __init__(self):
        self.model = None

    def load_brain(self):
        try:
            self.model = load_model()
            logger.info("NEXUS AI Brain loaded successfully.")
        except Exception as e:
            logger.error(f"NEXUS AI Brain Load Failed: {e}")

    def analyze_and_store(self, host, value, item_key, severity):
        result = detect_anomaly(self.model, value, item_key, severity)
        
        prediction = result.get("prediction", "NORMAL")
        score = round(float(result.get("anomaly_score", 0.0)), 3)
        issues = ", ".join(result.get("issues", []))
        recommendations = get_recommendation(result)
        
        save_audit_result(host, prediction, severity, score, issues, recommendations)
        
        return {
            "prediction": prediction,
            "score": score,
            "recommendations": recommendations
        }

engine = AILogicCenter()