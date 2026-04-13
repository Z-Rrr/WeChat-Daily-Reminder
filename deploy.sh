#!/bin/bash
# Azure Linux 服务器部署脚本
# 用于自动化部署 WeChat Daily Reminder 到云端

set -e  # 任何错误立即退出

PROJECT_HOME="/home/azureuser/WeChat-Daily-Reminder"
VENV_PATH="$PROJECT_HOME/venv"
LOG_DIR="/var/log/wechat-reminder"
NGROK_URL="${NGROK_URL:-}"
GATEWAY_API_KEY="${GATEWAY_API_KEY:-}"

echo "======================================================"
echo "WeChat Daily Reminder - Azure Linux Deployment"
echo "======================================================"
echo ""

# 检查必要参数
if [ -z "$NGROK_URL" ]; then
    echo "[ERROR] NGROK_URL not set. Usage:"
    echo "        export NGROK_URL=https://abc123xyz.ngrok.io"
    echo "        export GATEWAY_API_KEY=your-gateway-key"
    echo "        bash deploy.sh"
    exit 1
fi

if [ -z "$GATEWAY_API_KEY" ]; then
    echo "[ERROR] GATEWAY_API_KEY not set."
    exit 1
fi

# 克隆或更新项目
if [ ! -d "$PROJECT_HOME" ]; then
    echo "[INFO] Cloning project..."
    git clone https://github.com/Z-Rrr/WeChat-Daily-Reminder.git "$PROJECT_HOME"
else
    echo "[INFO] Updating project..."
    cd "$PROJECT_HOME"
    git pull origin master
fi

cd "$PROJECT_HOME"

# 创建虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "[INFO] Creating Python virtual environment..."
    python3.12 -m venv "$VENV_PATH"
fi

# 激活虚拟环境并安装依赖
source "$VENV_PATH/bin/activate"
echo "[INFO] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建日志目录
sudo mkdir -p "$LOG_DIR"
sudo chown -R azureuser:azureuser "$LOG_DIR"

# 创建配置文件
if [ ! -f "config.json" ]; then
    echo "[INFO] Creating config.json..."
    cat > config.json <<EOF
{
  "timezone": "Asia/Shanghai",
  "daily_plan": {
    "path": "daily_plan.md",
    "target_date_offset_days": 1
  },
  "jobs": []
}
EOF
fi

# 创建每日计划文件
if [ ! -f "daily_plan.md" ]; then
    echo "[INFO] Creating daily_plan.md..."
    cat > daily_plan.md <<'EOF'
## 2026-04-14

- 08:30 | 文件传输助手 | 早上好，今天先完成最重要的三件事。
- 12:20 | 文件传输助手 | 午间记得喝水、走动一下。
- 18:30 | 文件传输助手 | 下班前收尾今天的工作。
EOF
fi

# 测试连接
echo "[INFO] Testing gateway connection..."
response=$(curl -s -w "%{http_code}" -o /dev/null \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  "$NGROK_URL/health")

if [ "$response" = "200" ]; then
    echo "[SUCCESS] Gateway connection OK"
else
    echo "[WARNING] Gateway health check returned HTTP $response"
    echo "[WARNING] This may be due to network latency. Continuing..."
fi

# 测试单次发送
echo "[INFO] Running test send..."
"$VENV_PATH/bin/python" main.py -c config.json --preview morning-greeting || true

# 创建 systemd 服务
echo "[INFO] Setting up systemd service..."
sudo tee /etc/systemd/system/wechat-reminder.service > /dev/null <<EOF
[Unit]
Description=WeChat Daily Reminder Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=$PROJECT_HOME
Environment="PATH=$VENV_PATH/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$VENV_PATH/bin/python main.py -c config.json \\
  --gateway-url $NGROK_URL \\
  --gateway-api-key $GATEWAY_API_KEY
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wechat-reminder
sudo systemctl restart wechat-reminder

echo ""
echo "======================================================"
echo "Deployment Complete!"
echo "======================================================"
echo ""
echo "Service Status:"
sudo systemctl status wechat-reminder --no-pager
echo ""
echo "Recent Logs:"
sudo journalctl -u wechat-reminder -n 10 --no-pager
echo ""
echo "To view live logs:"
echo "  sudo journalctl -u wechat-reminder -f"
echo ""
echo "To stop/start the service:"
echo "  sudo systemctl stop wechat-reminder"
echo "  sudo systemctl start wechat-reminder"
