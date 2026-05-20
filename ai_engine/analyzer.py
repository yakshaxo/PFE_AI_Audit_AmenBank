
def analyze_row(row, df):
    issues = []
    
    # 1. Statistical Checks
    if row['cpu_usage'] > df['cpu_usage'].mean() + (2 * df['cpu_usage'].std()):
        issues.append("Critical CPU saturation")
    if row['memory_usage'] > df['memory_usage'].mean() + (2 * df['memory_usage'].std()):
        issues.append("Memory leak suspected")
    if row['network_traffic'] > df['network_traffic'].mean() + (2 * df['network_traffic'].std()):
        issues.append("Network congestion detected")

    # 2. INTENSITY CHECK (The Fix)
    # We force CRITICAL if any value is dangerously high, regardless of the issue count
    is_extreme = row['cpu_usage'] > 90 or row['memory_usage'] > 90 or row['network_traffic'] > 500
    
    cpu_val = row.get('cpu_usage', 0)
    
    severity = "LOW"
    if len(issues) >= 2 or cpu_val > 90:
        severity = "CRITICAL"
    elif len(issues) == 1:
        severity = "MEDIUM"

    return {
        "severity": severity,
        "issues": issues if issues else ["Complex behavioral anomaly"]
    }