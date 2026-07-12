#!/usr/bin/env bash
#
# JobHunter — Automated Auto-run Setup Script
# Sets up virtual environment, installs dependencies, configures environment,
# and automatically registers the scheduler using systemd --user or cron.
#

set -e

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║         🔍 JobHunter Setup Script                 ║"
echo "║     Autonomous Job Scraping Agent                 ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📁 Project directory: ${SCRIPT_DIR}${NC}\n"

# Create logs directory
mkdir -p "${SCRIPT_DIR}/logs"
mkdir -p "${SCRIPT_DIR}/data"

# ─── Step 1: Python check ───
echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON=python3
    PY_VERSION=$($PYTHON --version 2>&1)
    echo -e "  ${GREEN}✓ Found: ${PY_VERSION}${NC}"
else
    echo -e "  ${RED}✗ Python 3 not found! Please install Python 3.10+${NC}"
    exit 1
fi

# ─── Step 2: Virtual environment ───
echo -e "\n${YELLOW}[2/5] Setting up virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "  ${GREEN}✓ Virtual environment already exists${NC}"
else
    $PYTHON -m venv .venv
    echo -e "  ${GREEN}✓ Created .venv${NC}"
fi

# Activate venv
source .venv/bin/activate
echo -e "  ${GREEN}✓ Activated .venv${NC}"

# ─── Step 3: Install dependencies ───
echo -e "\n${YELLOW}[3/5] Installing dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "  ${GREEN}✓ All dependencies installed${NC}"

# ─── Step 4: Configure .env ───
echo -e "\n${YELLOW}[4/5] Configuring environment...${NC}"
if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓ .env file already exists${NC}"
    # Check if webhook URL is set
    if grep -q "YOUR_ID/YOUR_TOKEN" .env 2>/dev/null; then
        echo -e "  ${RED}⚠  Discord webhook URL is not configured!${NC}"
        echo -e "  ${YELLOW}  Please edit .env and replace the placeholder webhook URL${NC}"
    fi
else
    cp .env.example .env
    echo -e "  ${GREEN}✓ Created .env from template${NC}"
    echo ""
    echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}Enter your Discord webhook URL${NC}"
    echo -e "  ${CYAN}(Server Settings > Integrations > Webhooks > Copy URL)${NC}"
    echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    read -rp "  Webhook URL (or press Enter to skip): " WEBHOOK_URL
    if [ -n "$WEBHOOK_URL" ]; then
        # Escape special characters for sed
        ESCAPED_URL=$(printf '%s\n' "$WEBHOOK_URL" | sed -e 's/[\/&]/\\&/g')
        sed -i "s|https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN|${ESCAPED_URL}|g" .env
        echo -e "  ${GREEN}✓ Webhook URL saved to .env${NC}"
    else
        echo -e "  ${YELLOW}⚠  Skipped — edit .env manually before running${NC}"
    fi
fi

# ─── Step 5: Setup Auto-run Scheduling ───
echo -e "\n${YELLOW}[5/5] Setting up auto-run scheduling...${NC}"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Ask user for frequency
echo -e "  ${CYAN}How often should JobHunter scan?${NC}"
echo -e "  ${BOLD}1)${NC} Every 2 hours (recommended)"
echo -e "  ${BOLD}2)${NC} Every hour"
echo -e "  ${BOLD}3)${NC} Every 30 minutes"
echo -e "  ${BOLD}4)${NC} Skip auto-run setup (manual runs only)"
echo ""
read -rp "  Choose [1-4] (default: 1): " AUTO_CHOICE

INTERVAL_HOURS=2
CRON_SCHEDULE="0 */2 * * *"
SYSTEMD_ON_ACTIVE="2h"

