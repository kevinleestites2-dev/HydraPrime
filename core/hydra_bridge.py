#!/usr/bin/env python3
"""
HydraPrime Bridge — hydra_bridge.py
Internal message bus: OpenClaw ↔ Hermes ↔ OpenHuman
+ Telegram heartbeat every 30 minutes
"""

import os, json, time, threading, requests
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ── Config ─────────────────────────────────────────────────
_cfg = os.path.expanduser("~/HydraPrime/config/hydra.env")
if os.path.exists(_cfg):
    load_dotenv(_cfg)

OPENCLAW_PORT   = os.getenv("OPENCLAW_PORT",   "18789")
HERMES_PORT     = os.getenv("HERMES_GATEWAY_PORT", "8765")
OPENHUMAN_PORT  = os.getenv("OPENHUMAN_PORT",  "3000")
BRIDGE_PORT     = int(os.getenv("HYDRA_BRIDGE_PORT", "9999"))
TG_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID",   "")

OPENCLAW_BASE   = f"http://localhost:{OPENCLAW_PORT}"
HERMES_BASE     = f"http://localhost:{HERMES_PORT}"
OPENHUMAN_BASE  = f"http://localhost:{OPENHUMAN_PORT}"

app = Flask(__name__)

# ── Telegram ───────────────────────────────────────────────
def tg(msg: str):
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

# ── Head health ────────────────────────────────────────────
def ping(name: str, url: str) -> dict:
    try:
        r = requests.get(url, timeout=3)
        return {"head": name, "status": "online", "code": r.status_code}
    except Exception as e:
        return {"head": name, "status": "offline", "error": str(e)}

# ── HEAD 1: OpenClaw hardware queries ─────────────────────
SENSOR_MAP = {
    "gps":        "/api/location",
    "battery":    "/api/battery",
    "camera":     "/api/camera/capture",
    "network":    "/api/network",
    "sensors":    "/api/sensors",
    "microphone": "/api/audio/record",
}

def sense(sensor: str) -> dict:
    endpoint = SENSOR_MAP.get(sensor, f"/api/{sensor}")
    try:
        r = requests.get(f"{OPENCLAW_BASE}{endpoint}", timeout=10)
        return {"sensor": sensor, "data": r.json()}
    except Exception as e:
        return {"sensor": sensor, "error": str(e)}

# ── HEAD 2: Hermes brain ───────────────────────────────────
# Hermes exposes an HTTP gateway via: hermes gateway --port 8765
# The gateway accepts task payloads and returns agent results.
def think(task: str, context: dict = None) -> dict:
    payload = {"task": task}
    if context:
        payload["context"] = context
    try:
        r = requests.post(f"{HERMES_BASE}/execute", json=payload, timeout=90)
        return r.json()
    except Exception as e:
        # Fallback: try /run endpoint (Hermes version differences)
        try:
            r = requests.post(f"{HERMES_BASE}/run", json={"prompt": task}, timeout=90)
            return r.json()
        except Exception:
            return {"error": str(e), "task": task}

# ── HEAD 3: OpenHuman context ─────────────────────────────
CONTEXT_MAP = {
    "today":    "/api/context/today",
    "calendar": "/api/integrations/calendar",
    "email":    "/api/integrations/gmail",
    "memory":   "/api/memory/tree",
    "all":      "/api/context/full",
    "slack":    "/api/integrations/slack",
    "github":   "/api/integrations/github",
    "notion":   "/api/integrations/notion",
}

def get_context(scope: str = "today") -> dict:
    endpoint = CONTEXT_MAP.get(scope, f"/api/context/{scope}")
    try:
        r = requests.get(f"{OPENHUMAN_BASE}{endpoint}", timeout=10)
        return {"scope": scope, "data": r.json()}
    except Exception as e:
        return {"scope": scope, "error": str(e)}

# ── Full fusion loop ───────────────────────────────────────
def fuse(task: str) -> dict:
    """
    The HydraPrime execution loop:
    1. Snapshot hardware state (OpenClaw)
    2. Pull life context (OpenHuman)
    3. Inject both into Hermes + execute
    4. Report to Telegram
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] 🐉 Executing: {task}")

    hardware = {
        "gps":     sense("gps"),
        "battery": sense("battery"),
        "network": sense("network"),
    }
    life = get_context("today")
    result = think(task, context={"hardware": hardware, "life_context": life})

    output = result.get("result", result.get("output", result.get("response", str(result))))
    tg(f"Task: {task}\n\nResult: {str(output)[:1000]}")

    return {
        "task": task,
        "result": result,
        "hardware": hardware,
        "life_context": life,
        "timestamp": ts,
    }

# ── Flask routes ───────────────────────────────────────────
@app.route("/status")
def status():
    heads = [
        ping("OpenClaw",  OPENCLAW_BASE),
        ping("Hermes",    HERMES_BASE),
        ping("OpenHuman", OPENHUMAN_BASE),
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
    return jsonify(think(task, data.get("context")))

@app.route("/sense/<sensor>")
def route_sense(sensor):
    return jsonify(sense(sensor))

@app.route("/context/<scope>")
def route_context(scope):
    return jsonify(get_context(scope))

@app.route("/execute", methods=["POST"])
def route_execute():
    data = request.json or {}
    task = data.get("task", "")
    if not task:
        return jsonify({"error": "task required"}), 400
    return jsonify(fuse(task))

@app.route("/report", methods=["POST"])
def route_report():
    data = request.json or {}
    tg(data.get("message", ""))
    return jsonify({"sent": True})

@app.route("/mcp/tools", methods=["GET"])
def mcp_tools():
    """Proxy MCP tool listing from OpenHuman's MCP server."""
    try:
        r = requests.get(f"{OPENHUMAN_BASE}/mcp/tools", timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503

@app.route("/mcp/execute", methods=["POST"])
def mcp_execute():
    """Proxy MCP tool execution to OpenHuman."""
    data = request.json or {}
    try:
        r = requests.post(f"{OPENHUMAN_BASE}/mcp/execute", json=data, timeout=30)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503

# ── Heartbeat ──────────────────────────────────────────────
def heartbeat():
    while True:
        time.sleep(1800)  # 30 minutes
        heads = [
            ping("OpenClaw",  OPENCLAW_BASE),
            ping("Hermes",    HERMES_BASE),
            ping("OpenHuman", OPENHUMAN_BASE),
        ]
        on  = [h["head"] for h in heads if h["status"] == "online"]
        off = [h["head"] for h in heads if h["status"] == "offline"]
        msg = f"💓 Heartbeat [{datetime.now().strftime('%H:%M')}]\n"
        msg += f"Online: {', '.join(on) if on else 'none'}"
        if off:
            msg += f"\n⚠️ Offline: {', '.join(off)}"
        tg(msg)

if __name__ == "__main__":
    tg("🐉 HydraPrime Bridge ONLINE — all three heads initializing")
    threading.Thread(target=heartbeat, daemon=True).start()
    print(f"🐉 HydraPrime Bridge → port {BRIDGE_PORT}")
    app.run(host="0.0.0.0", port=BRIDGE_PORT, debug=False)
