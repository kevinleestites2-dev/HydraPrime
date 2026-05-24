#!/usr/bin/env python3
"""
HydraPrime CLI — hydra
Single entry point for all three heads.
"""

import sys, os, json, subprocess, requests, time

BRIDGE = "http://localhost:9999"
HYDRA_DIR = os.path.expanduser("~/HydraPrime")

def cmd_start():
    print("🐉 Starting HydraPrime...\n")

    # ── Head 1: OpenClaw ──
    try:
        subprocess.Popen(
            ["sv", "up", "openclaw"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.Popen(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("  🦾 OpenClaw     → starting (sv up openclaw)")
    except Exception as e:
        print(f"  🦾 OpenClaw     → warning: {e}")

    # ── Head 2: Hermes (runs inside proot Ubuntu) ──
    hermes_cmd = (
        "proot-distro login ubuntu -- bash -c "
        "'cd /root/hermes-agent && source venv/bin/activate && "
        "hermes gateway --port 8765 >> /tmp/hermes_gateway.log 2>&1 &'"
    )
    try:
        subprocess.Popen(hermes_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("  🧠 Hermes       → starting (hermes gateway --port 8765)")
    except Exception as e:
        print(f"  🧠 Hermes       → warning: {e}")

    # ── Head 3: OpenHuman ──
    oh_dir = os.path.expanduser("~/openhuman")
    if os.path.isdir(oh_dir):
        try:
            log_path = os.path.join(HYDRA_DIR, "logs", "openhuman.log")
            with open(log_path, "a") as lf:
                subprocess.Popen(
                    ["node", "dist/main.js"],
                    cwd=oh_dir, stdout=lf, stderr=lf
                )
            print("  👁️  OpenHuman   → starting (node dist/main.js)")
        except Exception as e:
            print(f"  👁️  OpenHuman   → warning: {e}")
    else:
        print(f"  👁️  OpenHuman   → not found at {oh_dir}")

    # ── Bridge ──
    bridge = os.path.expanduser("~/hydra_bridge.py")
    log_path = os.path.join(HYDRA_DIR, "logs", "bridge.log")
    try:
        with open(log_path, "a") as lf:
            subprocess.Popen(["python3", bridge], stdout=lf, stderr=lf)
        print("  🌉 Bridge       → starting (port 9999)\n")
    except Exception as e:
        print(f"  🌉 Bridge       → warning: {e}\n")

    print("Waiting for heads to come up...")
    time.sleep(5)
    cmd_status()

def cmd_stop():
    subprocess.run(["sv", "down", "openclaw"], capture_output=True)
    subprocess.run(["pkill", "-f", "hermes gateway"], capture_output=True)
    subprocess.run(["pkill", "-f", "hydra_bridge"], capture_output=True)
    subprocess.run(["pkill", "-f", "openhuman"], capture_output=True)
    print("🐉 HydraPrime stopped.")

def cmd_status():
    try:
        r = requests.get(f"{BRIDGE}/status", timeout=5)
        d = r.json()
        print(f"🐉 HydraPrime: {d.get('hydra','?').upper()}")
        print(f"   Heads online: {d.get('heads_online','?')}")
        for h in d.get("heads", []):
            icon = "✅" if h["status"] == "online" else "❌"
            extra = f"  (code {h['code']})" if h.get("code") else f"  ({h.get('error','')})"
            print(f"   {icon} {h['head']}: {h['status']}{extra}")
    except Exception:
        print("❌ Bridge offline — run 'hydra start'")

def cmd_think(task: str):
    if not task:
        print("Usage: hydra think \"your task\"")
        return
    print(f"🧠 Hermes → {task}\n")
    try:
        r = requests.post(f"{BRIDGE}/think", json={"task": task}, timeout=90)
        d = r.json()
        out = d.get("result", d.get("output", d.get("response", json.dumps(d, indent=2))))
        print(f"📤 Result:\n{out}")
    except Exception as e:
        print(f"❌ {e}")

def cmd_execute(task: str):
    if not task:
        print("Usage: hydra execute \"your task\"")
        return
    print(f"🐉 Full fusion → {task}\n")
    try:
        r = requests.post(f"{BRIDGE}/execute", json={"task": task}, timeout=120)
        d = r.json()
        result = d.get("result", {})
        out = result.get("result", result.get("output", result.get("response", str(result))))
        hw  = d.get("hardware", {})
        print(f"📤 Result:\n{out}\n")
        gps = hw.get("gps", {}).get("data", {})
        bat = hw.get("battery", {}).get("data", {})
        if gps or bat:
            print(f"📍 Hardware snapshot: GPS={gps} | Battery={bat}")
    except Exception as e:
        print(f"❌ {e}")

def cmd_sense(sensor: str):
    print(f"🦾 Sensing: {sensor}")
    try:
        r = requests.get(f"{BRIDGE}/sense/{sensor}", timeout=10)
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"❌ {e}")

def cmd_context(scope: str):
    print(f"👁️  Context: {scope}")
    try:
        r = requests.get(f"{BRIDGE}/context/{scope}", timeout=10)
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"❌ {e}")

def cmd_logs(head: str = "bridge"):
    log_map = {
        "bridge":    f"{HYDRA_DIR}/logs/bridge.log",
        "openclaw":  "/data/data/com.termux/files/usr/var/log/openclaw/current",
        "hermes":    "/tmp/hermes_gateway.log",
        "openhuman": f"{HYDRA_DIR}/logs/openhuman.log",
    }
    path = log_map.get(head, log_map["bridge"])
    try:
        os.system(f"tail -50 {path}")
    except Exception as e:
        print(f"❌ {e}")

def cmd_help():
    print("""
🐉 HydraPrime CLI

  hydra start                   Start all three heads + bridge
  hydra stop                    Stop everything
  hydra status                  Check all heads online/offline

  hydra think  "task"           Hermes brain only
  hydra execute "task"          Full fusion (hardware + context + brain)

  hydra sense  <sensor>         OpenClaw hardware query
      Sensors: gps | battery | network | camera | sensors | microphone

  hydra context <scope>         OpenHuman life context
      Scopes:  today | calendar | email | memory | slack | github | all

  hydra logs   <head>           Tail logs
      Heads:   bridge | openclaw | hermes | openhuman

  hydra help                    This screen
""")

# ── Entry ──────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        cmd_help(); sys.exit(0)

    cmd  = args[0].lower()
    rest = " ".join(args[1:]) if len(args) > 1 else ""
    arg1 = args[1] if len(args) > 1 else ""

    if   cmd == "start":    cmd_start()
    elif cmd == "stop":     cmd_stop()
    elif cmd == "status":   cmd_status()
    elif cmd == "think":    cmd_think(rest)
    elif cmd == "execute":  cmd_execute(rest)
    elif cmd == "sense":    cmd_sense(arg1 or "battery")
    elif cmd == "context":  cmd_context(arg1 or "today")
    elif cmd == "logs":     cmd_logs(arg1 or "bridge")
    elif cmd == "help":     cmd_help()
    else:
        print(f"Unknown command: {cmd}")
        cmd_help()