case "${AUTO_CHOICE:-1}" in
    1)
        INTERVAL_HOURS=2
        CRON_SCHEDULE="0 */2 * * *"
        SYSTEMD_ON_ACTIVE="2h"
        DESC="every 2 hours"
        ;;
    2)
        INTERVAL_HOURS=1
        CRON_SCHEDULE="0 * * * *"
        SYSTEMD_ON_ACTIVE="1h"
        DESC="every hour"
        ;;
    3)
        INTERVAL_HOURS=0.5
        CRON_SCHEDULE="*/30 * * * *"
        SYSTEMD_ON_ACTIVE="30min"
        DESC="every 30 minutes"
        ;;
    4)
        INTERVAL_HOURS=0
        DESC=""
        ;;
esac

# Update env file with scan interval
if [ "$INTERVAL_HOURS" != "0" ]; then
    sed -i "s/SCAN_INTERVAL_HOURS=.*/SCAN_INTERVAL_HOURS=${INTERVAL_HOURS}/g" .env || true
fi

# Detect Scheduling System
if [ -n "$DESC" ]; then
    if command -v crontab &>/dev/null; then
        echo -e "  ${GREEN}✓ Found cron scheduler.${NC}"
        CRON_CMD="${VENV_PYTHON} -m jobhunter.main >> ${SCRIPT_DIR}/logs/cron.log 2>&1"
        CRON_ENTRY="${CRON_SCHEDULE} cd ${SCRIPT_DIR} && ${CRON_CMD}"
        (crontab -l 2>/dev/null | grep -v "jobhunter.main" ; echo "$CRON_ENTRY") | crontab -
        echo -e "  ${GREEN}✓ Cron job installed to run ${DESC}.${NC}"
        echo -e "  ${CYAN}  Verify with: crontab -l${NC}"
    elif command -v systemctl &>/dev/null; then
        echo -e "  ${GREEN}✓ Found systemd scheduler. Configuring systemd --user service...${NC}"
        
        # Define directories
        SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
        mkdir -p "$SYSTEMD_USER_DIR"

        # Create systemd service
        cat <<EOF > "${SYSTEMD_USER_DIR}/jobhunter.service"
[Unit]
Description=JobHunter - Autonomous Job Scraping Agent
After=network.target

[Service]
Type=oneshot
ExecStart=${VENV_PYTHON} -m jobhunter.main
WorkingDirectory=${SCRIPT_DIR}
StandardOutput=append:${SCRIPT_DIR}/logs/systemd.log
StandardError=append:${SCRIPT_DIR}/logs/systemd.log
EOF

        # Create systemd timer
        cat <<EOF > "${SYSTEMD_USER_DIR}/jobhunter.timer"
[Unit]
Description=Run JobHunter Timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=${SYSTEMD_ON_ACTIVE}
Persistent=true

[Install]
WantedBy=timers.target
EOF

        # Reload systemd user daemon and enable/start timer
        systemctl --user daemon-reload
        systemctl --user enable jobhunter.timer
        systemctl --user start jobhunter.timer

        echo -e "  ${GREEN}✓ Systemd timer installed and started successfully (runs ${DESC}).${NC}"
        echo -e "  ${CYAN}  Check status with: systemctl --user status jobhunter.timer${NC}"
        echo -e "  ${CYAN}  Logs are written to: ${SCRIPT_DIR}/logs/systemd.log${NC}"
    else
        echo -e "  ${RED}✗ Neither cron nor systemd was found.${NC}"
        echo -e "  ${YELLOW}  Please run the agent manually or write a loop script.${NC}"
    fi
fi

# ─── Done! ───
echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✅ Setup Complete!                        ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}To run a manual scan now:${NC}"
echo -e "  ${CYAN}  cd ${SCRIPT_DIR}${NC}"
echo -e "  ${CYAN}  .venv/bin/python -m jobhunter.main${NC}"
echo ""

# Offer to run a test scan
read -rp "  Run a test scan now? [Y/n]: " RUN_NOW
if [[ "${RUN_NOW:-Y}" =~ ^[Yy]?$ ]]; then
    echo ""
    echo -e "${BLUE}🔍 Running test scan...${NC}"
    echo ""
    cd "$SCRIPT_DIR"
    .venv/bin/python -m jobhunter.main
fi
