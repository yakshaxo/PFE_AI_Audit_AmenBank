import pandas as pd
import numpy as np
import os

# --- AUTO-CREATE FOLDERS ---
os.makedirs("data/raw", exist_ok=True)

def generate_banking_dataset(n_samples=50000):
    np.random.seed(42)
    print(f"--- AMEN BANK DATA GENERATOR ---")
    print(f"Creating {n_samples} records with 8 Monitoring Metrics...")

    # 1. NORMAL BEHAVIOR (Baseline)
    # We initialize everything as float to prevent "LossySetitemError"
    data = pd.DataFrame({
        "cpu_usage": np.random.normal(45, 10, n_samples),
        "memory_usage": np.random.normal(60, 8, n_samples),
        "disk_io": np.random.normal(250, 60, n_samples),
        "network_traffic": np.random.normal(700, 180, n_samples),
        "db_connections": np.random.normal(150, 30, n_samples).astype(float),
        "failed_logins": np.random.poisson(1, n_samples).astype(float), 
        "response_time": np.random.normal(120, 25, n_samples),
        "thread_count": np.random.normal(80, 10, n_samples)
    })

    # 2. INJECT ANOMALIES (2% - Cyber Attacks & Crashes)
    anomaly_count = int(n_samples * 0.02)
    indices = np.random.choice(n_samples, anomaly_count, replace=False)

    # Scenario A: Infrastructure Crash
    data.loc[indices[:anomaly_count//2], ["cpu_usage", "memory_usage"]] += 50
    
    # Scenario B: Security Brute Force
    data.loc[indices, "failed_logins"] = np.random.randint(60, 200, anomaly_count)
    
    # Scenario C: Database Stress
    data.loc[indices, "db_connections"] = np.random.randint(700, 1200, anomaly_count)
    
    # Scenario D: Network Latency
    data.loc[indices, "response_time"] = np.random.uniform(3000, 6000, anomaly_count)

    # Labeling
    data["label"] = 1
    data.loc[~data.index.isin(indices), "label"] = 0

    # 3. SAVE
    path = "data/raw/monitoring_dataset.csv"
    data.to_csv(path, index=False)
    print(f"✅ SUCCESS: Dataset saved at {os.path.abspath(path)}")

if __name__ == "__main__":
    generate_banking_dataset()