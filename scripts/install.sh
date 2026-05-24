#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# HydraPrime — Unified Installer
# Three heads. One body. Total autonomy.
# OpenClaw (hardware) + Hermes (brain) + OpenHuman (context)
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[1;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

HYDRA_DIR="$HOME/HydraPrime"
CONFIG_DIR="$HYDRA_DIR/config"
LOG_DIR="$HYDRA_DIR/logs"

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║   🐉 HydraPrime — Unified Installer  ║"
echo "  ║   Three heads. One body.             ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

mkdir -p "$CONFIG_DIR" "$LOG_DIR"

# ─────────────────────────────────────────────────────────
# STEP 0 — Base dependencies
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[0/5] Installing base dependencies...${NC}"
export DEBIAN_FRONTEND=noninteractive
pkg update -y -o Dpkg::Options::="--force-confnew" 2>/dev/null || pkg update -y
pkg upgrade -y 2>/dev/null || true
pkg install -y git python nodejs-lts build-essential cmake clang ninja \
    pkg-config binutils termux-api termux-services proot-distro tmux nano \
    rust make libffi openssl ripgrep ffmpeg

# Fix TMPDIR (critical for Node/npm on Termux)
mkdir -p "$PREFIX/tmp" "$HOME/tmp"
touch ~/.bashrc
sed -i '/export TMPDIR=/d' ~/.bashrc
sed -i '/export TMP=/d' ~/.bashrc
sed -i '/export TEMP=/d' ~/.bashrc
echo 'export TMPDIR="$PREFIX/tmp"' >> ~/.bashrc
echo 'export TMP="$PREFIX/tmp"' >> ~/.bashrc
echo 'export TEMP="$PREFIX/tmp"' >> ~/.bashrc
export TMPDIR="$PREFIX/tmp"
export TMP="$PREFIX/tmp"
export TEMP="$PREFIX/tmp"

# Fix Node-GYP crash
mkdir -p ~/.gyp
echo "{'variables':{'android_ndk_path':''}}" > ~/.gyp/include.gypi

echo -e "${GREEN}  ✅ Base dependencies ready${NC}"

# ─────────────────────────────────────────────────────────
# STEP 1 — HEAD 1: OpenClaw (Hardware Layer)
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Installing Head 1: OpenClaw (Hardware)...${NC}"

# Install OpenClaw via npm
npm install -g openclaw@latest 2>&1 | tee "$LOG_DIR/openclaw_install.log" | tail -5

# Patch hardcoded /tmp paths (critical on Android)
TARGET_FILE="$PREFIX/lib/node_modules/openclaw/dist/entry.js"
if [ -f "$TARGET_FILE" ]; then
    sed -i "s|/tmp/openclaw|$PREFIX/tmp/openclaw|g" "$TARGET_FILE"
    echo -e "${GREEN}  ✅ Patched entry.js${NC}"
fi

# Setup background service
SERVICE_DIR="$PREFIX/var/service/openclaw"
OPENCLAW_LOG_DIR="$PREFIX/var/log/openclaw"
mkdir -p "$SERVICE_DIR/log" "$OPENCLAW_LOG_DIR"

cat > "$SERVICE_DIR/run" << SVCEOF
#!/data/data/com.termux/files/usr/bin/sh
export PATH=$PREFIX/bin:\$PATH
export TMPDIR=$PREFIX/tmp
exec openclaw gateway 2>&1
SVCEOF

cat > "$SERVICE_DIR/log/run" << LOGEOF
#!/data/data/com.termux/files/usr/bin/sh
exec svlogd -tt $OPENCLAW_LOG_DIR
LOGEOF

chmod +x "$SERVICE_DIR/run" "$SERVICE_DIR/log/run"

# Set SVDIR for service manager
sed -i '/export SVDIR=/d' ~/.bashrc
echo 'export SVDIR="$PREFIX/var/service"' >> ~/.bashrc
export SVDIR="$PREFIX/var/service"

service-daemon stop >/dev/null 2>&1 || true
service-daemon start >/dev/null 2>&1 || true
sleep 2
sv-enable openclaw 2>/dev/null || true

echo -e "${GREEN}  ✅ OpenClaw ready — Web UI: http://localhost:18789${NC}"
echo -e "${YELLOW}  ⚠️  Run 'openclaw onboard' first (say NO to daemon install — already done)${NC}"

# ─────────────────────────────────────────────────────────
# STEP 2 — HEAD 2: Hermes (Brain / Intelligence Layer)
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Installing Head 2: Hermes (Brain)...${NC}"

# Fix Python sysconfig for psutil on Python 3.13
_pyfile="$(find $PREFIX/lib/python3.* -name '_sysconfigdata*.py' 2>/dev/null | head -1)"
if [ -f "$_pyfile" ]; then
    cp "$_pyfile" "$_pyfile.backup" 2>/dev/null || true
    sed -i 's|-fno-openmp-implicit-rpath||g' "$_pyfile"
    rm -rf "$PREFIX/lib/python3."*/__pycache__ 2>/dev/null || true
fi

# Install Ubuntu via proot-distro (Hermes needs it)
if ! proot-distro list 2>/dev/null | grep -q "ubuntu"; then
    proot-distro install ubuntu
fi

# Install Hermes inside proot Ubuntu
proot-distro login ubuntu -- bash -c "
    export DEBIAN_FRONTEND=noninteractive
    apt update -qq && apt upgrade -y -qq -o Dpkg::Options::='--force-confold'
    apt install -y -qq python3 python3-pip python3-venv git curl build-essential nodejs npm

    if [ ! -d /root/hermes-agent ]; then
        git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git /root/hermes-agent
    fi

    cd /root/hermes-agent
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel -q
    pip install -e . -q
    ln -sf /root/hermes-agent/venv/bin/hermes /usr/local/bin/hermes 2>/dev/null || true
    echo 'Hermes installed OK'
" 2>&1 | tee "$LOG_DIR/hermes_install.log" | tail -8

echo -e "${GREEN}  ✅ Hermes ready${NC}"
echo -e "${YELLOW}  ⚠️  Run 'hermes setup' inside proot to configure model/API keys${NC}"

# ─────────────────────────────────────────────────────────
# STEP 3 — HEAD 3: OpenHuman (Context Layer)
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Installing Head 3: OpenHuman (Context)...${NC}"

OH_DIR="$HOME/openhuman"
if [ ! -d "$OH_DIR" ]; then
    git clone --depth=1 https://github.com/kevinleestites2-dev/openhuman.git "$OH_DIR"
fi

cd "$OH_DIR"

# Install Node dependencies
if [ -f "package.json" ]; then
    npm install --silent 2>&1 | tail -5 || true
fi

# Build if needed
if [ -f "package.json" ] && grep -q '"build"' package.json; then
    npm run build --silent 2>&1 | tail -5 || true
fi

echo -e "${GREEN}  ✅ OpenHuman ready — Core: http://localhost:3000${NC}"

# ─────────────────────────────────────────────────────────
# STEP 4 — HydraPrime Bridge
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Installing HydraPrime Bridge...${NC}"

pip install -q flask requests python-dotenv aiohttp 2>/dev/null || \
    pip3 install -q flask requests python-dotenv aiohttp

# Download bridge and CLI from HydraPrime repo
curl -fsSL "https://raw.githubusercontent.com/kevinleestites2-dev/HydraPrime/main/core/hydra_bridge.py" \
    -o "$HOME/hydra_bridge.py" 2>/dev/null || \
    echo -e "${YELLOW}  ⚠️  Clone repo manually if raw fetch fails${NC}"

curl -fsSL "https://raw.githubusercontent.com/kevinleestites2-dev/HydraPrime/main/core/hydra_cli.py" \
    -o "$HOME/hydra" 2>/dev/null || true

chmod +x "$HOME/hydra" 2>/dev/null || true

# Add to PATH
if ! grep -q "# HydraPrime" ~/.bashrc; then
    echo '' >> ~/.bashrc
    echo '# HydraPrime' >> ~/.bashrc
    echo 'export PATH="$HOME:$PATH"' >> ~/.bashrc
    echo 'export HYDRA_DIR="$HOME/HydraPrime"' >> ~/.bashrc
fi

echo -e "${GREEN}  ✅ Bridge ready — port 9999${NC}"

# ─────────────────────────────────────────────────────────
# STEP 5 — Config
# ─────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Writing config...${NC}"

cat > "$CONFIG_DIR/hydra.env" << 'CFGEOF'
# ═══════════════════════════════════════
# HydraPrime Configuration
# ═══════════════════════════════════════

# ── Hermes (Brain) ──────────────────────
# Model options:
#   ollama/gemma4:31b-cloud  (local, no API cost)
#   openai/gpt-4o
#   anthropic/claude-3-5-sonnet
HERMES_MODEL=ollama/gemma3:4b
HERMES_GATEWAY_PORT=8765

# ── OpenClaw (Hardware) ─────────────────
OPENCLAW_PORT=18789

# ── OpenHuman (Context) ─────────────────
OPENHUMAN_PORT=3000

# ── Hydra Bridge ────────────────────────
HYDRA_BRIDGE_PORT=9999

# ── Telegram Reporting ──────────────────
TELEGRAM_BOT_TOKEN=8616341142:AAGv9M_buIvZtzzDGUE5ikE4K9GTlZ9E5ik
TELEGRAM_CHAT_ID=7135054241

# ── API Keys (Hermes uses these) ────────
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
CFGEOF

echo -e "${GREEN}  ✅ Config: $CONFIG_DIR/hydra.env${NC}"

# ─────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────
source ~/.bashrc 2>/dev/null || true

echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  🐉 HydraPrime Installation Complete${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}REQUIRED first-time steps:${NC}"
echo -e "  1. ${BOLD}openclaw onboard${NC}              (say NO to daemon)"
echo -e "  2. ${BOLD}proot-distro login ubuntu${NC}"
echo -e "     ${BOLD}cd hermes-agent && source venv/bin/activate${NC}"
echo -e "     ${BOLD}hermes setup${NC}                  (configure your model)"
echo -e "     ${BOLD}exit${NC}"
echo ""
echo -e "  ${YELLOW}Then start everything:${NC}"
echo -e "  ${BOLD}hydra start${NC}"
echo ""
echo -e "  ${YELLOW}Commands:${NC}"
echo -e "  ${BOLD}hydra status${NC}                     check all heads"
echo -e "  ${BOLD}hydra execute \"task\"${NC}             full 3-head fusion"
echo -e "  ${BOLD}hydra think \"task\"${NC}               brain only"
echo -e "  ${BOLD}hydra sense gps${NC}                  hardware query"
echo -e "  ${BOLD}hydra context today${NC}              life context"
echo ""
