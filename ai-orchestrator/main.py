import requests
import time
import docker
import threading
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# -----------------------------
# CONFIG
# -----------------------------

PROMETHEUS_URL = "http://prometheus:9090"

AUTH_QUERY = """
sum(rate(auth_request_latency_seconds_sum[2m])) 
/
sum(rate(auth_request_latency_seconds_count[2m]))
"""

ORDER_QUERY = """
sum(rate(order_request_latency_seconds_sum[2m])) 
/
sum(rate(order_request_latency_seconds_count[2m]))
"""

CHECK_INTERVAL = 5
ABSOLUTE_SLA_LIMIT = 2.0

COOLDOWN_SECONDS = 30
MAX_RESTARTS_PER_WINDOW = 3
WINDOW_RESET_SECONDS = 120
STABILIZATION_SECONDS = 20

# -----------------------------
# METRICS
# -----------------------------

healing_attempts_total = Counter("healing_attempts_total", "Total healing attempts")
healing_success_total = Counter("healing_success_total", "Successful healings")
healing_failures_total = Counter("healing_failures_total", "Escalation events")
healing_mttr_seconds = Histogram("healing_mttr_seconds", "Mean time to recovery")

active_incident = Gauge("active_incident", "1 if incident active")
incident_escalated = Gauge("incident_escalated", "1 if escalated")
incident_duration_seconds = Histogram("incident_duration_seconds", "Incident duration")

# -----------------------------
# STATE
# -----------------------------

docker_client = docker.from_env()

last_restart_time = None
restart_count = 0
window_start_time = datetime.now()
stabilizing_until = None

incident_start_time = None
escalated = False

# -----------------------------
# FASTAPI
# -----------------------------

app = FastAPI()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# -----------------------------
# UTIL
# -----------------------------

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

# -----------------------------
# RESTART FUNCTIONS
# -----------------------------

def restart_service(service_name):
    global last_restart_time, restart_count
    global window_start_time, stabilizing_until
    global incident_start_time, escalated

    now = datetime.now()

    if escalated:
        return

    if (now - window_start_time).total_seconds() > WINDOW_RESET_SECONDS:
        restart_count = 0
        window_start_time = now

    if restart_count >= MAX_RESTARTS_PER_WINDOW:
        healing_failures_total.inc()
        incident_escalated.set(1)
        escalated = True
        print("🚨 ESCALATED — restart limit reached")
        return

    if last_restart_time and (now - last_restart_time).total_seconds() < COOLDOWN_SECONDS:
        return

    healing_attempts_total.inc()
    active_incident.set(1)

    if incident_start_time is None:
        incident_start_time = now

    for container in docker_client.containers.list(all=True):
        if service_name in container.name:
            container.restart()
            print(f"🔄 Restarted {service_name}")
            restart_count += 1
            last_restart_time = now
            stabilizing_until = now + timedelta(seconds=STABILIZATION_SECONDS)
            return

# -----------------------------
# CONTROL LOOP
# -----------------------------

def monitoring_loop():
    global incident_start_time, escalated

    print("🚀 Root-Cause Orchestrator Started")

    while True:
        now = datetime.now()

        if stabilizing_until and now < stabilizing_until:
            time.sleep(CHECK_INTERVAL)
            continue

        auth_latency = get_metric(AUTH_QUERY)
        order_latency = get_metric(ORDER_QUERY)

        auth_bad = auth_latency is not None and auth_latency > ABSOLUTE_SLA_LIMIT
        order_bad = order_latency is not None and order_latency > ABSOLUTE_SLA_LIMIT

        # Root cause reasoning
        if auth_bad:
            restart_service("auth-service")

        elif order_bad:
            restart_service("order-service")

        # Recovery detection
        if incident_start_time and not auth_bad and not order_bad:
            duration = (datetime.now() - incident_start_time).total_seconds()
            incident_duration_seconds.observe(duration)
            healing_success_total.inc()
            healing_mttr_seconds.observe(duration)

            active_incident.set(0)
            incident_escalated.set(0)

            incident_start_time = None
            escalated = False
            restart_count = 0

        time.sleep(CHECK_INTERVAL)

# -----------------------------
# START BACKGROUND THREAD
# -----------------------------

thread = threading.Thread(target=monitoring_loop, daemon=True)
thread.start()