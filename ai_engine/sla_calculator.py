import psycopg2

# Zabbix database config
ZABBIX_DB = {
    'host': 'postgres',  
    'port': 5432,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'StrongPassword123'
}


def calculate_sla(host: str, days: int = 30) -> dict:
    """
    Calculate server uptime SLA from Zabbix database.

    Returns:
    {
        "host": "louay-pc",
        "period_days": 30,
        "uptime_percentage": 99.87,
        "total_downtime_minutes": 56.0,
        "incidents": 3,
        "sla_status": "GOOD"
    }
    """
    try:
        conn = psycopg2.connect(**ZABBIX_DB)
        cur = conn.cursor()

        # Query agent.ping history for the host
        query = """
            SELECT
                AVG(CASE WHEN h.value = 1 THEN 1.0 ELSE 0.0 END) * 100 AS uptime_pct,
                COUNT(CASE WHEN h.value = 0 THEN 1 END) AS incidents
            FROM history_uint h
            JOIN items i ON h.itemid = i.itemid
            JOIN hosts ho ON i.hostid = ho.hostid
            WHERE ho.host = %s
              AND i.key_ LIKE 'agent.ping%%'
              AND h.clock > EXTRACT(epoch FROM NOW() - INTERVAL '1 day' * %s)
        """

        cur.execute(query, (host, days))
        result = cur.fetchone()
        cur.close()
        conn.close()

        uptime_pct = float(result[0]) if result[0] is not None else 100.0
        incidents = int(result[1]) if result[1] is not None else 0
        downtime_minutes = round((100 - uptime_pct) * days * 24 * 60 / 100, 2)

        return {
            "host": host,
            "period_days": days,
            "uptime_percentage": round(uptime_pct, 2),
            "total_downtime_minutes": downtime_minutes,
            "incidents": incidents,
            "sla_status": "GOOD" if uptime_pct >= 99.5 else "POOR"
        }

    except Exception as e:
        # Return safe defaults if DB query fails
        return {
            "host": host,
            "period_days": days,
            "uptime_percentage": 0.0,
            "total_downtime_minutes": 0.0,
            "incidents": 0,
            "sla_status": "UNKNOWN",
            "error": str(e)
        }