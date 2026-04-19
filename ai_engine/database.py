import psycopg2
import os
import logging
import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("uvicorn")

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'pfe_postgres'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('AI_DB_NAME', 'ai_audit'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        connect_timeout=5
    )
def fetch_unique_hosts():
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
        if conn:
            conn.close()

def fetch_audit_summary():
    """Calculates summary statistics for the dashboard."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_results")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ai_results WHERE severity = 'CRITICAL'")
        critical = cur.fetchone()[0]
        return {"total": total, "critical": critical}
    except Exception as e:
        logger.error(f"Error fetching audit summary: {e}")
        return {"total": 0, "critical": 0}
    finally:
        if conn:
            conn.close()

def to_pg_array(value):
    """
    Converts a string or list to a proper PostgreSQL TEXT[] array.
    PostgreSQL expects: {"item1", "item2"} format.
    """
    if isinstance(value, list):
        # Already a list — clean each item
        items = [str(i).replace('"', '\\"') for i in value]
    elif isinstance(value, str):
        # Single string — wrap in list
        items = [value.replace('"', '\\"')]
    else:
        items = [str(value)]
    
    return '{' + ','.join(f'"{item}"' for item in items) + '}'

def save_audit_result(host, prediction, severity, score, issues, recommendations):
    """Persists AI analysis results using explicit array casting for PostgreSQL."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # SQL query using ARRAY constructor to match the _text type
        query = """
            INSERT INTO ai_results (host, prediction, severity, score, issues, recommendations, timestamp)
            VALUES (%s, %s, %s, %s, ARRAY[%s]::TEXT[], ARRAY[%s]::TEXT[], %s)
        """
        
        # Ensure we pass strings that the ARRAY constructor will wrap
        iss_val = issues[0] if isinstance(issues, list) else str(issues)
        rec_val = recommendations[0] if isinstance(recommendations, list) else str(recommendations)

        cur.execute(query, (
            str(host),
            str(prediction),
            str(severity),
            float(score),
            iss_val,
            rec_val,
            datetime.datetime.now()
        ))
        conn.commit()
        logger.info(f"✅ Record Saved: {host}")
    except Exception as e:
        logger.error(f"❌ Persistence Error: {e}")
    finally:
        if conn:
            conn.close()