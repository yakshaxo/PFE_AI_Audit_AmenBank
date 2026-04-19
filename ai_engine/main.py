import os
import bcrypt
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import logging

from database import get_db_connection, fetch_unique_hosts
from auth import verify_password
from ai_engine import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI(title="Sentinella Audit")

base_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

class AuditPayload(BaseModel):
    host: str
    value: float
    item_key: Optional[str] = "system.cpu.util"
    severity: Optional[str] = "Not Set"

@app.on_event("startup")
async def startup_event():
    logger.info("--- Initializing Sentinella Audit System ---")
    
    # 1. Database Connection Check
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        logger.info("✅ Data Persistence: Ready")
    except Exception as e:
        logger.error(f"❌ Data Persistence: Failed! Error: {e}")

    # 2. Machine Learning Model Loading (Added Loggers)
    try:
        logger.info("🧠 ML Model: Attempting to load neural weights...")
        engine.load_brain() 
        logger.info("✅ AI Model: Loaded and brain is ready for analysis")
    except Exception as e:
        logger.error(f"❌ AI Model: Critical Failure during loading! Error: {e}")

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        logger.info(f"🔍 Attempting login for user: {username}")
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT password, roleid FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        conn.close()

        if not user:
            logger.warning(f"❌ Login failed: User '{username}' not found.")
        else:
            if verify_password(password, user[0]):
                logger.info(f"✅ Login successful for {username}. RoleID: {user[1]}")
                role_path = "admin" if str(user[1]) == "1" else "user"
                return RedirectResponse(url=f"/{role_path}_dashboard", status_code=303)
            else:
                logger.warning(f"❌ Login failed: Incorrect password for user '{username}'.")

        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials. Please try again."
        })
    except Exception as e:
        logger.error(f"🔥 Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "System error during login."
        })

@app.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_view(request: Request):
    hosts = fetch_unique_hosts()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "hosts": hosts})

@app.get("/user_dashboard", response_class=HTMLResponse)
async def user_view(request: Request):
    hosts = fetch_unique_hosts()
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "hosts": hosts})

@app.post("/analyze")
async def api_analyze(data: AuditPayload):
    result = engine.analyze_and_store(
        data.host,
        data.value,
        data.item_key,
        data.severity
    )
    return {
        "host": data.host,
        "prediction": result.get("prediction"),
        "score": result.get("score"),
        "recommendations": result.get("recommendations")
    }

@app.get("/logout")
async def logout():
    return RedirectResponse(url="/")

@app.post("/admin/create-user")
async def create_user_api(username: str = Form(...), password: str = Form(...), roleid: int = Form(...)):
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password, roleid) VALUES (%s, %s, %s)",
            (username, hashed_pw, roleid)
        )
        conn.commit()
        conn.close()
        return {"message": f"User {username} created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))