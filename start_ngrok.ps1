$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$candidatePaths = @(
    $env:NGROK_PATH,
    (Join-Path $projectRoot "ngrok.exe"),
    "C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe",
    "C:\ngrok\ngrok.exe"
) | Where-Object { $_ }

$ngrokExe = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $ngrokExe) {
    Write-Error @"
ngrok.exe was not found.

Set the NGROK_PATH environment variable or place ngrok.exe in one of these locations:
- $projectRoot\ngrok.exe
- C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe
- C:\ngrok\ngrok.exe
"@
}

Write-Host "Starting ngrok for BUFIA on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Using: $ngrokExe" -ForegroundColor Cyan
Write-Host "If you have not added your ngrok authtoken yet, run:" -ForegroundColor Yellow
Write-Host "`"$ngrokExe`" config add-authtoken YOUR_TOKEN" -ForegroundColor Yellow

& $ngrokExe http 8000
