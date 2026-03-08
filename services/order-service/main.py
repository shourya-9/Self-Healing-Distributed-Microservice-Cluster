from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import time
import random
import requests
from threading import Lock

app = FastAPI()

REQUEST_COUNT = Counter(
    "order_requests_total",
    "Total order requests"
)

REQUEST_LATENCY = Histogram(
    "order_request_latency_seconds",
    "Order request latency"
)

LATENCY_MODE = False
state_lock = Lock()

@app.post("/create-order")
def create_order():
    global LATENCY_MODE

    start = time.time()

    # dependency call to auth-service
    try:
        requests.get("http://auth-service:8000/login", timeout=2)
    except:
        pass

    with state_lock:
        if LATENCY_MODE:
            time.sleep(random.uniform(1.5, 3.0))

    REQUEST_COUNT.inc()
    REQUEST_LATENCY.observe(time.time() - start)

    return {"status": "order created"}


@app.post("/toggle-latency")
def toggle_latency(enabled: bool):
    global LATENCY_MODE

    with state_lock:
        LATENCY_MODE = enabled

    return {"latency_mode": LATENCY_MODE}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")