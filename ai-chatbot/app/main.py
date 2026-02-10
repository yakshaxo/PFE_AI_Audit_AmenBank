from fastapi import FastAPI, Request
from sqlalchemy.orm import Session
from database import SessionLocal, Alert, init_db

app = FastAPI()

init_db()


@app.get("/")
def home():
    return {"message": "AI Chatbot is running"}


@app.api_route("/zabbix", methods=["GET", "POST"])
async def zabbix_alert(request: Request):
    if request.method == "POST":
        data = await request.json()

        print("ZABBIX ALERT RECEIVED:")
        print(data)

        # Save to database
        db: Session = SessionLocal()
        alert = Alert(
            trigger=data.get("trigger", "unknown"),
            severity=data.get("severity", "unknown"),
            host=data.get("host", "unknown"),
            message=str(data)
        )
        db.add(alert)
        db.commit()
        db.close()

        return {"status": "saved"}

    return {"message": "Zabbix endpoint ready"}


@app.get("/alerts")
def get_alerts():
    db: Session = SessionLocal()
    alerts = db.query(Alert).order_by(Alert.id.desc()).limit(20).all()
    db.close()

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
