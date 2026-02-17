# Server Restart Instructions

## Problem
Multiple Python processes are running (12 processes detected). The Django server is likely running with old cached code.

## Solution: Restart Django Server

### Step 1: Stop All Python Processes
Run this command to stop all Python processes:

```powershell
Stop-Process -Name python -Force
```

### Step 2: Wait a moment
Wait 2-3 seconds for all processes to fully terminate.

### Step 3: Start Django Server Fresh
```powershell
python manage.py runserver
```

### Step 4: Clear Browser Cache
After the server starts:
- Press `Ctrl + Shift + Delete` to open clear browsing data
- Select "Cached images and files"
- Click "Clear data"

OR simply:
- Press `Ctrl + Shift + R` for hard refresh

### Step 5: Access the Page
Navigate to: `http://127.0.0.1:8000/machines/rentals/`

## What You Should See

### Statistics (at the top):
```
Total Pending: 0
Paid & Pending: 0
Unpaid: 0
With Payment Proof: 0
Confirmed Requests: 2  ← This should show 2
```

### Rental List:
```
Rental Requests (2)  ← This should show 2

[Two rental cards with light green background should appear here]
```

## If Still Not Working

### Check Server Output
Look at the terminal where Django is running. You should see:
```
System check identified no issues (0 silenced).
December 02, 2025 - 19:XX:XX
Django version X.X.X, using settings 'bufia_project.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Check for Errors
If you see any errors in the terminal, that's the issue. Common errors:
- Import errors
- Syntax errors
- Database errors

### Verify Data Still Exists
```powershell
python manage.py shell -c "from machines.models import Rental; print('Approved:', Rental.objects.filter(status='approved').count())"
```

Should output: `Approved: 2`

## Quick Command Sequence

Copy and paste these commands one by one:

```powershell
# 1. Stop all Python processes
Stop-Process -Name python -Force

# 2. Wait 3 seconds
Start-Sleep -Seconds 3

# 3. Verify data exists
python manage.py shell -c "from machines.models import Rental; print('Approved rentals:', Rental.objects.filter(status='approved').count())"

# 4. Start server
python manage.py runserver
```

Then:
1. Open browser
2. Press `Ctrl + Shift + R` to hard refresh
3. Navigate to `http://127.0.0.1:8000/machines/rentals/`
4. Check that "Confirmed Requests: 2" appears
5. Scroll down to see the 2 rental cards

## Debug Comment in Template

I've added a debug comment in the template. After restarting, view the page source (Ctrl+U) and look for:
```html
<!-- Debug: Total rentals = 2 -->
```

If this shows "Total rentals = 2", then the data is reaching the template correctly.

## Success Checklist

✅ All Python processes stopped
✅ Server restarted fresh
✅ Browser cache cleared
✅ Page shows "Confirmed Requests: 2"
✅ Page shows "Rental Requests (2)"
✅ Two rental cards visible with light green background
✅ Debug comment shows "Total rentals = 2"
