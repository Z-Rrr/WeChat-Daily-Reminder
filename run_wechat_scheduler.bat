@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=C:\Users\Administrator\Desktop\ZR\学习agent的代码项目"
set "PYTHON_EXE=%PROJECT_DIR%\.venv312\Scripts\python.exe"

echo [INFO] Project: %PROJECT_DIR%
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo [ERROR] Cannot enter project directory.
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    echo [HINT] Please create the environment first:
    echo        uv venv --python 3.12 .venv312
    echo        .\.venv312\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

title WeChat Scheduler
echo [INFO] Starting WeChat scheduler...
echo [INFO] Press Ctrl+C in this window to stop.
echo.

"%PYTHON_EXE%" main.py -c config.json
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [ERROR] Program exited with code %EXIT_CODE%.
) else (
    echo [INFO] Program stopped.
)
pause
exit /b %EXIT_CODE%
