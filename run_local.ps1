$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Virtual environment Python was not found at $pythonExe"
}

Write-Host "Starting BUFIA locally on http://0.0.0.0:8000" -ForegroundColor Green
Write-Host "Use your PC's Wi-Fi IP on another device, for example: http://192.168.1.8:8000" -ForegroundColor Cyan
Write-Host "Using stable no-reload mode for local debugging." -ForegroundColor Yellow
& $pythonExe -u manage.py runserver 0.0.0.0:8000 --noreload
