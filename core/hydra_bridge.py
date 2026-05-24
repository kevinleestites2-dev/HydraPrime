#!/usr/bin/env python3
"""
HydraPrime Bridge — hydra_bridge.py
The internal message bus connecting all three heads.
OpenClaw (hardware) ↔ Hermes (brain) ↔ OpenHuman (context)
+ Telegram reporting
"""

import os
import json
import asyncio
import aiohttp
import requests
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ── Load config ────────────────────────────────────────────
load_dotenv(os.path.expanduser("~/HydraPrime/config/hydra.env"))

OPENCLAW_URL   = f"http://localhost:{os.getenv('OPENCLAW_PORT', '18789')}"
HERMES_URL     = f"http://localhost:{os.getenv('HERMES_GATEWAY_PORT', '8765')}"
OPENHUMAN_URL  = f"http://localhost:{os.getenv('OPENHUMAN_PORT', '3000')}"
TG_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")
BRIDGE_PORT    = int(os.getenv("HYDRA_BRIDGE_PORT", "9999"))

app = Flask(__name__)

# ── Telegram reporting ─────────────────────────────────────
def tg_send(msg: str):
    """Send a message to Telegram."""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": f"🐉 HydraPrime\n{msg}"},
            timeout=5
        )
    except Exception:
        pass

# ── Head health check ──────────────────────────────────────
def check_head(name: str, url: str) -> dict:
    try:
        r = requests.get(url, timeout=3)
        return {"head": name, "status": "online", "code": r.status_code}
    except Exception as e:
        return {"head": name, "status": "offline", "error": str(e)}

# ── Hardware query (OpenClaw) ──────────────────────────────
def sense(sensor: str) -> dict:
    """Query hardware via OpenClaw."""
    sensor_map = {
        "gps":         "/api/location",
        "battery":     "/api/battery",
        "camera":      "/api/camera/capture",
        "network":     "/api/network",
        "sensors":     "/api/sensors",
        "microphone":  "/api/audio/record",
    }
    endpoint = sensor_map.get(sensor, f"/api/{sensor}")
    try:
        r = requests.get(f"{OPENCLAW_URL}{endpoint}", timeout=10)
        return {"sensor": sensor, "data": r.json()}
    except Exception as e:
        return {"sensor": sensor, "error": str(e)}

# ── Send task to Hermes brain ──────────────────────────────
def think(task: str, context: dict = None) -> dict:
    """Send a task to the Hermes agent."""
    payload = {"task": task}
    if context:
        payload["context"] = context
    try:
        r = requests.post(f"{HERMES_URL}/execute", json=payload, timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e), "task": task}

# ── Pull context from OpenHuman ────────────────────────────
def get_context(scope: str = "today") -> dict:
    """Pull life context from OpenHuman."""
    scope_map = {
        "today":    "/api/context/today",
        "calendar": "/api/integrations/calendar",
        "email":    "/api/integrations/gmail",
        "memory":   "/api/memory/tree",
        "all":      "/api/context/full",
    }
    endpoint = scope_map.get(scope, f"/api/context/{scope}")
    try:
        r = requests.get(f"{OPENHUMAN_URL}{endpoint}", timeout=10)
        return {"scope": scope, "data": r.json()}
    except Exception as e:
        return {"scope": scope, "error": str(e)}

# ── Full fusion: sense + context → think ──────────────────
def fuse_and_execute(task: str) -> dict:
    """
    The full HydraPrime loop:
    1. Pull hardware context (OpenClaw)
    2. Pull life context (OpenHuman)
    3. Inject both into Hermes brain
    4. Execute and report to Telegram
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🐉 HydraPrime executing: {task}")

    # Head 1: Hardware snapshot
    hardware = {
        "gps":     sense("gps"),
        "battery": sense("battery"),
        "network": sense("network"),
    }

    # Head 3: Life context
    life = get_context("today")

    # Head 2: Execute with full context
    result = think(task, context={"hardware": hardware, "life_context": life})

    # Report to Telegram
    output = result.get("result", result.get("output", str(result)))
    tg_send(f"Task: {task}\n\nResult: {output[:1000]}")

    return {
        "task": task,
        "result": result,
        "hardware_snapshot": hardware,
        "life_context": life,
        "timestamp": timestamp,
    }

# ── Flask API endpoints ────────────────────────────────────
@app.route("/status", methods=["GET"])
def status():
    heads = [
        check_head("OpenClaw",  OPENCLAW_URL),
        check_head("Hermes",    HERMES_URL),
        check_head("OpenHuman", OPENHUMAN_URL),
    ]
    online = sum(1 for h in heads if h["status"] == "online")
    return jsonify({
        "hydra": "online",
        "heads_online": f"{online}/3",
        "heads": heads,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/think", methods=["POST"])
def route_think():
    data = request.json or {}
    task = data.get("task", "")
    if not task:
        return jsonify({"error": "task required"}), 400
    result = think(task, data.get("context"))
    return jsonify(result)

@app.route("/sense/<sensor>", methods=["GET"])
def route_sense(sensor):
    return jsonify(sense(sensor))

@app.route("/context/<scope>", methods=["GET"])
def route_context(scope):
    return jsonify(get_context(scope))

@app.route("/execute", methods=["POST"])
def route_execute():
    """Full fusion execution — all three heads."""
    data = request.json or {}
    task = data.get("task", "")
    if not task:
        return jsonify({"error": "task required"}), 400
    return jsonify(fuse_and_execute(task))

@app.route("/report", methods=["POST"])
def route_report():
    """Send a message to Telegram."""
    data = request.json or {}
    msg = data.get("message", "")
    tg_send(msg)
    return jsonify({"sent": True})

# ── Heartbeat ──────────────────────────────────────────────
def heartbeat_loop():
    """Send a heartbeat to Telegram every 30 minutes."""
    while True:
        time.sleep(1800)
        heads = [
            check_head("OpenClaw",  OPENCLAW_URL),
            check_head("Hermes",    HERMES_URL),
            check_head("OpenHuman", OPENHUMAN_URL),
        ]
        online = [h["head"] for h in heads if h["status"] == "online"]
        offline = [h["head"] for h in heads if h["status"] == "offline"]
        msg = f"💓 Heartbeat\nOnline: {', '.join(online) if online else 'none'}"
        if offline:
            msg += f"\n⚠️ Offline: {', '.join(offline)}"
        tg_send(msg)

if __name__ == "__main__":
    # Announce startup
    tg_send("🐉 HydraPrime Bridge ONLINE\nAll three heads initializing...")

    # Start heartbeat in background
    hb = threading.Thread(target=heartbeat_loop, daemon=True)
    hb.start()

    print(f"🐉 HydraPrime Bridge running on port {BRIDGE_PORT}")
    app.run(host="0.0.0.0", port=BRIDGE_PORT, debug=False)
