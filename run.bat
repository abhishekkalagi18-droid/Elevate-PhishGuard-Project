@echo off
cd /d "%~dp0"
title PhishGuard Enterprise Lab

if exist venv\Scripts\python.exe (
    echo [PhishGuard] Starting using local virtual environment...
    venv\Scripts\python.exe app.py
) else (
    echo [PhishGuard] Starting using system Python...
    python app.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] Failed to start PhishGuard.
    echo Please run: python -m pip install -r requirements.txt
    pause
)
