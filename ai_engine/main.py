import os
import sys
import bcrypt
import logging
import io
import pandas as pd
from datetime import datetime
from typing import Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# ── 1. PATH SETUP ───────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ── 2. MODULE IMPORTS ───────────────────────────────────────
from reports.generate_report import get_zabbix_stats, get_ai_stats, get_sla_stats, generate_pdf
from database import (
    get_db_connection, fetch_unique_hosts, fetch_all_users,
    fetch_audit_summary, save_flag, fetch_pending_flags,
    resolve_flag, fetch_host_stats, fetch_host_logs, fetch_recent_anomalies
)
from auth import verify_password
from ai_engine import engine
from sla_calculator import calculate_sla

# ── 3. APP SETUP ────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- NEXUS SYSTEM STARTING ---")
    try:
        engine.load_brain()
        logger.info("AI Brain: Ready")
    except Exception as e:
        logger.error(f"Brain Failed: {e}")
    yield

app = FastAPI(title="NEXUS Intelligence System", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# ── 4. DATA MODELS ──────────────────────────────────────────
class AuditPayload(BaseModel):
    host: str
    value: Optional[float] = 0.0
    item_key: Optional[str] = "system.cpu.util"
    severity: Optional[Union[str, int]] = "Not Set"

class FlagPayload(BaseModel):
    audit_id: int
    username: str
    reason: str

# ── HELPERS ─────────────────────────────────────────────────
def get_current_user(request: Request):
    return {
        "username": request.cookies.get("nexus_user"),
        "role":     request.cookies.get("nexus_role"),
    }

def require_admin(request: Request):
    u = get_current_user(request)
    return u if u["role"] == "1" else None

def require_login(request: Request):
    u = get_current_user(request)
    return u if u["username"] else None

# ── 5. AUTH ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    u = get_current_user(request)
    if u["username"]:
        return RedirectResponse(
            url="/admin_dashboard" if u["role"] == "1" else "/user_dashboard",
            status_code=302
        )
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request):
    form     = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))

    logger.info(f"LOGIN ATTEMPT: '{username}'")

    if not username or not password:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Username and password are required."
        })

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT passwd, roleid FROM users WHERE username ILIKE %s", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        logger.warning(f"LOGIN FAIL: '{username}' not found")
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Invalid username or password."
        })

    stored_hash = str(row[0])
    role_id     = str(row[1]).strip()

    if not verify_password(password, stored_hash):
        logger.warning(f"LOGIN FAIL: wrong password for '{username}'")
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Invalid username or password."
        })

    logger.info(f"LOGIN OK: '{username}' role={role_id}")
    dest = "/admin_dashboard" if role_id == "1" else "/user_dashboard"
    resp = RedirectResponse(url=dest, status_code=303)
    resp.set_cookie("nexus_user", username, httponly=True, samesite="lax")
    resp.set_cookie("nexus_role", role_id,  httponly=True, samesite="lax")
    return resp

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("nexus_user")
    resp.delete_cookie("nexus_role")
    return resp

# ── 6. PASSWORD RESET ────────────────────────────────────────

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_view(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})

@app.post("/api/reset-password")
async def handle_reset(request: Request):
    form         = await request.form()
    username     = str(form.get("username",     "")).strip()
    email        = str(form.get("email",        "")).strip()
    new_password = str(form.get("new_password", ""))

    if not all([username, email, new_password]):
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "All fields are required."
        })

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn   = get_db_connection()
    cur    = conn.cursor()
    cur.execute(
        "UPDATE users SET passwd=%s WHERE username ILIKE %s AND email ILIKE %s",
        (hashed, username, email)
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()

    if not updated:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "error": "No account found with that username and email."
        })
    return RedirectResponse(url="/login?msg=reset_success", status_code=303)

# ── 7. DASHBOARDS ────────────────────────────────────────────

@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_view(request: Request):
    u = require_admin(request)
    if not u:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "hosts":   fetch_unique_hosts(),
        "users":   fetch_all_users(),
        "username": u["username"],
    })

@app.get("/user_dashboard", response_class=HTMLResponse)
async def user_view(request: Request):
    u = require_login(request)
    if not u:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("user_dashboard.html", {
        "request":  request,
        "hosts":    fetch_unique_hosts(),
        "username": u["username"],
    })

# ── 8. USER MANAGEMENT ───────────────────────────────────────

