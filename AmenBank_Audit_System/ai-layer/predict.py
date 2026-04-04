import os
import joblib
import pandas as pd
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import config

from src.data_loader import load_dataset
from src.preprocessing import preprocess
from src.model import detect_anomalies
from src.analyzer import analyze_row
from src.recommender import recommend

# --- SOC STYLING ---
BG_COLOR = "#0b0f19"
ACCENT_RED = "#ff3333"
ACCENT_BLUE = "#00d4ff"
NORMAL_GREEN = "#2ecc71"
TEXT_COLOR = "#e0e0e0"

def run_advanced_audit():
    print("🚀 INITIALIZING AMEN BANK SOC COMMAND CENTER...")
    plt.style.use('dark_background')

    if not os.path.exists(config.MODEL_PATH):
        print("❌ Error: Run train_model.py first!")
        return

    model = joblib.load(config.MODEL_PATH)
    df = load_dataset(config.DATA_PATH)
    features = preprocess(df)

    # 1. AI EXECUTION
    results = detect_anomalies(model, features.copy())
    results["anomaly_score"] = model.decision_function(features)
    results["risk_level"] = results["anomaly_score"].apply(lambda x: min(100, max(0, (0.5 - x) * 100)))

    for col in df.columns:
        if col not in results.columns:
            results[col] = df[col]

    anomalies = results[results["anomaly"] == -1].copy()
    anomalies = anomalies.sort_values(by="risk_level", ascending=False)
    anomalies.to_csv(config.LOG_PATH, index=False)

    # 2. VISUALIZATION
    fig, axes = plt.subplots(6, 1, figsize=(16, 26), facecolor=BG_COLOR)
    fig.subplots_adjust(right=0.75, hspace=0.45, top=0.92)

    # Header KPIs
    health = 100 - (len(anomalies)/len(results)*100)
    kpi_text = f"TOTAL LOGS: {len(results):,}  |  THREATS: {len(anomalies)}  |  HEALTH: {health:.2f}%"
    fig.text(0.5, 0.94, kpi_text, color=ACCENT_BLUE, fontsize=14, ha='center', fontweight='bold', family='monospace')

    for i, metric in enumerate(config.METRICS):
        ax = axes[i]
        ax.set_facecolor(BG_COLOR)
        ax.scatter(results.index, results[metric], c=NORMAL_GREEN, s=2, alpha=0.08)
        ax.scatter(anomalies.index, anomalies[metric], c=ACCENT_RED, s=22, edgecolors='white', linewidths=0.2)
        ax.set_ylabel(metric.upper().replace('_', ' '), color=ACCENT_BLUE, fontweight='bold', fontsize=9)
        ax.grid(True, color='#1c212b', linestyle=':', alpha=0.3)

    ax_risk = axes[4]
    ax_risk.set_facecolor(BG_COLOR)
    ax_risk.fill_between(results.index, results["risk_level"], color=ACCENT_RED, alpha=0.25)
    ax_risk.plot(results["risk_level"], color=ACCENT_RED, linewidth=0.7)
    ax_risk.set_ylabel("RISK LEVEL %", color=ACCENT_RED, fontweight='bold')
    ax_risk.set_ylim(0, 100)
    axes[5].axis('off')

    # 3. INTELLIGENT SIDEBAR
    if not anomalies.empty:
        top_threat = anomalies.iloc[0]
        analysis = analyze_row(top_threat, results)
        actions = recommend(analysis)

        diagnosis_txt = "\n".join([f" - {iss}" for iss in analysis["issues"]])
        protocol_txt = "\n".join([f" >> {rec}" for rec in actions])

        sidebar = (
            f" [!] SECURITY AUDIT REPORT\n"
            f" ━━━━━━━━━━━━━━━━━━━━━━\n"
            f" STATUS   : {analysis['severity']}\n"
            f" MAX RISK : {top_threat['risk_level']:.1f}%\n"
            f" ━━━━━━━━━━━━━━━━━━━━━━\n"
            f" DIAGNOSIS:\n{diagnosis_txt}\n\n"
            f" PROTOCOL:\n{protocol_txt}\n"
            f" ━━━━━━━━━━━━━━━━━━━━━━\n"
            f" TARGET   : AMEN BANK PROD"
        )
        fig.text(0.77, 0.5, sidebar, fontsize=11, family='monospace', color=TEXT_COLOR,
                 bbox=dict(facecolor='#0d1117', edgecolor=ACCENT_RED, boxstyle='round,pad=1.2'))

    plt.suptitle("AMEN BANK | INTELLIGENT THREAT DETECTION SYSTEM", color=TEXT_COLOR, fontsize=24, fontweight='bold', y=0.97)
    plt.savefig(config.REPORT_PATH, dpi=160, facecolor=fig.get_facecolor())
    print(f"✅ SUCCESS: High-Contrast Dashboard saved at {config.REPORT_PATH}")

if __name__ == "__main__":
    run_advanced_audit()