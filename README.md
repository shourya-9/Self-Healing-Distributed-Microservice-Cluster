# 🚀 AI Self-Healing Microservices System

An AI-powered self-healing system that detects anomalies in microservices using machine learning and automatically recovers from failures in real time.

---

## ⚡ Overview

This project simulates a production-like distributed system with:

- Multiple microservices (`auth-service`, `order-service`)
- Real-time monitoring via Prometheus
- AI-based anomaly detection using Isolation Forest
- Automated recovery (self-healing)
- Interactive control dashboard

The system continuously learns normal behavior and reacts when services degrade.

---

## 🧠 Key Features

### 🔍 Anomaly Detection (AI)
- Uses Isolation Forest for anomaly detection
- Learns baseline behavior dynamically
- Works on real-time Prometheus metrics

### 🔧 Self-Healing
- Automatically restarts failing services
- Root cause inference based on latency signals
- Cooldown + restart limits

### 🚨 Incident Management
- Tracks active incidents
- Measures MTTR (Mean Time To Recovery)
- Escalates when recovery fails

### 📊 Observability
- Prometheus metrics:
  - Latency
  - Healing attempts
  - Failures & escalations
- Grafana dashboards

### 🎛 Interactive Dashboard
- Start/Stop system
- Toggle traffic
- Inject latency faults
- Live system status

---

## 🏗 Architecture

User Dashboard  
        ↓  
Control Server  
        ↓  
Microservices (Auth + Order)  
        ↓  
Prometheus  
        ↓  
AI Orchestrator  
        ↓  
Docker (Restart Engine)

---

## 🧪 How It Works

1. Training Phase  
   - Collect latency metrics  
   - Train Isolation Forest model  

2. Detection Phase  
   - Evaluate incoming metrics  
   - Detect anomalies  

3. Recovery Phase  
   - Infer root cause  
   - Restart affected service  

4. Escalation  
   - Triggered after repeated failures  

---

## ⚙️ Tech Stack

- Python (FastAPI)
- Scikit-learn (Isolation Forest)
- Docker / Docker Compose
- Prometheus + Grafana
- HTML / CSS / JS Dashboard

---

## 🚀 Getting Started

### Clone

git clone https://github.com/your-username/ai-self-healing-system.git  
cd ai-self-healing-system  

### Setup

python3 -m venv .venv  
source .venv/bin/activate  
pip install -r control-server/requirements.txt  

### Run Control Server

uvicorn control-server.main:app --port 7010  

### Open Dashboard

Open control-panel/index.html  

---

## 🧪 Demo Workflow

1. Start system  
2. Enable traffic  
3. Wait for model training (model_ready = 1)  
4. Inject latency  
5. Observe:
   - anomaly detection  
   - automatic restart  
   - recovery  

---

## 📈 Metrics

- healing_attempts_total  
- healing_success_total  
- healing_failures_total  
- healing_mttr_seconds  
- active_incident  
- incident_escalated  
- model_ready  

---

## ⚠️ Challenges

- Prometheus smoothing affects latency
- ML models sensitive to training data
- Traffic pattern changes impact detection

---

## 💡 Future Improvements

- Adaptive retraining
- Better root cause analysis
- UI + Grafana integration
- Explainable AI outputs

---

## 🧠 Concepts Demonstrated

- AIOps systems
- ML in production
- Observability-driven design
- Automated incident response

---
