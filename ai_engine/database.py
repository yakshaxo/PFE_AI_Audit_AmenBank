import psycopg2
import os
import logging
import datetime
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger("uvicorn")

def get_db_connection():
    """Establishes a connection to the PostgreSQL ai_audit database."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'pfe_postgres'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('AI_DB_NAME', 'ai_audit'),
        user=os.getenv('POSTGRES_USER', 'zabbix'),
        password=os.getenv('POSTGRES_PASSWORD', 'StrongPassword123'), 
        connect_timeout=5
    )

# --- EXISTING CORE FUNCTIONS ---

def fetch_unique_hosts():
    """Fetches unique hostnames for dashboard filtering."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT host FROM ai_results ORDER BY host ASC")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching hosts: {e}")
        return []
    finally:
        if conn: conn.close()

def fetch_all_users():
    """Fetches user list for Admin Management."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username, roleid, email FROM users ORDER BY username ASC")
        return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []
    finally:
        if conn: conn.close()

def fetch_audit_summary():
    """Calculates top-level stats for overview cards."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_results")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ai_results WHERE prediction = 'ANOMALY'")
        critical = cur.fetchone()[0]
        return {"total": total, "critical": critical}
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return {"total": 0, "critical": 0}
    finally:
        if conn: conn.close()

def save_audit_result(host, prediction, severity, score, issues, recommendations):
    """Persists AI analysis results into the audit trail[cite: 71, 72]."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO ai_results (host, prediction, severity, score, issues, recommendations, timestamp)
            VALUES (%s, %s, %s, %s, ARRAY[%s]::TEXT[], ARRAY[%s]::TEXT[], %s)
        """
        iss_val = issues[0] if isinstance(issues, list) else str(issues)
        rec_val = recommendations[0] if isinstance(recommendations, list) else str(recommendations)

        cur.execute(query, (
            str(host), str(prediction), str(severity), float(score),
            iss_val, rec_val, datetime.datetime.now()
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ DB Save Error: {e}")
    finally:
        if conn: conn.close()

# --- NEW: ANALYST & MONITORING FUNCTIONS  ---

def fetch_host_stats(host):
    """Calculates health metrics for a specific host."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                COUNT(*) as total_audits,
                COUNT(*) FILTER (WHERE prediction = 'ANOMALY') as anomaly_count,
                (SELECT prediction FROM ai_results WHERE host = %s ORDER BY timestamp DESC LIMIT 1) as last_status
            FROM ai_results WHERE host = %s
        """, (host, host))
        return cur.fetchone()
    except Exception as e:
        logger.error(f"Error fetching host stats: {e}")
        return {"total_audits": 0, "anomaly_count": 0, "last_status": "UNKNOWN"}
    finally:
        if conn: conn.close()

def fetch_host_logs(host, limit=20):
    """Fetches recent activity for a specific host[cite: 30, 82]."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, timestamp, prediction, severity, score, issues 
            FROM ai_results WHERE host = %s ORDER BY timestamp DESC LIMIT %s
        """, (host, limit))
        return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching host logs: {e}")
        return []
    finally:
        if conn: conn.close()

def fetch_recent_anomalies(limit=30):
    """Powers the cross-host Anomaly Feed[cite: 31, 82]."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, timestamp, host, severity, score, issues, recommendations
            FROM ai_results WHERE prediction = 'ANOMALY' 
            ORDER BY timestamp DESC LIMIT %s
        """, (limit,))
        return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        return []
    finally:
        if conn: conn.close()

# --- NEW: HUMAN-IN-THE-LOOP FLAGGING [cite: 12, 76] ---

def save_flag(audit_id, username, reason):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
            INSERT INTO flags (audit_id, username, reason, flagged_at, status)
            VALUES (%s, %s, %s, NOW(), 'pending')
        """
        cur.execute(query, (audit_id, username, reason))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving flag: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def fetch_pending_flags():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # We use array_to_string to convert the 'issues' array into a single text block
    query = """
        SELECT 
            f.id, 
            f.audit_id, 
            f.username, 
            f.reason, 
            f.flagged_at, 
            a.host, 
            array_to_string(a.issues, ', ') AS logs 
        FROM flags f
        JOIN ai_results a ON f.audit_id = a.id
        WHERE f.status = 'pending'
        ORDER BY f.flagged_at DESC
    """
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
        flags = []
        for row in rows:
            flags.append({
                "id": row[0],
                "audit_id": row[1],
                "username": row[2],
                "reason": row[3],
                "flagged_at": row[4],
                "host": row[5],
                "logs": row[6]  # This now contains the joined 'issues'
            })
        return flags
    finally:
        cur.close()
        conn.close()


        
def resolve_flag(flag_id, status='resolved'):
    """
    Updates the status of a user-submitted flag.
    Typically changes 'pending' to 'resolved' or 'dismissed'.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "UPDATE flags SET status = %s WHERE id = %s"
        cur.execute(query, (status, flag_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error resolving flag {flag_id}: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()
        
def purge_old_ai_results(days_to_keep=30):
    """Data Retention Policy: Deletes historical predictions to manage storage footprint."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "DELETE FROM ai_results WHERE timestamp < NOW() - INTERVAL '%s days';"
        cur.execute(query, (days_to_keep,))
        conn.commit()
        logger.info(f"Database Maintenance: Purged AI results older than {days_to_keep} days.")
    except Exception as e:
        logger.error(f"Database Maintenance Error: Purge routine failed: {e}")
    finally:
        if conn:
            conn.close()