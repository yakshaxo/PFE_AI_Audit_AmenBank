# 🏦 NEXUS: AI-Powered Infrastructure Monitoring & Audit System
**Final Year Project (PFE) – Amen Bank (2025–2026)**

![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)
![Python](https://img.shields.io/badge/Python-3.9+-yellow?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql)
![Zabbix](https://img.shields.io/badge/Zabbix-Monitoring-D40000?logo=zabbix)
![Ansible](https://img.shields.io/badge/Ansible-Automation-EE0000?logo=ansible)

NEXUS is an automated, fully containerized infrastructure monitoring and auditing platform. By integrating real-time telemetry from 300+ critical hosts with a custom, dual-layer Machine Learning engine, NEXUS transitions Amen Bank's infrastructure management from reactive alerting to proactive anomaly detection.

---

## 📋 Table of Contents
1. [Context & Problem Statement](#-context--problem-statement)
2. [Proposed Solution: NEXUS](#-proposed-solution-nexus)
3. [Global System Architecture](#-global-system-architecture)
4. [The Dual-Layer AI Engine](#-the-dual-layer-ai-engine)
5. [Security, HITL & Deployment](#-security-hitl--deployment)
6. [Results & Business Impact](#-results--business-impact)
7. [Installation & Access](#-installation--access)
8. [Future Perspectives](#-future-perspectives)
9. [Project Team](#-project-team)

---

## 🚨 Context & Problem Statement

Amen Bank operates a massive scale of 300+ critical hosts requiring 24/7 high availability, generating millions of telemetry data points daily across network, CPU, memory, and database layers. The legacy approach relied on traditional tools with manually configured thresholds, leading to three major vulnerabilities:

* **Reactive Monitoring:** Alerts only triggered after a server crashed, offering no predictive capability.
* **Alert Fatigue:** Static thresholds created high noise (false positives), masking true anomalies like gradual memory leaks.
* **Security Blindness:** Subtle infrastructural degradations went completely undetected.

---

## 💡 Proposed Solution: NEXUS

To solve these critical issues, NEXUS was built upon four core pillars:

1.  **Automated Detection:** A dual-layer AI engine flags anomalies *before* static thresholds are breached.
2.  **Secure Workflow:** A Human-in-the-Loop (HITL) validation system with Role-Based Access Control (RBAC) and full audit traceability.
3.  **Compliance Reporting:** Auto-generated PDF & CSV reports aligned with strict banking SLA requirements.
4.  **Scalable Deployment:** Ansible automates lightweight agent distribution, while Docker provides a modular, "black-box" core.

---

## 🧠 The Dual-Layer AI Engine

The intelligence of NEXUS relies on our custom **Hybrid Decision Gate**, designed specifically to eliminate alert fatigue. 

### Method 1: Isolation Forest (Machine Learning)
An unsupervised ML algorithm that builds randomized decision trees on historical metrics. It automatically learns the unique behavioral baseline of every single host, isolating sparse, anomalous data points instantly.

### Method 2: 2-Sigma Statistical Rule
A rolling statistical calculation that constantly updates the mean ($\mu$) and standard deviation ($\sigma$) per host, establishing highly flexible, dynamic boundaries.

### 🛡️ The Hybrid Gate 
An alert is **only** triggered if *both* the Isolation Forest and the 2-Sigma rule simultaneously flag an event as anomalous. If only one flags it, the event is logged for background traceability but does not trigger a disruptive alarm for the IT team.

---

## 🏗 Global System Architecture

The platform is divided into 5 isolated layers managed under a single `docker-compose.yml`:

1.  **Collection:** Zabbix Agents gather telemetry every 30 seconds.
2.  **Routing:** Zabbix Server dispatches webhooks to a secure FastAPI/Nginx layer.
3.  **Intelligence:** The AI Engine (Scikit-learn) processes the payload and assigns an anomaly score.
4.  **Storage:** PostgreSQL securely logs the alert, AI scores, and HITL actions.
5.  **Visualization:** Data is rendered in real-time via Grafana and a custom web interface.

---

## 🔒 Security, HITL & Deployment

* **Human-in-the-Loop (HITL):** When the AI flags an anomaly, it appears on the Analyst dashboard. The Analyst reviews and flags it, an Administrator validates it, and the system logs every action (timestamp, user ID) to generate compliance audit trails.
* **Strict Security:** All Zabbix requests require a Machine-Key authentication header. Traffic enters via HTTPS (Nginx), and the database network is completely masked from the public internet.
* **Black-Box Deployment:** The entire source code and AI models are packaged into a sealed Docker image, allowing Amen Bank operators to install the platform with a single command.

---

## 📈 Results & Business Impact

| Metric | Before NEXUS (Legacy) | After NEXUS |
| :--- | :--- | :--- |
| **Detection** | Reactive — alerts sent after failure | **Proactive** — anomalies flagged before breach |
| **False Positives**| High noise from static rules | **Eliminated** by dual-gate confirmation |
| **Deployment** | Manual per-host scripts (300+ hosts) | **Ansible** automates agent deployment |
| **Audit Trail** | No workflow, no traceability | **Full timestamped audit log** for every event |

---
