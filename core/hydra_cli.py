#!/usr/bin/env python3
"""
HydraPrime CLI — hydra
Usage: hydra <command> [args]
"""

import sys
import requests
import subprocess
import os
import json

BRIDGE = "http://localhost:9999"

def banner():
    print("🐉 HydraPrime — Three heads. One body.")

def cmd_start():
    """Start all three heads + the bridge."""
    print("🐉 Starting HydraPrime...")

    # Start OpenClaw
    subprocess.Popen(["sv", "up", "openclaw"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  🦾 OpenClaw → starting")

    # Start Hermes in proot
    subprocess.Popen(
        ["proot-distro", "login", "ubuntu", "--", "bash", "-c",
         "cd /root/hermes && hermes gateway --port 8765 &> /tmp/hermes.log &"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("  🧠 Hermes → starting")

    # Start OpenHuman
    oh_dir = os.path.expanduser("~/HydraPrime/heads/openhuman/openhuman")
    subprocess.Popen(
        ["node", "dist/main.js"],
        cwd=oh_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("  👁️  OpenHuman → starting")

    # Start bridge
    bridge_script = os.path.expanduser("~/hydra_bridge.py")
    subprocess.Popen(
        ["python3", bridge_script],
        stdout=open(os.path.expanduser("~/HydraPrime/logs/bridge.log"), "a"),
        stderr=subprocess.STDOUT
    )
    print("  🌉 Bridge → starting on :9999")
    print("\n✅ HydraPrime online. Use 'hydra status' to confirm all heads.")

def cmd_status():
    """Check status of all heads."""
    try:
        r = requests.get(f"{BRIDGE}/status", timeout=5)
        data = r.json()
        print(f"🐉 HydraPrime: {data['hydra'].upper()}")
        print(f"   Heads online: {data['heads_online']}")
        for h in data["heads"]:
            icon = "✅" if h["status"] == "online" else "❌"
            print(f"   {icon} {h['head']}: {h['status']}")
    except Exception:
        print("❌ Bridge is offline. Run 'hydra start' first.")

def cmd_think(task: str):
    """Send a task to the Hermes brain."""
    print(f"🧠 Thinking: {task}")
    try:
        r = requests.post(f"{BRIDGE}/think", json={"task": task}, timeout=60)
        data = r.json()
        result = data.get("result", data.get("output", json.dumps(data, indent=2)))
        print(f"\n📤 Result:\n{result}")
    except Exception as e:
        print(f"❌ Error: {e}")

def cmd_execute(task: str):
    """Full fusion execution — all three heads."""
    print(f"🐉 Full fusion executing: {task}")
    try:
        r = requests.post(f"{BRIDGE}/execute", json={"task": task}, timeout=90)
        data = r.json()
        result = data.get("result", {})
        output = result.get("result", result.get("output", str(result)))
        print(f"\n📤 Result:\n{output}")
        print(f"\n📍 Hardware: {json.dumps(data.get('hardware_snapshot', {}), indent=2)[:300]}")
    except Exception as e:
        print(f"❌ Error: {e}")

def cmd_sense(sensor: str):
    """Query hardware via OpenClaw."""
    print(f"🦾 Sensing: {sensor}")
    try:
        r = requests.get(f"{BRIDGE}/sense/{sensor}", timeout=10)
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")

def cmd_context(scope: str = "today"):
    """Pull life context from OpenHuman."""
    print(f"👁️  Pulling context: {scope}")
    try:
        r = requests.get(f"{BRIDGE}/context/{scope}", timeout=10)
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")

def cmd_stop():
    """Stop all heads."""
    subprocess.run(["sv", "down", "openclaw"], capture_output=True)
    subprocess.run(["pkill", "-f", "hermes"], capture_output=True)
    subprocess.run(["pkill", "-f", "hydra_bridge"], capture_output=True)
    subprocess.run(["pkill", "-f", "openhuman"], capture_output=True)
    print("🐉 HydraPrime stopped.")

def cmd_help():
    banner()
    print("""
Commands:
  hydra start                   Start all three heads + bridge
  hydra stop                    Stop all heads
  hydra status                  Check all heads online/offline
  hydra think "<task>"          Send task to Hermes brain
  hydra execute "<task>"        Full fusion: hardware + context + brain
  hydra sense <sensor>          Query hardware (gps, battery, network, camera)
  hydra context <scope>         Pull life context (today, calendar, email, memory)
  hydra help                    Show this help

Sensors:  gps | battery | camera | network | sensors | microphone
Scopes:   today | calendar | email | memory | all
""")

# ── Main ────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        cmd_help()
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "start":        cmd_start()
    elif cmd == "stop":       cmd_stop()
    elif cmd == "status":     cmd_status()
    elif cmd == "think":      cmd_think(" ".join(args[1:]) if len(args) > 1 else "")
    elif cmd == "execute":    cmd_execute(" ".join(args[1:]) if len(args) > 1 else "")
    elif cmd == "sense":      cmd_sense(args[1] if len(args) > 1 else "battery")
    elif cmd == "context":    cmd_context(args[1] if len(args) > 1 else "today")
    elif cmd == "help":       cmd_help()
    else:
        print(f"Unknown command: {cmd}")
        cmd_help()
