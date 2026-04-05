# src/analyzer.py

def analyze_row(row, df):
    issues = []
     
     
    if row['cpu_usage'] > df['cpu_usage'].mean() + (2 * df['cpu_usage'].std()):
        issues.append("Critical CPU saturation")
        
    if row['memory_usage'] > df['memory_usage'].mean() + (2 * df['memory_usage'].std()):
        issues.append("Memory leak suspected")
        
    if row['network_traffic'] > df['network_traffic'].mean() + (2 * df['network_traffic'].std()):
        issues.append("Inbound traffic spike (DDoS)")

    severity = "LOW"
    if len(issues) == 1: severity = "MEDIUM"
    if len(issues) >= 2: severity = "CRITICAL"

    return {
        "severity": severity,
        "issues": issues if issues else ["Complex behavioral anomaly"],
        "is_correlated": len(issues) > 1
    }