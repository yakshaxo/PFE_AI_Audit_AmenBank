from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
def home():
    return {"message": "AI Chatbot is running"}

@app.post("/zabbix")
async def zabbix_alert(request: Request):
    data = await request.json()
    print("Received alert:", data)
    return {"status": "ok"}
