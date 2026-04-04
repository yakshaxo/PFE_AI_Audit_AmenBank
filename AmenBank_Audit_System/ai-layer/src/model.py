import os
import joblib
from sklearn.ensemble import IsolationForest
import config

def train_iforest(X):
    model = IsolationForest(
        n_estimators=200,
        contamination=config.CONTAMINATION,
        random_state=42,
        n_jobs=-1 
    )
    model.fit(X)
    return model

def detect_anomalies(model, data):
    df_results = data.copy()
    predictions = model.predict(data)
    df_results["anomaly"] = predictions
    return df_results