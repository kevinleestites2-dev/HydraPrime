#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# HydraPrime — Unified Installer
# Three heads. One body. Total autonomy.
# ============================================================

set -e

HYDRA_DIR="$HOME/HydraPrime"
HEADS_DIR="$HYDRA_DIR/heads"
CONFIG_DIR="$HYDRA_DIR/config"
LOG_DIR="$HYDRA_DIR/logs"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  🐉 HydraPrime Installer"
echo "  Three heads. One body. Total autonomy."
echo -e "${NC}"

# ── Step 0: Base dependencies ──────────────────────────────
echo -e "${YELLOW}[0/6] Installing base dependencies...${NC}"
pkg update -y -q
pkg install -y -q python python-pip git curl nodejs proot-distro rsvg2

# ── Step 1: Setup dirs ─────────────────────────────────────
echo -e "${YELLOW}[1/6] Setting up HydraPrime directories...${NC}"
mkdir -p "$HEADS_DIR" "$CONFIG_DIR" "$LOG_DIR"
mkdir -p "$HEADS_DIR/openclaw"
mkdir -p "$HEADS_DIR/hermes"
mkdir -p "$HEADS_DIR/openhuman"

# ── Step 2: HEAD 1 — OpenClaw ─────────────────────────────
echo -e "${YELLOW}[2/6] Installing Head 1: OpenClaw (Hardware)...${NC}"
cd "$HEADS_DIR/openclaw"

# Install termux tools for hardware access
pkg install -y -q termux-api

# Clone OpenClaw setup
if [ ! -d "openclaw-android-setup" ]; then
  git clone --depth=1 https://github.com/kevinleestites2-dev/OpenClaw-Android.git openclaw-android-setup
fi

cd openclaw-android-setup
chmod +x *.sh 2>/dev/null || true

# Run OpenClaw setup non-interactively
if command -v openclaw &>/dev/null; then
  echo -e "${GREEN}  ✅ OpenClaw already installed${NC}"
else
  bash setup_claw.sh 2>&1 | tee "$LOG_DIR/openclaw_install.log" || true
  source ~/.bashrc 2>/dev/null || true
fi

# Start OpenClaw service
sv up openclaw 2>/dev/null || true
termux-wake-lock 2>/dev/null || true
echo -e "${GREEN}  ✅ OpenClaw ready — Web UI: http://localhost:18789${NC}"

# ── Step 3: HEAD 2 — Hermes ───────────────────────────────
echo -e "${YELLOW}[3/6] Installing Head 2: Hermes (Brain)...${NC}"
cd "$HEADS_DIR/hermes"

# proot Ubuntu for Hermes
if ! proot-distro list | grep -q "ubuntu.*installed"; then
  proot-distro install ubuntu
fi

# Clone Hermes inside proot
proot-distro login ubuntu -- bash -c "
  apt-get update -qq
  apt-get install -y -qq python3 python3-pip git curl
  if [ ! -d /root/hermes ]; then
    git clone --depth=1 https://github.com/kevinleestites2-dev/Hermes-Agent-On-Android.git /root/hermes
  fi
  cd /root/hermes
  pip3 install -q -r requirements.txt 2>/dev/null || pip3 install -q hermes-agent 2>/dev/null || true
  echo 'Hermes dependencies ready'
" 2>&1 | tee "$LOG_DIR/hermes_install.log" | tail -5

echo -e "${GREEN}  ✅ Hermes ready — Gateway: http://localhost:8765${NC}"

# ── Step 4: HEAD 3 — OpenHuman ────────────────────────────
echo -e "${YELLOW}[4/6] Installing Head 3: OpenHuman (Context)...${NC}"
cd "$HEADS_DIR/openhuman"

if [ ! -d "openhuman" ]; then
  git clone --depth=1 https://github.com/kevinleestites2-dev/openhuman.git openhuman
fi

cd openhuman

# Install Node deps for OpenHuman core
if command -v npm &>/dev/null; then
  npm install --silent 2>&1 | tail -3 || true
fi

echo -e "${GREEN}  ✅ OpenHuman ready — Core: http://localhost:3000${NC}"

# ── Step 5: Hydra Bridge ──────────────────────────────────
echo -e "${YELLOW}[5/6] Installing HydraPrime Bridge...${NC}"
pip3 install -q flask requests python-dotenv aiohttp

# Copy bridge to home
cp "$HYDRA_DIR/core/hydra_bridge.py" "$HOME/hydra_bridge.py" 2>/dev/null || true
cp "$HYDRA_DIR/core/hydra_cli.py" "$HOME/hydra" 2>/dev/null || true
chmod +x "$HOME/hydra" 2>/dev/null || true

# Add hydra to PATH
if ! grep -q "HydraPrime" ~/.bashrc; then
  echo '' >> ~/.bashrc
  echo '# HydraPrime' >> ~/.bashrc
  echo 'export PATH="$HOME:$PATH"' >> ~/.bashrc
  echo 'export HYDRA_DIR="$HOME/HydraPrime"' >> ~/.bashrc
fi

echo -e "${GREEN}  ✅ Bridge ready${NC}"

# ── Step 6: Config ────────────────────────────────────────
echo -e "${YELLOW}[6/6] Writing default config...${NC}"
cat > "$CONFIG_DIR/hydra.env" << 'EOF'
# HydraPrime Configuration
# Fill in your API keys and model preferences

# ── Model (Hermes Brain) ──────────────────────────────────
HERMES_MODEL=ollama/gemma4:31b-cloud   # or openai/gpt-4o, anthropic/claude-3-5-sonnet
HERMES_GATEWAY_PORT=8765

# ── OpenClaw ──────────────────────────────────────────────
OPENCLAW_PORT=18789

# ── OpenHuman ─────────────────────────────────────────────
OPENHUMAN_PORT=3000

# ── Reporting ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=8616341142:AAGv9M_buIvZtzzDGUE5ikE4K9GTlZ9E5ik
TELEGRAM_CHAT_ID=7135054241

# ── API Keys (optional — Hermes uses these) ───────────────
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
EOF

echo -e "${GREEN}  ✅ Config written: $CONFIG_DIR/hydra.env${NC}"

# ── Done ──────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  🐉 HydraPrime Installation Complete${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Start all heads:    ${BOLD}hydra start${NC}"
echo -e "  Check status:       ${BOLD}hydra status${NC}"
echo -e "  Send a command:     ${BOLD}hydra think \"your task\"${NC}"
echo -e "  Hardware query:     ${BOLD}hydra sense gps${NC}"
echo -e "  Life context:       ${BOLD}hydra context today${NC}"
echo ""
echo -e "  Edit config:        ${BOLD}nano $CONFIG_DIR/hydra.env${NC}"
echo ""
source ~/.bashrc 2>/dev/null || true
