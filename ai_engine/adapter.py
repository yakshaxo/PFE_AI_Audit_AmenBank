import pandas as pd
import joblib
import os
import numpy as np
import sys
import logging

# Set up logging to match main.py
logger = logging.getLogger("AI-Engine")

# Setup paths for modules
sys.path.append(os.path.dirname(__file__))

try:
    from analyzer import analyze_row
    from recommender import recommend as hakim_recommend
    HAKIM_AVAILABLE = True
except ImportError:
    HAKIM_AVAILABLE = False
    print("WARNING: Technical modules (analyzer/recommender) missing. Using AI Fallback.")

# Synthetic baseline for statistical analysis
np.random.seed(42)
baseline_df = pd.DataFrame({
    'cpu_usage': np.random.normal(30, 10, 100),
    'memory_usage': np.random.normal(40, 15, 100),
    'network_traffic': np.random.normal(100, 50, 100)
})

def load_model():
    """Finds and loads the AI model (.pkl or .joblib)"""
    models_dir = os.path.join(os.path.dirname(__file__), 'models')
    possible_names = ['model.pkl', 'audit_model.joblib', 'model.joblib']

    for name in possible_names:
        path = os.path.join(models_dir, name)
        if os.path.exists(path):
            return joblib.load(path)

    raise FileNotFoundError(f"AI Model not found in {models_dir}")

def detect_anomaly(model, value: float, item_key: str) -> dict:
    """
    Main detection logic using the ML Model + Statistical Analyzer
    """
    # 1. Statistical row for analyzer (uses descriptive column names)
    row = pd.Series({
        'cpu_usage':       value if 'cpu'     in item_key.lower() else 30,
        'memory_usage':    value if 'memory'  in item_key.lower() else 40,
        'network_traffic': value if 'network' in item_key.lower() else 100,
    })

    # 2. ML Model input — order MUST match training: ['cpu', 'memory', 'disk', 'network']
    feature_order = ['cpu', 'memory', 'disk', 'network']
    model_data = [[
        value if 'cpu'     in item_key.lower() else 30,   # cpu
        value if 'memory'  in item_key.lower() else 40,   # memory
        30,                                                # disk (placeholder)
        value if 'network' in item_key.lower() else 100,  # network
    ]]

    model_input = pd.DataFrame(model_data, columns=feature_order)

    try:
        model_prediction = model.predict(model_input)[0]
        is_ai_anomaly = (model_prediction == -1)
        logger.info(f"AI Model Prediction for {item_key}: {'ANOMALY' if is_ai_anomaly else 'NORMAL'}")
    except Exception as e:
        logger.error(f"Model prediction failed: {e}")
        is_ai_anomaly = value > 90  # Fallback threshold

    # 3. Statistical analysis
    if HAKIM_AVAILABLE:
        analysis = analyze_row(row, baseline_df)
    else:
        analysis = {"severity": "LOW", "issues": ["AI Pattern Detected"], "is_correlated": False}

    return {
        "prediction":    "ANOMALY" if (is_ai_anomaly or analysis.get('severity') != "LOW") else "NORMAL",
        "severity":      "CRITICAL" if is_ai_anomaly else analysis.get('severity', 'LOW'),
        "issues":        analysis.get("issues", []),
        "anomaly_score": 0.95 if is_ai_anomaly else 0.10
    }

def get_recommendation(prediction_result, alert=None):
    """Uses the recommender logic to give advice"""
    if HAKIM_AVAILABLE:
        return hakim_recommend(prediction_result)
    return ["General Audit: Investigate the suspicious activity in Zabbix."]