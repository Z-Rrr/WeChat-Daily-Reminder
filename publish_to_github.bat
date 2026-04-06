@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=C:\Users\Administrator\Desktop\ZR\学习agent的代码项目"
set "REMOTE_URL=https://github.com/Z-Rrr/微信每日提醒.git"

echo [INFO] Project: %PROJECT_DIR%
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
  echo [ERROR] Cannot enter project directory.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Not a git repository.
  pause
  exit /b 1
)

git remote remove origin >nul 2>&1
git remote add origin "%REMOTE_URL%"

echo [INFO] Pushing to %REMOTE_URL%
git push -u origin master
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Push failed with code %EXIT_CODE%.
  echo [HINT] Check network/proxy and GitHub login, then retry.
) else (
  echo [INFO] Push succeeded.
)
pause
exit /b %EXIT_CODE%
