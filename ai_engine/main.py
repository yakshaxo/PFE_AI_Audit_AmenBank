import os
import sys
import bcrypt
import logging
import io
import pandas as pd
from datetime import datetime
from typing import Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware 
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware # ADDED: For Nginx support
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from database import purge_old_ai_results

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

# ── 3. APP SETUP & PROFESSIONAL ERROR HANDLING ──────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Initialize background scheduler
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- NEXUS SYSTEM STARTING ---")
    try:
        engine.load_brain()
        logger.info("AI Brain: Ready")
    except Exception as e:
        logger.error(f"Brain Failed: {e}")
        
    # --- DATA RETENTION CONFIGURATION ---
    try:
        # Scheduled job runs every 24 hours to delete results older than 30 days
        scheduler.add_job(purge_old_ai_results, 'interval', hours=24, args=[30])
        scheduler.start()
        logger.info("Data Retention Scheduler: Active (30-day rolling window)")
    except Exception as e:
        logger.error(f"Failed to start Data Retention Scheduler: {e}")
        
    yield
    
    logger.info("--- NEXUS SYSTEM SHUTTING DOWN ---")
    try:
        scheduler.shutdown()
        logger.info("Data Retention Scheduler: Stopped cleanly")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

is_debug = os.getenv("DEBUG", "False").lower() == "true"
app = FastAPI(title="NEXUS Intelligence System", lifespan=lifespan, debug=is_debug)

# FIX: Added ProxyHeadersMiddleware to stop the redirect loop
# This tells FastAPI to trust the 'X-Forwarded-Proto' header from Nginx
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# --- ANTI-CACHING MIDDLEWARE ---
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Implement Secure Signed Sessions
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "fallback-secret-key-change-me"),
    session_cookie="nexus_session",
    max_age=1800, 
    same_site=os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower(),
    https_only=os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
)

templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        logger.warning(f"404 Not Found Accessed: {request.url}")
        try:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        except:
            return HTMLResponse("<h1>404 - Not Found</h1>", status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"status": "error", "message": str(exc.detail)})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal Server Error: {exc}")
    return JSONResponse(status_code=500, content={"status": "error", "message": "An internal system error occurred. Please contact the administrator."})

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

# ── 5. SECURITY DEPENDENCIES ────────────────────────────────
API_KEY_CREDENTIAL = os.getenv("INTERNAL_API_KEY", "amen-bank-secure-key-2026")

def get_current_user(request: Request):
    user = request.session.get("nexus_user")
    role = str(request.session.get("nexus_role")).strip() if request.session.get("nexus_role") else None
    return {"username": user, "role": role}

def verify_logged_in(request: Request):
    u = get_current_user(request)
    if not u["username"]:
        raise HTTPException(status_code=401, detail="Authentication required")
    return u

def verify_admin(request: Request):
    u = get_current_user(request)
    if not u["username"] or u["role"] != "1":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return u

def verify_machine_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY_CREDENTIAL:
        raise HTTPException(status_code=403, detail="Invalid Machine API Key")
    return x_api_key

# ── 6. AUTH & UI ROUTES ─────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    u = get_current_user(request)
    if u["username"]:
        return RedirectResponse(url="/admin_dashboard" if u["role"] == "1" else "/user_dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request):
    form     = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))

    if not username or not password:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Username and password are required."})

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT passwd, roleid FROM users WHERE username ILIKE %s", (username,))
    row = cur.fetchone()
    conn.close()

    if not row or not verify_password(password, str(row[0])):
        logger.warning(f"LOGIN FAIL: wrong credentials for '{username}'")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password."})

    role_id = str(row[1]).strip()
    logger.info(f"LOGIN OK: '{username}' role={role_id}")
    
    request.session["nexus_user"] = username
    request.session["nexus_role"] = role_id

    dest = "/admin_dashboard" if role_id == "1" else "/user_dashboard"
    resp = RedirectResponse(url=dest, status_code=303)
    resp.delete_cookie("nexus_user")
    resp.delete_cookie("nexus_role")
    return resp

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("nexus_user")
    resp.delete_cookie("nexus_role")
    return resp

