from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal, Alert, init_db



app = FastAPI()

# Initialize database tables
init_db()


# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "AI Chatbot is running"}

@app.api_route("/zabbix", methods=["GET", "POST"])
async def zabbix_alert(request: Request, db: Session = Depends(get_db)):
    if request.method == "POST":
        data = await request.json()

        print("ZABBIX ALERT RECEIVED:")
        print(data)

        alert = Alert(
            trigger=data.get("trigger", "unknown"),
            severity=data.get("severity", "unknown"),
            host=data.get("server", "unknown"),
            message=str(data)
        )

        db.add(alert)
        db.commit()

        return {"status": "saved"}

    return {"message": "Zabbix endpoint ready"}



@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.id.desc()).limit(20).all()

    return [
        {
            "id": a.id,
            "trigger": a.trigger,
            "severity": a.severity,
            "host": a.host,
            "message": a.message,
            "timestamp": a.timestamp,
        }
        for a in alerts
    ]
