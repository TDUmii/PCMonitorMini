@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -c "import psutil, customtkinter" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto error
)
start "" ".venv\Scripts\pythonw.exe" "app.py"
exit /b 0
:error
echo Khong khoi dong duoc. Hay cai Python 3 voi tuy chon Tcl/Tk va thu lai.
pause
exit /b 1
