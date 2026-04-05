def recommend(analysis):
    recommendations = []
    text = " ".join(analysis["issues"]).upper()

    if "LOGINS" in text:
        recommendations.append("Firewall: Immediately block source IPs and verify LDAP/Active Directory logs.")
    if "DB" in text:
        recommendations.append("Database: Kill long-running idle sessions and check for deadlocks.")
    if "RESPONSE" in text or "LATENCY" in text:
        recommendations.append("App Layer: Check load balancer distribution and investigate backend service health.")
    if "CPU" in text or "MEMORY" in text:
        recommendations.append("Infrastructure: Investigate for rogue processes or consider horizontal scaling.")
    
    if not recommendations:
        recommendations.append("General Audit: Review the full system logs via Zabbix for subtle patterns.")
        
    return recommendations