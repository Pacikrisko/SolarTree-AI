@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo [SolarTree AI] Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Python is missing. Install Python 3.11+ first.
    pause
    exit /b 1
  )
)
if not exist ".env" copy ".env.example" ".env" >nul
echo [SolarTree AI] Installing/updating backend dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check internet and Python version.
  pause
  exit /b 1
)
echo [SolarTree AI] Starting API: http://127.0.0.1:8000/docs
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
pause
