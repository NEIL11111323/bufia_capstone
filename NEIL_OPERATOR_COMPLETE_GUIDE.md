# Neil Operator - Complete Guide

## Understanding the System

### Roles:
- **Admin/Superuser**: You - can assign operators to jobs
- **Operator**: Neil - receives job assignments and manages them

## Complete Workflow

### Step 1: Verify Neil is Set Up as Operator

Run this command to check:
```bash
python verify_neil_operator.py
```

This will show:
- ✅ Neil's account details
- ✅ His role (should be 'operator')
- ✅ Any jobs assigned to him
- ✅ Instructions if something is wrong

### Step 2: Assign a Job to Neil (As Admin)

1. **Login as Admin**
   - Use your admin credentials

2. **Go to Admin Dashboard**
   - Navigate to: `http://127.0.0.1:8000/machines/admin/dashboard/`

3. **Find a Rental to Approve**
   - Look for pending rentals
   - Click "Approve" or "Review" button

4. **Assign Neil as Operator**
   - On the approval page, scroll to "Assign Operator" section
   - Select "neil" from the dropdown
   - Click "Assign Operator" button
   - You'll see success message: "Assigned neil to this rental"

5. **Approve the Rental**
   - Complete the approval process
   - The rental status changes to "approved"

### Step 3: Neil Views His Assignment

1. **Neil Logs In**
   - Username: `neil`
   - Password: (neil's password)

2. **Neil Goes to Dashboard**
   - Automatically redirected to: `/machines/operator/dashboard/`
   - OR click "Dashboard" in sidebar

3. **Neil Sees His Jobs**
   - Dashboard shows:
     - Active Jobs count
     - In Progress count
     - Completed count
   - Recent jobs list shows assigned rentals

4. **Neil Can:**
   - View all jobs: Click "View All" or go to "All Jobs" in sidebar
   - See job details: Click on any job
   - Update job status: Mark as traveling, operating, etc.
   - Submit harvest reports: When job is complete
   - View notifications: Check for new assignments

## Troubleshooting

### Problem: Neil doesn't see assigned jobs

**Check 1: Is Neil set up correctly?**
```bash
python verify_neil_operator.py
```

Should show:
- Role: operator
- Is Staff: True
- Is Active: True

**Check 2: Was the job actually assigned?**
- Login as admin
- Go to the rental detail
- Check if "Assigned Operator" shows "neil"

**Check 3: Is the rental status correct?**
- Jobs only show if status is NOT: completed, cancelled, or rejected
- Check rental status in admin dashboard

**Check 4: Did you restart Django server?**
```bash
# Stop server (Ctrl+C)
# Restart
python manage.py runserver
```

### Problem: Can't assign Neil to a job

**Solution**: Make sure you're logged in as admin/superuser, not as an operator.

### Problem: Neil's role is wrong

**Fix with Django shell**:
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()

neil = User.objects.get(username='neil')
neil.role = User.OPERATOR
neil.is_staff = True
neil.is_active = True
neil.save()

print(f"✅ Neil is now an operator")
```

## Quick Reference

### URLs

**Admin URLs:**
- Dashboard: `/machines/admin/dashboard/`
- Operator Overview: `/machines/operators/overview/`
- Rental Approval: `/machines/admin/rental/<id>/approve/`

**Operator URLs (Neil):**
- Dashboard: `/machines/operator/dashboard/`
- All Jobs: `/machines/operator/jobs/`
- Job Detail: `/machines/operator/jobs/<id>/`
- Ongoing Jobs: `/machines/operator/jobs/ongoing/`
- Awaiting Harvest: `/machines/operator/jobs/awaiting-harvest/`
- Completed Jobs: `/machines/operator/jobs/completed/`
- Machines: `/machines/operator/machines/`
- Notifications: `/machines/operator/notifications/`

### Operator Dashboard Features

When Neil logs in, he can:

1. **View Statistics**
   - Active jobs count
   - In progress count
   - Completed jobs count

2. **Manage Jobs**
   - See all assigned jobs
   - View job details (machine, member, location, area)
   - Update job status (traveling, operating, completed)
   - Submit harvest reports

3. **Track Progress**
   - Filter by status (ongoing, awaiting harvest, completed)
   - View job history
   - Check notifications

4. **Submit Reports**
   - Harvest quantity
   - Completion notes
   - Photos (if enabled)

## Testing the Complete Flow

1. **Verify Neil** (run script):
   ```bash
   python verify_neil_operator.py
   ```

2. **Assign Job** (as admin):
   - Login as admin
   - Approve rental
   - Assign to neil

3. **Check Dashboard** (as neil):
   - Login as neil
   - Go to dashboard
   - See assigned job

4. **Update Status** (as neil):
   - Click on job
   - Update status to "traveling" or "operating"
   - Submit when complete

---

**Status**: System ready for operator assignments
**Next Step**: Run `python verify_neil_operator.py` to check Neil's setup
**Then**: Restart Django server and test the workflow
