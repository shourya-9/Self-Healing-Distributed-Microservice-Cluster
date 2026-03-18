from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import time
import random
import os
from threading import Lock

app = FastAPI()

# -------------------------------
# Metrics
# -------------------------------

REQUEST_COUNT = Counter(
    "auth_requests_total",
    "Total auth requests"
)

REQUEST_LATENCY = Histogram(
    "auth_request_latency_seconds",
    "Auth request latency"
)

# -------------------------------
# Runtime State (Live Toggles)
# -------------------------------

LATENCY_MODE = False
CRASH_MODE = False

state_lock = Lock()

# -------------------------------
# Core Endpoint
# -------------------------------

@app.get("/login")
def login():
    global LATENCY_MODE, CRASH_MODE

    start = time.time()

    # Simulate crash
    with state_lock:
        if CRASH_MODE:
            os._exit(1)

    # Simulate latency
    with state_lock:
        if LATENCY_MODE:
            time.sleep(random.uniform(6, 10))

    REQUEST_COUNT.inc()
    REQUEST_LATENCY.observe(time.time() - start)

    return {"status": "logged in"}


# -------------------------------
# Live Toggle Endpoints
# -------------------------------

@app.post("/toggle-latency")
def toggle_latency(enabled: bool):
    global LATENCY_MODE
    with state_lock:
        LATENCY_MODE = enabled
    return {"latency_mode": LATENCY_MODE}


@app.post("/toggle-crash")
def toggle_crash(enabled: bool):
    global CRASH_MODE
    with state_lock:
        CRASH_MODE = enabled
    return {"crash_mode": CRASH_MODE}


# -------------------------------
# Health + Metrics
# -------------------------------

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")