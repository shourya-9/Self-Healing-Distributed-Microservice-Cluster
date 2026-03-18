import subprocess
import os
import threading
import requests
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

order_traffic = False
auth_traffic = False


def order_generator():
    global order_traffic
    while order_traffic:
        try:
            requests.post("http://localhost:8002/create-order")
        except:
            pass


def auth_generator():
    global auth_traffic
    while auth_traffic:
        try:
            requests.get("http://localhost:8001/login")
        except:
            pass


@app.post("/start-order-traffic")
def start_order_traffic():
    global order_traffic
    order_traffic = True
    threading.Thread(target=order_generator, daemon=True).start()
    return {"status": "order traffic started"}


@app.post("/stop-order-traffic")
def stop_order_traffic():
    global order_traffic
    order_traffic = False
    return {"status": "order traffic stopped"}


@app.post("/start-auth-traffic")
def start_auth_traffic():
    global auth_traffic
    auth_traffic = True
    threading.Thread(target=auth_generator, daemon=True).start()
    return {"status": "auth traffic started"}


@app.post("/stop-auth-traffic")
def stop_auth_traffic():
    global auth_traffic
    auth_traffic = False
    return {"status": "auth traffic stopped"}


@app.post("/start-system")
def start_system():

    subprocess.run(
        "docker compose up --build -d",
        shell=True,
        cwd=PROJECT_ROOT
    )

    return {"status": "system started"}


@app.post("/stop-system")
def stop_system():

    subprocess.run(
        "docker compose down",
        shell=True,
        cwd=PROJECT_ROOT
    )

    return {"status": "system stopped"}


@app.get("/system-status")
def system_status():

    result = subprocess.run(
        "docker compose ps --services --filter status=running",
        shell=True,
        capture_output=True,
        text=True
    )

    running = len(result.stdout.strip()) > 0

    return {"running": running}