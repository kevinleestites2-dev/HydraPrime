#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# HydraPrime Boot Daemon
# Installs a Termux:Boot script so HydraPrime auto-starts
# every time the phone boots.
# ============================================================
# 
# REQUIRES: Termux:Boot app installed from F-Droid
# After running this script:
#   1. Open Termux:Boot app once (to register it)
#   2. Give it "Run on startup" permission
#   3. Reboot — HydraPrime starts automatically
# ============================================================

BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/hydraprime.sh"

mkdir -p "$BOOT_DIR"

cat > "$BOOT_SCRIPT" << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# HydraPrime auto-start on boot

# Give Android time to fully boot
sleep 15

# Load environment
source ~/.bashrc 2>/dev/null || true

# Keep CPU awake
termux-wake-lock

# Start OpenClaw service
export SVDIR="$PREFIX/var/service"
service-daemon start 2>/dev/null || true
sleep 2
sv up openclaw 2>/dev/null || true

# Start Hermes gateway inside proot
proot-distro login ubuntu -- bash -c \
  "cd /root/hermes-agent && source venv/bin/activate && hermes gateway --port 8765 >> /tmp/hermes_gateway.log 2>&1 &" \
  2>/dev/null || true

# Start OpenHuman
if [ -d "$HOME/openhuman" ]; then
  cd "$HOME/openhuman"
  node dist/main.js >> "$HOME/HydraPrime/logs/openhuman.log" 2>&1 &
fi

# Start HydraPrime bridge
sleep 5
python3 "$HOME/hydra_bridge.py" >> "$HOME/HydraPrime/logs/bridge.log" 2>&1 &

echo "[$(date)] HydraPrime boot sequence complete" >> "$HOME/HydraPrime/logs/boot.log"
BOOTEOF

chmod +x "$BOOT_SCRIPT"

echo "✅ Boot daemon installed: $BOOT_SCRIPT"
echo ""
echo "Next steps:"
echo "  1. Install 'Termux:Boot' from F-Droid (if not already)"
echo "  2. Open the Termux:Boot app once to register it"
echo "  3. Grant it 'Run on startup' permission in Android settings"
echo "  4. Reboot your phone — HydraPrime will auto-start"
echo ""
echo "Manual check after reboot:"
echo "  hydra status"
