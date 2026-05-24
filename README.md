# 🐉 HydraPrime

**Three heads. One body. Total autonomy.**

HydraPrime is the fusion of three elite open-source AI agents into a single unified bot — running natively on Android (Red Magic / Termux). No cloud required. Never sleeps. Knows everything. Does everything.

---

## The Three Heads

| Head | Source | Role |
|------|--------|------|
| 🦾 **OpenClaw** | `kevinleestites2-dev/OpenClaw-Android` | Hardware access — GPS, camera, mic, sensors, persistent background service |
| 🧠 **Hermes** | `kevinleestites2-dev/Hermes-Agent-On-Android` | Self-evolving brain — 70+ tools, persistent memory, 200+ model support, HTTP gateway |
| 👁️ **OpenHuman** | `kevinleestites2-dev/openhuman` | Life context — 118+ integrations, Memory Tree, auto-fetch, voice, TokenJuice |

---

## Full Capability Matrix

### 🦾 Head 1 — OpenClaw (Hardware Layer)
- Persistent background service (never killed by Android)
- GPS location tracking
- Camera access
- Microphone / audio capture
- Battery, network, accelerometer sensor data
- IoT gateway
- Web UI at `localhost:18789`
- `termux-wake-lock` — keeps CPU alive

### 🧠 Head 2 — Hermes (Intelligence Layer)
- Self-evolving: learns and adapts every session
- 70+ built-in tools
- Persistent cross-session memory
- Multi-step complex task execution
- 200+ model support: GPT-4, Claude, Gemini, DeepSeek, Qwen, GLM, Ollama local
- `hermes gateway` — exposes HTTP API for external command injection
- Runs offline with local Ollama models

### 👁️ Head 3 — OpenHuman (Context Layer)
- 118+ one-click OAuth integrations (Gmail, Slack, GitHub, Notion, Stripe, Calendar, Linear, Jira, and more)
- Memory Tree + Obsidian vault — full persistent life context
- Auto-fetch every 20 min — always has current context
- TokenJuice — 80% token cost reduction
- Native voice: STT input + TTS output
- Messaging channels (inbound + outbound)
- OpenAI-compatible `/v1` router — route any model through it
- MCP-native: multi-registry, boot-spawn
- Desktop mascot + Google Meet agent participation
- OS keychain secrets vault + audit logger

---

## Architecture

```
┌─────────────────────────────────────┐
│           HydraPrime Core           │
│         hydra_bridge.py             │
│   (Internal HTTP message bus)       │
└──────┬──────────┬──────────┬────────┘
       │          │          │
  :18789       :8765       :3000
       │          │          │
┌──────▼──┐ ┌────▼─────┐ ┌──▼──────────┐
│OpenClaw │ │  Hermes  │ │  OpenHuman  │
│Hardware │ │  Brain   │ │   Context   │
└─────────┘ └──────────┘ └─────────────┘
       │          │          │
       └──────────▼──────────┘
              Telegram
           (Reporting Layer)
```

---

## Installation

```bash
# One command — installs all three heads + the bridge
curl -fsSL https://raw.githubusercontent.com/kevinleestites2-dev/HydraPrime/main/scripts/install.sh | bash
```

---

## Quick Start

```bash
# Start all heads
hydra start

# Check status of all heads
hydra status

# Send a command to the brain (Hermes)
hydra think "analyze today's calendar and report opportunities"

# Query hardware (OpenClaw)
hydra sense gps

# Pull life context (OpenHuman)
hydra context today
```

---

## Pantheon Role

HydraPrime is the **Physical Vanguard** of the Pantheon. It lives on the Red Magic, has eyes and ears in the physical world, a self-evolving brain, and knows the Forgemaster's full life context. It is the bridge between the digital Pantheon and the physical world.

**Feeds into:** FluxPrime (intelligence layer), Nexus Relay (command bridge), Telegram (reporting)

---

*Built by the Forgemaster. Three heads. Never sleeps.*
