@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "start_project.ps1"
echo.
echo Press any key to exit this launcher...
pause >nul
