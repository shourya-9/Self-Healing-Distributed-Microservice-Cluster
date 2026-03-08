import requests
import time
import docker
import threading
import numpy as np
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ==============================
# CONFIG
# ==============================

PROMETHEUS_URL = "http://prometheus:9090"

AUTH_QUERY = """
sum(rate(auth_request_latency_seconds_sum[90s]))
/
sum(rate(auth_request_latency_seconds_count[90s]))
"""

ORDER_QUERY = """
sum(rate(order_request_latency_seconds_sum[90s]))
/
sum(rate(order_request_latency_seconds_count[90s]))
"""

CHECK_INTERVAL = 5
TRAINING_DURATION_SECONDS = 120
CONTAMINATION = 0.1
STABILIZATION_SECONDS = 20

COOLDOWN_SECONDS = 30
MAX_RESTARTS_PER_WINDOW = 3
WINDOW_RESET_SECONDS = 120

# ==============================
# SERVICE DEPENDENCIES
# ==============================

SERVICE_DEPENDENCIES = {
    "order-service": ["auth-service"],
    "auth-service": []
}

# ==============================
# METRICS
# ==============================

healing_attempts_total = Counter("healing_attempts_total", "Total healing attempts")
healing_success_total = Counter("healing_success_total", "Successful healings")
healing_failures_total = Counter("healing_failures_total", "Escalation events")

healing_mttr_seconds = Histogram("healing_mttr_seconds", "Mean time to recovery")

active_incident = Gauge("active_incident", "1 if incident active")
incident_escalated = Gauge("incident_escalated", "1 if escalation occurred")
model_ready_metric = Gauge("model_ready", "1 if ML model trained")

# ==============================
# STATE
# ==============================

docker_client = docker.from_env()

training_data = []
model = None
scaler = StandardScaler()

model_ready = False
training_start_time = datetime.now()

last_restart_time = None
restart_count = 0
window_start_time = datetime.now()
stabilizing_until = None

incident_active = False
escalated = False
incident_start_time = None

# ==============================
# FASTAPI
# ==============================

app = FastAPI()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# ==============================
# PROMETHEUS METRIC FETCH
# ==============================

def get_metric(query):
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )

        data = response.json()

        if data["status"] != "success":
            return None

        results = data["data"]["result"]

        if not results:
            return None

        return float(results[0]["value"][1])

    except:
        return None

# ==============================
# ROOT CAUSE LOGIC
# ==============================

def determine_root_cause(auth_latency, order_latency):

    AUTH_THRESHOLD = 1.0
    ORDER_THRESHOLD = 1.0

    auth_problem = auth_latency > AUTH_THRESHOLD
    order_problem = order_latency > ORDER_THRESHOLD

    if auth_problem:
        return "auth-service"

    if order_problem and not auth_problem:
        return "order-service"

    return None

# ==============================
# RESTART LOGIC
# ==============================

def restart_service(service_name):

    global last_restart_time, restart_count
    global window_start_time, stabilizing_until
    global escalated, incident_active, incident_start_time

    now = datetime.now()

    if escalated:
        return

    if (now - window_start_time).total_seconds() > WINDOW_RESET_SECONDS:
        restart_count = 0
        window_start_time = now

    if restart_count >= MAX_RESTARTS_PER_WINDOW:
        incident_escalated.set(1)
        healing_failures_total.inc()
        escalated = True
        print("⚠ Escalation triggered")
        return

    if last_restart_time and (now - last_restart_time).total_seconds() < COOLDOWN_SECONDS:
        return

    healing_attempts_total.inc()
    active_incident.set(1)

    if not incident_active:
        incident_active = True
        incident_start_time = now

    for container in docker_client.containers.list(all=True):
        if service_name in container.name:
            print(f"🔥 Restarting {service_name}")
            container.restart()
            restart_count += 1
            last_restart_time = now
            stabilizing_until = now + timedelta(seconds=STABILIZATION_SECONDS)
            return

# ==============================
# MONITORING LOOP
# ==============================

def monitoring_loop():

    global model, model_ready, training_data
    global incident_active, escalated, incident_start_time

    print("🚀 AI Orchestrator Started")

    while True:

        now = datetime.now()

        if stabilizing_until and now < stabilizing_until:
            time.sleep(CHECK_INTERVAL)
            continue

        auth_latency = get_metric(AUTH_QUERY)
        order_latency = get_metric(ORDER_QUERY)

        if auth_latency is None:
            auth_latency = 0.0

        if order_latency is None:
            order_latency = 0.0

        sample = np.array([auth_latency, order_latency])

        # ================= TRAINING =================

        if not model_ready:

            training_data.append(sample)

            if (now - training_start_time).total_seconds() >= TRAINING_DURATION_SECONDS:

                X = np.array(training_data)
                X_scaled = scaler.fit_transform(X)

                model = IsolationForest(
                    n_estimators=200,
                    contamination=CONTAMINATION,
                    random_state=42
                )

                model.fit(X_scaled)

                model_ready = True
                model_ready_metric.set(1)

                print("✅ ML Model trained")

            time.sleep(CHECK_INTERVAL)
            continue

        # ================= DETECTION =================

        sample_scaled = scaler.transform([sample])

        prediction = model.predict(sample_scaled)[0]
        score = model.decision_function(sample_scaled)[0]

        print(f"Latency sample {sample} | score {score}")

        if prediction == -1 and not escalated:

            print("🚨 ML anomaly detected")

            root = determine_root_cause(auth_latency, order_latency)

            if root:
                print(f"🔎 Root cause inferred: {root}")
                restart_service(root)

        # ================= RECOVERY =================

        if incident_active and prediction == 1:

            duration = (datetime.now() - incident_start_time).total_seconds()

            healing_success_total.inc()
            healing_mttr_seconds.observe(duration)

            active_incident.set(0)
            incident_escalated.set(0)

            incident_active = False
            escalated = False
            restart_count = 0

            print(f"🟢 System recovered in {duration:.2f}s")

        time.sleep(CHECK_INTERVAL)

# ==============================
# START BACKGROUND LOOP
# ==============================

thread = threading.Thread(target=monitoring_loop, daemon=True)
thread.start()