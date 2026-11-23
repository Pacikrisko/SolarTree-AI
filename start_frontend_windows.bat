@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo [SolarTree AI] Installing frontend dependencies...
  call npm install
  if errorlevel 1 (
    echo npm install failed. Install Node.js 22.12+ and check internet.
    pause
    exit /b 1
  )
)
echo [SolarTree AI] Starting frontend: http://127.0.0.1:5173
call npm run dev
pause