@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_view(request: Request):
    u = get_current_user(request)
    if not u["username"] or u["role"] != "1":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "hosts": fetch_unique_hosts(), 
        "users": fetch_all_users(), "username": u["username"]
    })

@app.get("/user_dashboard", response_class=HTMLResponse)
async def user_view(request: Request):
    u = get_current_user(request)
    if not u["username"] or u["role"] != "2":
        if u["role"] == "1":
            return RedirectResponse(url="/admin_dashboard", status_code=303)
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("user_dashboard.html", {
        "request": request, "hosts": fetch_unique_hosts(), "username": u["username"]
    })

# ── 7. PROTECTED API ENDPOINTS ──────────────────────────────

@app.post("/admin/create-user")
async def create_user(request: Request, u=Depends(verify_admin)):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    email = str(form.get("email", "")).strip() or None
    password = str(form.get("password", ""))
    roleid = int(form.get("roleid", 2))

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, email, passwd, roleid) VALUES (%s,%s,%s,%s)", (username, email, hashed, roleid))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin_dashboard", status_code=303)

@app.get("/api/summary")
async def get_summary(u=Depends(verify_logged_in)):
    s = fetch_audit_summary()
    return {"total": s.get("total", 0), "critical": s.get("critical", 0), "hosts": len(fetch_unique_hosts())}

@app.get("/api/logs")
async def get_logs(limit: int = 100, u=Depends(verify_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, host, prediction, severity, score, issues, recommendations, timestamp FROM ai_results ORDER BY timestamp DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "host": r[1], "prediction": r[2], "severity": r[3], "score": r[4], "issues": r[5], "recommendations": r[6], "timestamp": str(r[7])} for r in rows]

@app.get("/api/host/{host}")
async def get_host_data(host: str, u=Depends(verify_logged_in)):
    return {"stats": fetch_host_stats(host), "logs": fetch_host_logs(host, limit=20)}

@app.get("/api/anomalies")
async def get_anomalies(limit: int = 30, u=Depends(verify_logged_in)):
    return fetch_recent_anomalies(limit)

@app.get("/api/sla/{host}")
async def get_sla(host: str, days: int = 30, u=Depends(verify_logged_in)):
    return calculate_sla(host, days)

@app.post("/api/flag")
async def create_flag(payload: FlagPayload, u=Depends(verify_logged_in)):
    save_flag(payload.audit_id, payload.username, payload.reason)
    return {"status": "success", "message": "Flagged. Admin will review."}

@app.get("/api/flags")
async def get_flags(u=Depends(verify_admin)):
    return fetch_pending_flags()

@app.post("/api/flag/{flag_id}/{action}")
async def resolve_item(flag_id: int, action: str, u=Depends(verify_admin)):
    resolve_flag(flag_id, action)
    return {"status": "success", "action": action}

@app.get("/api/download-report")
async def download_report(u=Depends(verify_logged_in)):
    t, c, p = get_zabbix_stats()
    filename = generate_pdf(t, c, p, get_ai_stats(), get_sla_stats())
    return FileResponse(path=filename, filename=f"NEXUS_Report_{datetime.now().strftime('%Y%m%d')}.pdf", media_type="application/pdf")

@app.get("/api/export/csv")
async def export_csv(type: str = "all", u=Depends(verify_admin)):
    conn = get_db_connection()
    query = "SELECT * FROM ai_results WHERE prediction='ANOMALY'" if type == "anomalies" else "SELECT * FROM ai_results"
    df = pd.read_sql(query, conn)
    conn.close()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=NEXUS_Data.csv"})

# ── 8. MACHINE API ──────────────────────────────────────────
@app.post("/analyze", dependencies=[Depends(verify_machine_key)])
async def api_analyze(data: AuditPayload):
    result = engine.analyze_and_store(data.host, data.value, data.item_key, data.severity)
    return {**data.dict(), **result}

@app.post("/webhook", dependencies=[Depends(verify_machine_key)])
async def webhook(data: AuditPayload):
    return await api_analyze(data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=False)