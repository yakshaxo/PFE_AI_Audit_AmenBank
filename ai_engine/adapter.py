import pandas as pd
import joblib
import os
import numpy as np
import sys
import logging

logger = logging.getLogger("AI-Engine")
sys.path.append(os.path.dirname(__file__))

try:
    from analyzer import analyze_row
    from recommender import recommend as hakim_recommend
    HAKIM_AVAILABLE = True
except ImportError:
    HAKIM_AVAILABLE = False

# Synthetic baseline
np.random.seed(42)
baseline_df = pd.DataFrame({
    'cpu_usage': np.random.normal(30, 10, 100),
    'memory_usage': np.random.normal(40, 15, 100),
    'network_traffic': np.random.normal(100, 50, 100)
})

def load_model():
    models_dir = os.path.join(os.path.dirname(__file__), 'models')
    possible_names = ['model.pkl', 'audit_model.joblib', 'model.joblib']
    for name in possible_names:
        path = os.path.join(models_dir, name)
        if os.path.exists(path):
            return joblib.load(path)
    raise FileNotFoundError(f"AI Model not found in {models_dir}")

def detect_anomaly(model, value: float, item_key: str, zabbix_severity: str = "LOW") -> dict:
    """
    Enhanced detection logic that captures real probability scores 
    and respects Zabbix severity levels.
    """
    row = pd.Series({
    'cpu_usage':       value if any(x in item_key.lower() for x in ['cpu', 'processor', 'load']) else 30,
    'memory_usage':    value if any(x in item_key.lower() for x in ['mem', 'vm.memory', 'swap']) else 40,
    'network_traffic': value if any(x in item_key.lower() for x in ['net', 'eth', 'traffic', 'if.in']) else 100,
})

    feature_order = ['cpu', 'memory', 'disk', 'network']
    model_data = [[
        value if 'cpu'     in item_key.lower() else 30,
        value if 'memory'  in item_key.lower() else 40,
        30,
        value if 'network' in item_key.lower() else 100,
    ]]
    model_input = pd.DataFrame(model_data, columns=feature_order)

    
    try:
        # Check if the model can provide probability scores
        if hasattr(model, "predict_proba"):
            # Get the probability for the 'Anomaly' class
            probabilities = model.predict_proba(model_input)[0]
            # If your model uses [Normal, Anomaly], take the second index
            anomaly_score = float(probabilities[1]) 
        else:
            # Fallback: if no probability, use a calculation based on the value
            # Example: higher value relative to 100% = higher score
            anomaly_score = min(0.99, value / 100.0) if value > 80 else 0.15
            
        is_ai_anomaly = (anomaly_score > 0.5)
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        anomaly_score = 0.5

    # 2. Statistical analysis
    if HAKIM_AVAILABLE:
        analysis = analyze_row(row, baseline_df)
    else:
        analysis = {"severity": "LOW", "issues": ["AI Pattern Detected"]}

    # 3. Logic: Use Zabbix Severity if AI is LOW but Zabbix is HIGH
    final_severity = analysis.get('severity', 'LOW')
    if final_severity == "LOW" and zabbix_severity not in ["Not Set", "Information", "LOW"]:
        final_severity = zabbix_severity

    return {
        "prediction": "ANOMALY" if (is_ai_anomaly or final_severity != "LOW") else "NORMAL",
        "severity": final_severity,
        "issues": analysis.get("issues", []),
        "anomaly_score": anomaly_score
    }

def get_recommendation(prediction_result, alert=None):
    if HAKIM_AVAILABLE:
        return hakim_recommend(prediction_result)
    return ["General Audit: Investigate the suspicious activity in Zabbix."]