# 🏦 PFE – AI Monitoring & Audit System for Amen Bank

## 📋 Description

This project implements an **AI-assisted monitoring and audit platform** for IT infrastructure.
The system integrates **Zabbix monitoring** with a **Python AI engine (FastAPI)** that analyzes alerts, detects anomalies, and generates automated **PDF audit reports**.

The platform is fully **containerized with Docker**, enabling reproducible deployment.

---

# 🎯 Project Objectives

* Monitor system infrastructure using **Zabbix**
* Capture alerts in real time
* Analyze alerts using **Machine Learning**
* Store alerts in **PostgreSQL**
* Provide **AI-based recommendations**
* Generate **PDF audit reports**

---

# 🛠 Technology Stack

| Layer            | Technology              |
| ---------------- | ----------------------- |
| Monitoring       | Zabbix Server           |
| Agents           | Zabbix Agent            |
| Backend API      | FastAPI                 |
| Machine Learning | Scikit-learn            |
| Database         | PostgreSQL              |
| Reports          | Python PDF Generator    |
| Containerization | Docker + Docker Compose |
| Visualization    | Zabbix Dashboard        |

---

# 🧠 System Architecture

Alert pipeline:

1. **Zabbix Agent**

   * Collects system metrics (CPU, memory, disk)

2. **Zabbix Server**

   * Evaluates triggers

3. **Webhook**

   * Sends alert data as JSON to the AI engine

4. **AI Engine (FastAPI)**

   * Receives alert
   * Stores it in PostgreSQL
   * Runs anomaly detection (ML)
   * Generates recommendations

5. **PDF Generator**

   * Aggregates alerts
   * Generates automated audit reports

---

# 📂 Project Structure

```
PFE_AI_Audit_AmenBank/

├── docker-compose.yml
├── .env
├── README.md
│
├── ai-engine/
│   ├── main.py              # FastAPI API + DB connection + alert storage
│   ├── analyzer.py          # ML anomaly detection logic (Hakim)
│   ├── recommender.py       # AI recommendations based on alerts
│   ├── pdf_generator.py     # PDF audit report generator
│   ├── model.pkl            # Trained ML model (generated after training)
│   └── train_model.py       # Script used to train the ML model
│
├── postgres/
│   └── init.sql             # Optional DB initialization
│
├── zabbix/
│   └── webhook_script.js    # Zabbix webhook sending alerts to AI engine
│
└── docs/
    └── architecture.md
```

---

# 🧠 AI Engine Responsibilities

### `main.py`

Central service responsible for:

* FastAPI server
* Database connection
* Alert API endpoint
* Storing alerts
* Calling analyzer and recommender modules

Example flow:

```
Zabbix Alert
      ↓
FastAPI Endpoint
      ↓
Store Alert in PostgreSQL
      ↓
Analyzer (ML anomaly score)
      ↓
Recommender (suggest action)
      ↓
Optional PDF report
```

---

### `analyzer.py`

Handles **machine learning analysis**.

Responsibilities:

* Load trained ML model (`model.pkl`)
* Predict anomaly score
* Classify alert severity

Example:

```
alert → model → anomaly_score
```

Hakim will implement:

* training dataset
* model training
* exporting the trained model

---

### `recommender.py`

Provides **expert recommendations** based on alerts.

Example:

```
CPU > 90% → "Check running processes"
Disk full → "Clean temporary files"
```

---

### `pdf_generator.py`

Generates **audit reports**.

Example report contents:

* alert history
* severity distribution
* anomaly detection results
* recommendations

Generated with Python libraries like:

```
reportlab
fpdf
```

---

# 🚀 Installation

### Start system

```
docker compose up -d
```

Check containers

```
docker compose ps
```

---

# 🌐 Access

| Service   | URL                          | Usage         |
| --------- | ---------------------------- | ------------- |
| Zabbix    | http://localhost:8080        | Monitoring    |
| AI API    | http://localhost:5000/docs   | Swagger API   |
| AI Health | http://localhost:5000/health | Service check |

---

# 🧪 End-to-End Alert Flow

1️⃣ CPU usage exceeds threshold
2️⃣ Zabbix trigger fires
3️⃣ Webhook sends JSON alert to FastAPI

Example payload:

```
{
 "host": "LOUAY-PC",
 "trigger": "High CPU Usage",
 "severity": "High",
 "message": "CPU usage > 90%"
}
```

4️⃣ AI engine processes alert:

```
main.py
   ↓
store in DB
   ↓
analyzer.py
   ↓
recommender.py
```

5️⃣ Optional report generation.

---

# 📊 Machine Learning Workflow

Hakim's workflow:

1. Collect alert dataset
2. Train model

```
python train_model.py
```

3. Export model

```
model.pkl
```

4. Analyzer loads model for predictions.

---

# 👥 Project Team

**Louay Krayem** – Infrastructure & Backend
**Hakim** – Machine Learning Layer

Supervisor:
Karim Rayachi – Amen Bank

---

# 🎓 Final Year Project

ESPRIT – Business Intelligence
