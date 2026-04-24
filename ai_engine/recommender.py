def recommend(analysis):
    recommendations = []
    text = " ".join(analysis["issues"]).upper()

    if "LOGINS" in text:
        recommendations.append("SOC ALERT: Unauthorized access attempt. Immediately isolate source IP and verify LDAP/Active Directory audit logs for brute-force patterns.")
    
    if "DB" in text:
        recommendations.append("INTEGRITY RISK: Database performance anomaly. Terminate idle sessions and check for deadlocks to prevent transaction timeout in core banking services.")
    
    if "RESPONSE" in text or "LATENCY" in text:
        recommendations.append("COMPLIANCE WARNING: High latency detected in App Layer. Investigate backend service health to ensure adherence to SLA transaction speed requirements.")
    
    if "CPU" in text:
        recommendations.append("AUDIT REQUIRED: CPU saturation anomaly. Verify transaction core integrity and check for unauthorized background processes (cryptojacking/malware risk).")
    
    if "MEMORY" in text:
        recommendations.append("RESOURCE RISK: Memory leak detected in application pool. Monitor Java heap space immediately to prevent transaction queue drops.")
    
    if not recommendations:
        recommendations.append("GENERAL AUDIT: System behavior outside normal baseline. Review full system logs via Zabbix for subtle persistent threats.")
        
    return recommendations