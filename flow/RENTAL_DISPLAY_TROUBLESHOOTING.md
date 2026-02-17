# Rental Display Troubleshooting

## Issue
Approved rentals exist in the database but are not appearing in the rental dashboard.

## Diagnosis
- Database query confirmed: 2 approved rentals exist
- Code changes are in place
- Query logic is correct
- Likely cause: Browser cache or Django server not reloaded

## Solution Steps

### Step 1: Restart Django Development Server
The Django development server needs to be restarted to pick up the code changes.

**If server is running in a terminal:**
1. Press `Ctrl+C` to stop the server
2. Run: `python manage.py runserver`
3. Wait for "Starting development server" message

**If server is running as a background process:**
1. Find the process: `Get-Process python`
2. Stop it: `Stop-Process -Name python -Force`
3. Restart: `python manage.py runserver`

### Step 2: Clear Browser Cache
After restarting the server:

**Option A: Hard Refresh**
- Windows/Linux: `Ctrl + Shift + R` or `Ctrl + F5`
- Mac: `Cmd + Shift + R`

**Option B: Clear Cache in Browser**
1. Open Developer Tools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

**Option C: Incognito/Private Window**
- Open the site in an incognito/private window
- This bypasses all cache

### Step 3: Verify Data
Navigate to: `http://127.0.0.1:8000/machines/rentals/`

You should see:
- Statistics showing "Confirmed Requests: 2"
- Two rental cards with light green background
- Green left border on the cards
- Status badges showing "Confirmed" or "Approved"

### Step 4: Check Filter Settings
Make sure the status filter is set to "All Status" (not "Pending"):
- Look at the Status dropdown in the filters section
- It should show "All Status" selected
- If it shows "Pending", change it to "All Status" and click Filter

## Verification Commands

Run these to verify the data is correct:

```bash
# Check total rentals
python manage.py shell -c "from machines.models import Rental; print('Total:', Rental.objects.count())"

# Check by status
python manage.py shell -c "from machines.models import Rental; print('Pending:', Rental.objects.filter(status='pending').count()); print('Approved:', Rental.objects.filter(status='approved').count())"

# List all rentals
python manage.py shell -c "from machines.models import Rental; [print(f'{r.id}: {r.status} - {r.machine.name}') for r in Rental.objects.all()]"
```

## Expected Results

### Statistics Cards Should Show:
```
Total Pending: 0
Paid & Pending: 0
Unpaid: 0
With Payment Proof: 0
Confirmed Requests: 2
```

### Rental List Should Show:
```
┌─────────────────────────────────────────────────────┐
│ Rental Requests (2)                                 │
├─────────────────────────────────────────────────────┤
│ 🟢 [Light Green Background]                         │
│ Rental #1 - Approved                                │
│ Machine: [Machine Name]                             │
│ User: [User Name]                                   │
│ Status: Confirmed                                   │
├─────────────────────────────────────────────────────┤
│ 🟢 [Light Green Background]                         │
│ Rental #2 - Approved                                │
│ Machine: [Machine Name]                             │
│ User: [User Name]                                   │
│ Status: Confirmed                                   │
└─────────────────────────────────────────────────────┘
```

## If Still Not Working

### Check Django Server Output
Look for any errors in the terminal where Django is running:
- Import errors
- Template errors
- Database errors

### Check Browser Console
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for JavaScript errors
4. Look for failed network requests

### Verify URL
Make sure you're accessing the correct URL:
- Correct: `http://127.0.0.1:8000/machines/rentals/`
- Not: `http://127.0.0.1:8000/machines/admin/dashboard/`

### Check User Permissions
Make sure you're logged in as an admin user:
- User must be staff or superuser
- Check: `python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u = User.objects.get(username='your_username'); print('Is staff:', u.is_staff, 'Is superuser:', u.is_superuser)"`

## Common Issues

### Issue 1: "Rental Requests (0)"
- **Cause**: Filter is set to "Pending" instead of "All Status"
- **Fix**: Change Status filter to "All Status"

### Issue 2: Statistics show 0 for everything
- **Cause**: Browser cache showing old data
- **Fix**: Hard refresh (Ctrl+Shift+R)

### Issue 3: Server not reloading changes
- **Cause**: Django auto-reload not working
- **Fix**: Manually restart server

### Issue 4: Template not updating
- **Cause**: Template cache
- **Fix**: Restart server and clear browser cache

## Quick Fix Command Sequence

```bash
# 1. Stop any running Django servers
Stop-Process -Name python -Force

# 2. Verify data exists
python manage.py shell -c "from machines.models import Rental; print('Approved rentals:', Rental.objects.filter(status='approved').count())"

# 3. Start server
python manage.py runserver

# 4. Open browser in incognito mode
# Navigate to: http://127.0.0.1:8000/machines/rentals/
# Make sure Status filter is set to "All Status"
```

## Success Indicators

✅ Statistics show "Confirmed Requests: 2"
✅ Two rental cards visible in the list
✅ Cards have light green background
✅ Cards have green left border
✅ Status badges show "Confirmed" or approved status
✅ "Rental Requests (2)" shown at top of list

## Files to Check

If issues persist, verify these files have the correct code:

1. **machines/admin_views.py**
   - Line ~30: Should have `status_filter = request.GET.get('status', 'all')`
   - Line ~45: Should have the Case/When annotation for priority sorting

2. **templates/machines/rental_list.html**
   - Line ~50: Should have CSS for `.rental-card.approved`
   - Line ~184: Should have dynamic class assignment with approved/rejected checks

## Contact Information

If the issue persists after trying all steps:
1. Check Django server logs for errors
2. Check browser console for JavaScript errors
3. Verify database has the expected data
4. Try accessing from a different browser