@app.post("/admin/create-user")
async def create_user(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    form     = await request.form()
    username = str(form.get("username", "")).strip()
    # email is OPTIONAL — the HTML input has no required attribute
    email    = str(form.get("email",    "")).strip() or None
    password = str(form.get("password", ""))
    roleid   = int(form.get("roleid",   2))

    logger.info(f"CREATE USER: {username} role={roleid}")

    if not username or not password:
        return RedirectResponse(
            url="/admin_dashboard?error=missing_fields", status_code=303
        )

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, passwd, roleid) VALUES (%s,%s,%s,%s)",
            (username, email, hashed, roleid)
        )
        conn.commit()
        conn.close()
        logger.info(f"USER CREATED: {username}")
    except Exception as e:
        logger.error(f"CREATE USER FAIL: {e}")
        return RedirectResponse(
            url="/admin_dashboard?error=db_error", status_code=303
        )

    return RedirectResponse(url="/admin_dashboard", status_code=303)

# ── 9. AI / MONITORING APIs ──────────────────────────────────

@app.get("/api/summary")
async def get_summary():
    s = fetch_audit_summary()
    return {
        "total":    s.get("total",    0),
        "critical": s.get("critical", 0),
        "hosts":    len(fetch_unique_hosts()),
    }

@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Admin dashboard overview + logs panel."""
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, host, prediction, severity, score,
               issues, recommendations, timestamp
        FROM   ai_results
        ORDER  BY timestamp DESC
        LIMIT  %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id":              r[0],
            "host":            r[1],
            "prediction":      r[2],
            "severity":        r[3],
            "score":           r[4],
            "issues":          r[5],
            "recommendations": r[6],
            "timestamp":       str(r[7]),
        }
        for r in rows
    ]

@app.get("/api/host/{host}")
async def get_host_data(host: str):
    return {"stats": fetch_host_stats(host), "logs": fetch_host_logs(host, limit=20)}

@app.get("/api/anomalies")
async def get_anomalies(limit: int = 30):
    return fetch_recent_anomalies(limit)

@app.post("/analyze")
async def api_analyze(data: AuditPayload):
    result = engine.analyze_and_store(data.host, data.value, data.item_key, data.severity)
    return {**data.dict(), **result}

@app.post("/webhook")
async def webhook(data: AuditPayload):
    return await api_analyze(data)

# ── 10. SLA ──────────────────────────────────────────────────

@app.get("/api/sla/{host}")
async def get_sla(host: str, days: int = 30):
    return calculate_sla(host, days)

# ── 11. FLAGGING ─────────────────────────────────────────────

@app.post("/api/flag")
async def create_flag(payload: FlagPayload):
    """
    User sends: { audit_id, username, reason }
    Saved to flags table → appears in admin /api/flags
    """
    try:
        logger.info(f"FLAG ATTEMPT: audit_id={payload.audit_id} by {payload.username}")
        save_flag(payload.audit_id, payload.username, payload.reason)
        return {"status": "success", "message": "Flagged. Admin will review."}
    except Exception as e:
        logger.error(f"FLAG FAIL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/flags")
async def get_flags():
    """Admin inbox — returns all pending flags joined with audit data."""
    return fetch_pending_flags()

@app.post("/api/flag/{flag_id}/{action}")
async def resolve_item(flag_id: int, action: str):
    if action not in ["confirm", "dismiss"]:
        raise HTTPException(status_code=400, detail="Action must be confirm or dismiss")
    resolve_flag(flag_id, action)
    return {"status": "success", "action": action}

# ── 12. EXPORTS ──────────────────────────────────────────────

@app.get("/api/download-report")
async def download_report():
    try:
        t, c, p  = get_zabbix_stats()
        filename = generate_pdf(t, c, p, get_ai_stats(), get_sla_stats())
        return FileResponse(
            path=filename,
            filename=f"NEXUS_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            media_type="application/pdf",
        )
    except Exception as e:
        logger.error(f"PDF error: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

@app.get("/api/export/csv")
async def export_csv(type: str = "all"):
    conn  = get_db_connection()
    query = ("SELECT * FROM ai_results WHERE prediction='ANOMALY'"
             if type == "anomalies" else "SELECT * FROM ai_results")
    df    = pd.read_sql(query, conn)
    conn.close()
    buf   = io.StringIO()
    df.to_csv(buf, index=False)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=NEXUS_Data.csv"},
    )

# ── 13. DEV BACKDOOR (Fix Admin Password) ────────────────────

@app.get("/dev/fix-admin")
async def dev_fix_admin():
    """TEMPORARY ROUTE to fix password corruption caused by PowerShell."""
    try:
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET passwd=%s WHERE username='admin'", (hashed,))
        conn.commit()
        conn.close()
        logger.info("DEV: Admin password securely reset to 'admin123'")
        return {"status": "success", "message": "Admin password securely fixed to 'admin123'"}
    except Exception as e:
        logger.error(f"DEV FIX FAIL: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=False)