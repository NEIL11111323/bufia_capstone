# PowerShell script to cleanly restart Django server
# Run this script to fix template caching issues

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "DJANGO CLEAN RESTART SCRIPT"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

# Step 1: Kill any running Django processes
Write-Host "Step 1: Stopping any running Django processes..."
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force
    Write-Host "✅ Stopped $($pythonProcesses.Count) Python process(es)"
} else {
    Write-Host "✅ No Python processes running"
}
Write-Host ""

# Step 2: Clear __pycache__ folders
Write-Host "Step 2: Clearing Python cache folders..."
$cacheCount = 0
Get-ChildItem -Recurse -Filter __pycache__ -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $cacheCount++
}
Write-Host "✅ Cleared $cacheCount __pycache__ folder(s)"
Write-Host ""

# Step 3: Verify template exists
Write-Host "Step 3: Verifying template file..."
$templatePath = "templates\machines\admin\operator_overview.html"
if (Test-Path $templatePath) {
    $fileSize = (Get-Item $templatePath).Length
    Write-Host "✅ Template exists: $templatePath ($fileSize bytes)"
} else {
    Write-Host "❌ Template NOT found: $templatePath"
    Write-Host "   Please create the template first!"
    exit 1
}
Write-Host ""

# Step 4: Instructions for restart
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "READY TO RESTART!"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
Write-Host "Now run this command to start Django:"
Write-Host ""
Write-Host "    python manage.py runserver" -ForegroundColor Green
Write-Host ""
Write-Host "Then navigate to:"
Write-Host "    http://127.0.0.1:8000/machines/operators/overview/" -ForegroundColor Cyan
Write-Host ""
Write-Host "The operator overview page should load successfully!"
Write-Host ""
