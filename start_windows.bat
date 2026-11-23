@echo off
chcp 65001 >nul
echo SolarTree AI - local application launcher
echo Two command windows will open. Keep them running.
start "SolarTree AI - Backend" "%~dp0start_backend_windows.bat"
start "SolarTree AI - Frontend" "%~dp0start_frontend_windows.bat"
echo Once both servers have started, open: http://127.0.0.1:5173
echo The first setup needs internet to install dependencies.
pause
