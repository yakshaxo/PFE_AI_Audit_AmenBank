import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports/figures")
LOGS_DIR = os.path.join(BASE_DIR, "reports/logs")

for folder in [MODELS_DIR, REPORTS_DIR, LOGS_DIR]:
    os.makedirs(folder, exist_ok=True)

DATA_PATH = os.path.join(BASE_DIR, "data/raw/monitoring_dataset.csv")
MODEL_PATH = os.path.join(MODELS_DIR, "audit_model.joblib")
REPORT_PATH = os.path.join(REPORTS_DIR, "anomaly_dashboard.png")
LOG_PATH = os.path.join(LOGS_DIR, "critical_threats.csv")

CONTAMINATION = 0.02 
METRICS = ['cpu_usage', 'memory_usage', 'disk_io', 'network_traffic']