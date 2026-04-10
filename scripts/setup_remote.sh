#!/bin/bash
CRON_H=${1:-20}
CRON_M=${2:-00}
PROJECT_ROOT=$(pwd)

echo "--- Industrial Automated Update Setup ---"

# 1. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Install Dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install requests xlsxwriter

# 3. Secure .env template
if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    cat << 'EOF' > .env
# Bertual API Credentials
BERTUAL_CUIT=YOUR_CUIT_HERE
BERTUAL_PASSWORD=YOUR_PASSWORD_HERE
BERTUAL_CLIENT_ID=0112629

# GitHub Token
GITHUB_TOKEN=YOUR_TOKEN_HERE

# Telegram Credentials
TELEGRAM_TOKEN=YOUR_TELEGRAM_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID_HERE
EOF
    chmod 600 .env
fi

# 4. Schedule Cron Job
echo "Scheduling cron job for $CRON_H:$CRON_M..."
# Remove existing run_daily.sh entry to avoid duplicates
(crontab -l 2>/dev/null | grep -v 'run_daily.sh') | crontab -
# Add new entry
(crontab -l 2>/dev/null; echo "$CRON_M $CRON_H * * * /bin/bash $PROJECT_ROOT/scripts/run_daily.sh >> $PROJECT_ROOT/reports/cron_log.txt 2>&1") | crontab -

echo "Setup complete. Remember to fill your .env file!"
