import pandas as pd
import joblib
import os
import numpy as np
import sys

# Setup paths for Hakim's modules
sys.path.append(os.path.dirname(__file__))

try:
    from analyzer import analyze_row
    from recommender import recommend as hakim_recommend
    HAKIM_AVAILABLE = True
except ImportError:
    HAKIM_AVAILABLE = False 
    print("WARNING: Technical modules (analyzer/recommender) missing. Using AI Fallback.")

# --- 1. Create a Synthetic Baseline ---
# Since we don't have the CSV, we create a 'Normal' reference for the math in analyzer.py
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
    # Create the data format expected by both the Model and the Analyzer
    row = pd.Series({
        'cpu_usage': value if 'cpu' in item_key.lower() else 30,
        'memory_usage': value if 'memory' in item_key.lower() else 40,
        'network_traffic': value if 'network' in item_key.lower() else 100,
    })

    # --- ACTION 1: CALL THE ML MODEL ---
    # We convert the row to a DataFrame for the model
    input_df = pd.DataFrame([row])
    
    try:
        # Most anomaly models return -1 for anomaly, 1 for normal
        model_prediction = model.predict(input_df)[0]
        is_ai_anomaly = (model_prediction == -1)
    except Exception as e:
        print(f"Model prediction failed: {e}")
        is_ai_anomaly = value > 90 # Basic fallback if model fails

    # --- ACTION 2: CALL THE ANALYZER (Statistical Check) ---
    if HAKIM_AVAILABLE:
        # We pass our baseline_df so the math doesn't crash
        analysis = analyze_row(row, baseline_df)
    else:
        analysis = {"severity": "LOW", "issues": ["AI detected pattern"], "is_correlated": False}

    # Merge AI intelligence with the Statistical results
    return {
        "prediction": "ANOMALY" if (is_ai_anomaly or analysis['severity'] != "LOW") else "NORMAL",
        "severity": "CRITICAL" if is_ai_anomaly else analysis['severity'],
        "issues": analysis.get("issues", []),
        "anomaly_score": 0.95 if is_ai_anomaly else 0.10
    }

def get_recommendation(prediction_result, alert=None):
    """Uses the recommender logic to give advice"""
    if HAKIM_AVAILABLE:
        return hakim_recommend(prediction_result)
    return ["General Audit: Investigate the suspicious activity in Zabbix."]
