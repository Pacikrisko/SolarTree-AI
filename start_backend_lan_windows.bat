@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo First run start_backend_windows.bat to install dependencies.
  pause
  exit /b 1
)
echo This API will accept connections from your local network.
echo Only use on a trusted LAN. Do not forward port 8000 on your router.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
