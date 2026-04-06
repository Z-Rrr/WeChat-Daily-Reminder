@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=C:\Users\Administrator\Desktop\ZR\学习agent的代码项目"
set "PYTHON_EXE=%PROJECT_DIR%\.venv312\Scripts\python.exe"
set "TEST_JOB=evening-greeting"

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

title WeChat Scheduler Test Once
echo [INFO] Sending one test message by job: %TEST_JOB%
echo.

"%PYTHON_EXE%" main.py -c config.json --once %TEST_JOB%
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [ERROR] Test failed, exit code %EXIT_CODE%.
) else (
    echo [INFO] Test message sent.
)
pause
exit /b %EXIT_CODE%
