Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BUFIA System Reset for Implementation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will DELETE ALL transaction data:" -ForegroundColor Yellow
Write-Host "- Rentals and bookings" -ForegroundColor Yellow
Write-Host "- Payments and refunds" -ForegroundColor Yellow
Write-Host "- Rice sales and harvest shares" -ForegroundColor Yellow
Write-Host "- Maintenance records" -ForegroundColor Yellow
Write-Host "- Membership applications" -ForegroundColor Yellow
Write-Host "- Notifications" -ForegroundColor Yellow
Write-Host ""
Write-Host "Users, machines, sectors, and settings will be KEPT." -ForegroundColor Green
Write-Host ""
$confirmation = Read-Host "Type 'YES' to proceed with reset"

if ($confirmation -ne 'YES') {
    Write-Host "Reset cancelled." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "Running reset command..." -ForegroundColor Cyan
python manage.py reset_transactions --confirm

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Reset Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your system is now ready for fresh implementation." -ForegroundColor Green
Write-Host "All reports will start from zero." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
