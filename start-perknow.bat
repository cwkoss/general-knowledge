@echo off
REM Quick start script for Perknow (Windows Command Prompt)
REM For PowerShell with better features, use: .\start-perknow.ps1

echo [PERKNOW] Starting Perknow Knowledge Management System...

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    exit /b 1
)

REM Check for uvicorn
uvicorn --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uvicorn not found. Run: pip install -r requirements.txt
    exit /b 1
)

REM Initialize directories
if not exist data mkdir data
if not exist export mkdir export
if not exist export\.git (
    echo [INFO] Initializing git in export/
    cd export && git init >nul 2>&1 && cd ..
)

REM Find available port (starting at 8003)
set PORT=8003
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%"') do (
    set PORT=8004
)

echo [INFO] Using port %PORT%
echo [INFO] Starting AI Gardener in background...

REM Start gardener in separate window
start "Perknow Gardener" cmd /k "python scripts/gardener_worker.py"

echo [INFO] Starting web server...
echo [INFO] Press Ctrl+C to stop, then close the gardener window
echo.

REM Start web server
uvicorn perknow.main:app --host 0.0.0.0 --port %PORT% --reload

echo.
echo [PERKNOW] Server stopped.
