@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
if not exist "%PYTHON%" set PYTHON=python
if "%LLM_API_KEY%"=="" echo [xiaoman] LLM_API_KEY is not set; set it in your shell or .env before production use.
cd /d "%SCRIPT_DIR%"
"%PYTHON%" main.py
