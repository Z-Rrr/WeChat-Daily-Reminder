#!/bin/bash
set -e

PROJECT_HOME="/home/azureuser/WeChat-Daily-Reminder"
VENV_PATH="$PROJECT_HOME/venv"
BOT_WEBHOOK_URL="${BOT_WEBHOOK_URL:-}"
BOT_API_KEY="${BOT_API_KEY:-}"
TIMEZONE_NAME="${TIMEZONE_NAME:-Asia/Shanghai}"
WEB_PORT="${WEB_PORT:-8000}"

if [ -z "$BOT_WEBHOOK_URL" ]; then
  echo "[ERROR] BOT_WEBHOOK_URL not set"
  exit 1
fi

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_CMD="python3.12"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  echo "[ERROR] python3 not found"
  exit 1
fi

if [ ! -d "$PROJECT_HOME" ]; then
  git clone https://github.com/Z-Rrr/WeChat-Daily-Reminder.git "$PROJECT_HOME"
else
  cd "$PROJECT_HOME"
  git pull origin master
fi

cd "$PROJECT_HOME"

if [ ! -f "$VENV_PATH/bin/activate" ]; then
  rm -rf "$VENV_PATH"
  "$PYTHON_CMD" -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

sudo tee /etc/systemd/system/wechat-reminder-web.service > /dev/null <<EOF
[Unit]
Description=WeChat Reminder Web + Scheduler
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=$PROJECT_HOME
Environment="PATH=$VENV_PATH/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="BOT_WEBHOOK_URL=$BOT_WEBHOOK_URL"
Environment="BOT_API_KEY=$BOT_API_KEY"
Environment="TIMEZONE_NAME=$TIMEZONE_NAME"
ExecStart=$VENV_PATH/bin/python web_main.py --host 0.0.0.0 --port $WEB_PORT --db-path data/reminders.db --timezone $TIMEZONE_NAME --bot-webhook-url $BOT_WEBHOOK_URL --bot-api-key $BOT_API_KEY
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wechat-reminder-web
sudo systemctl restart wechat-reminder-web

sudo systemctl status wechat-reminder-web --no-pager
