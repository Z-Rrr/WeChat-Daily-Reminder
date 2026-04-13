@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo =========================================================
echo WeChat Gateway Server Startup with ngrok Tunneling
echo =========================================================
echo.

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv312\Scripts\python.exe"
set "NGROK_API_KEY=your-ngrok-auth-token-here"
set "GATEWAY_API_KEY=wechat-gateway-secret-key-2026"

REM 检查 Python 环境
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at %PYTHON_EXE%
    echo [HINT] Create venv first:
    echo        uv venv --python 3.12 .venv312
    echo        .\.venv312\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

REM 检查 ngrok
ngrok --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ngrok not found. Please install it first:
    echo        https://ngrok.com/download
    echo.
    echo After download, add ngrok to PATH or run from this directory.
    pause
    exit /b 1
)

REM 显示配置信息
echo [INFO] Starting gateway server...
echo [INFO] Gateway API Key: %GATEWAY_API_KEY%
echo.

REM 在后台启动 ngrok（如果需要认证）
echo [INFO] Starting ngrok tunnel...
if "%NGROK_API_KEY%" neq "your-ngrok-auth-token-here" (
    ngrok config add-authtoken "%NGROK_API_KEY%" >nul 2>&1
)
start "ngrok" ngrok http 5000

REM 给 ngrok 一点时间启动
timeout /t 2 /nobreak

REM 启动网关服务
cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" gateway_server.py --host 127.0.0.1 --port 5000 --api-key "%GATEWAY_API_KEY%"

pause
