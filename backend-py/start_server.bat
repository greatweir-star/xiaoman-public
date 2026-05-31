@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo ==========================================
echo Xiaoman backend
echo Python: %PYTHON%
echo ==========================================

echo [1/3] Checking dependencies...
"%PYTHON%" -c "import lancedb" 2>nul
if errorlevel 1 (
    echo [1/3] Installing dependencies...
    "%PYTHON%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
) else (
    echo [1/3] Dependencies already installed.
)

echo [2/3] Checking environment...
if "%LLM_API_KEY%"=="" (
    echo [warning] LLM_API_KEY is not set. Real LLM calls need this environment variable.
)

echo [3/3] Starting server...
cd /d "%SCRIPT_DIR%"
"%PYTHON%" main.py

pause
