@echo off
echo ========================================
echo BUFIA System Reset for Implementation
echo ========================================
echo.
echo This will DELETE ALL transaction data:
echo - Rentals and bookings
echo - Payments and refunds
echo - Rice sales and harvest shares
echo - Maintenance records
echo - Membership applications
echo - Notifications
echo.
echo Users, machines, sectors, and settings will be KEPT.
echo.
pause
echo.
echo Running reset command...
python manage.py reset_transactions --confirm
echo.
echo ========================================
echo Reset Complete!
echo ========================================
echo.
echo Your system is now ready for fresh implementation.
echo All reports will start from zero.
echo.
pause
