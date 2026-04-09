import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
import os

np.random.seed(42)

# --- Normal operating data ---
# Simulates a healthy server: CPU 20-60%, memory 30-70%, disk 10-40%, network 50-200
n_normal = 1000
normal_data = pd.DataFrame({
    'cpu':     np.random.normal(35, 10, n_normal).clip(5, 70),
    'memory':  np.random.normal(50, 12, n_normal).clip(10, 80),
    'disk':    np.random.normal(25,  8, n_normal).clip(5, 50),
    'network': np.random.normal(120, 40, n_normal).clip(20, 250),
})

# --- Anomalous data (small portion) ---
n_anomaly = 50
anomaly_data = pd.DataFrame({
    'cpu':     np.random.uniform(85, 100, n_anomaly),   # very high CPU
    'memory':  np.random.uniform(85, 100, n_anomaly),   # very high memory
    'disk':    np.random.uniform(80, 100, n_anomaly),   # very high disk
    'network': np.random.uniform(500, 1000, n_anomaly), # traffic spike
})

# Combine and shuffle
df = pd.concat([normal_data, anomaly_data], ignore_index=True).sample(frac=1, random_state=42)

# Column order MUST match what adapter.py sends: ['cpu', 'memory', 'disk', 'network']
feature_columns = ['cpu', 'memory', 'disk', 'network']
X = df[feature_columns]

# Train Isolation Forest
# contamination=0.05 means ~5% of data expected to be anomalies
model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42,
    max_samples='auto'
)
model.fit(X)

# Verify on known normal value (cpu=30 should be NORMAL)
test_normal = pd.DataFrame([[30, 50, 25, 120]], columns=feature_columns)
test_anomaly = pd.DataFrame([[95, 90, 85, 800]], columns=feature_columns)

print("Test normal (cpu=30):", "NORMAL" if model.predict(test_normal)[0] == 1 else "ANOMALY")
print("Test anomaly (cpu=95):", "NORMAL" if model.predict(test_anomaly)[0] == 1 else "ANOMALY")
print("Offset:", model.offset_)
print("Contamination:", model.contamination)

# Save model
models_dir = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(models_dir, exist_ok=True)
model_path = os.path.join(models_dir, 'model.joblib')
joblib.dump(model, model_path)
print(f"\nModel saved to {model_path}")