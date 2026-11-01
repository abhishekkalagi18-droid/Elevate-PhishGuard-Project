# PhishGuard PowerShell Launcher
Set-Location $PSScriptRoot

if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "[PhishGuard] Starting via local virtual environment..." -ForegroundColor Cyan
    & ".\venv\Scripts\python.exe" app.py
} elseif (Test-Path "C:\Users\Abhishek\AppData\Local\Programs\Python\Python312\python.exe") {
    Write-Host "[PhishGuard] Starting via Python 3.12..." -ForegroundColor Cyan
    & "C:\Users\Abhishek\AppData\Local\Programs\Python\Python312\python.exe" app.py
} else {
    Write-Host "[PhishGuard] Starting via system Python..." -ForegroundColor Cyan
    python app.py
}
