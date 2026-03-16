# Operator Dashboard Setup Guide

## Overview
This guide will help you set up the operator dashboard and create operator accounts.

## Step 1: Create Operator Account

### Option A: Using Django Shell Script (Recommended)

1. Open terminal in your project directory
2. Run the script:
```bash
python manage.py shell < create_operator_account.py
```

3. You'll see output like:
```
============================================================
✅ OPERATOR ACCOUNT CREATED SUCCESSFULLY!
============================================================
Username:    operator1
Email:       operator@bufia.com
Password:    operator123
Full Name:   Juan Operator
Staff:       True
Superuser:   False
Active:      True
============================================================

📋 OPERATOR DASHBOARD ACCESS:
   URL: /machines/operator/dashboard/

🔑 LOGIN CREDENTIALS:
   Username: operator1
   Password: operator123

⚠️  IMPORTANT: Change the password after first login!
============================================================
```

### Option B: Using Django Admin

1. Login to Django admin: `/admin/`
2. Go to Users
3. Click "Add User"
4. Fill in:
   - Username: `operator1`
   - Password: `operator123`
5. Click "Save and continue editing"
6. In the Permissions section:
   - Check "Staff status" ✅
   - Leave "Superuser status" unchecked ❌
7. Fill in personal info:
   - First name: Juan
   - Last name: Operator
   - Email: operator@bufia.com
8. Click "Save"

### Option C: Using Python Shell

```python
python manage.py shell

from django.contrib.auth import get_user_model
User = get_user_model()

operator = User.objects.create_user(
    username='operator1',
    email='operator@bufia.com',
    password='operator123',
    first_name='Juan',
    last_name='Operator',
    is_staff=True,
    is_superuser=False,
    is_active=True
)

print(f"✅ Created operator: {operator.username}")
```

## Step 2: Access Operator Dashboard

1. **Logout** if you're logged in as admin
2. **Login** with operator credentials:
   - Username: `operator1`
   - Password: `operator123`
3. Navigate to: `/machines/operator/dashboard/`

## Step 3: Assign Jobs to Operator

### As Admin:

1. Login as admin
2. Go to Admin Dashboard: `/machines/admin/dashboard/`
3. Find an IN-KIND rental that's approved
4. Click on the rental to open approval page
5. In the "Assign Operator" section:
   - Select "Juan Operator" from dropdown
   - Click "Assign Operator"
6. Operator will receive notification

## Operator Dashboard Features

### Main Functions:

1. **View Assigned Jobs**
   - See all equipment jobs assigned to you
   - View job details (machine, member, dates, location)
   - Check current status

2. **Update Job Status**
   - Change status: Assigned → Traveling → Operating → Completed
   - Add notes about job progress
   - Track last update time

3. **Submit Harvest Reports** (IN-KIND only)
   - Enter total harvest in sacks (accepts decimals)
   - Add harvest notes
   - System auto-calculates BUFIA share
   - Admins receive instant notification

4. **View Statistics**
   - Assigned Jobs count
   - In Progress count
   - Awaiting Harvest count
   - Completed count

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  OPERATOR DASHBOARD                                     │
│  Manage your assigned equipment jobs                    │
└─────────────────────────────────────────────────────────┘

┌──────────┬──────────┬──────────┬──────────┐
│ Assigned │In Progress│ Awaiting │Completed │
│    5     │     2     │    1     │    3     │
└──────────┴──────────┴──────────┴──────────┘

┌─────────────────────────────────────────────────────────┐
│ 4-Wheel Drive Tractor                                   │
│ Juan Dela Cruz | Jan 15, 2024 - Jan 20, 2024          │
│ [IN-KIND] [In Progress] [Operating]                     │
├─────────────────────────────────────────────────────────┤
│ Machine Type: 4-Wheel Drive Tractor                    │
│ Field Location: Barangay San Jose                       │
│ Area: 2.5 hectares                                      │
│ Last Update: Jan 16, 10:30 AM                          │
├─────────────────────────────────────────────────────────┤
│ QUICK ACTIONS                                           │
│                                                         │
│ Update Job Status        │  Submit Harvest Report      │
│ ┌─────────────────────┐ │  ┌─────────────────────┐   │
│ │ Status: [Operating▼]│ │  │ Total Harvest: [___]│   │
│ │ Notes: [_________]  │ │  │ (sacks)             │   │
│ │ [Update Status]     │ │  │ Notes: [_________]  │   │
│ └─────────────────────┘ │  │ [Submit Harvest]    │   │
│                         │  └─────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Workflow Example

### Scenario: Operator completes a harvest job

1. **Operator logs in**
   - Goes to `/machines/operator/dashboard/`
   - Sees assigned job for "4-Wheel Drive Tractor"

2. **Updates status to "Operating"**
   - Selects "Operating" from status dropdown
   - Adds note: "Started plowing at 8:00 AM"
   - Clicks "Update Status"

3. **Completes harvest**
   - Counts total sacks: 21.3 sacks
   - Goes to "Submit Harvest Report" section
   - Enters: 21.3 in "Total Harvest" field
   - Adds note: "Good harvest, weather was favorable"
   - Clicks "Submit Harvest"

4. **System processes**
   - Calculates BUFIA share: 2.37 sacks
   - Calculates Member share: 18.93 sacks
   - Updates rental status to "Harvest Report Submitted"
   - Notifies all admins

5. **Admin confirms delivery**
   - Member delivers 2.37 sacks to BUFIA
   - Admin confirms in admin dashboard
   - Rental automatically completes
   - Machine becomes available

## URLs Reference

| Function | URL | Method |
|----------|-----|--------|
| Operator Dashboard | `/machines/operator/dashboard/` | GET |
| Update Job Status | `/machines/operator/rental/<id>/update/` | POST |
| Submit Harvest | `/machines/operator/rental/<id>/harvest/` | POST |

## Permissions

### Operator Can:
- ✅ View assigned jobs
- ✅ Update job status
- ✅ Submit harvest reports
- ✅ Add notes

### Operator Cannot:
- ❌ Approve/reject rentals
- ❌ Assign operators
- ❌ Confirm rice delivery
- ❌ View other operators' jobs
- ❌ Access admin dashboard

## Security Notes

1. **Change default password** after first login
2. **Operators must be staff** (`is_staff=True`)
3. **Operators should NOT be superusers** (`is_superuser=False`)
4. **Operators can only see their assigned jobs**
5. **All actions are logged** with timestamps

## Troubleshooting

### "You don't have permission to access the operator dashboard"
**Solution**: User must have `is_staff=True`
```python
user = User.objects.get(username='operator1')
user.is_staff = True
user.save()
```

### "No Jobs Assigned"
**Solution**: Admin needs to assign jobs to operator
1. Login as admin
2. Go to rental approval page
3. Assign operator to IN-KIND rental

### Harvest form not showing
**Solution**: Harvest submission only works for IN-KIND rentals
- Check rental payment type is "in_kind"
- Check rental is in "In Progress" state

## Creating Multiple Operators

To create additional operators, modify the script:

```python
# Operator 2
operator2 = User.objects.create_user(
    username='operator2',
    email='operator2@bufia.com',
    password='operator123',
    first_name='Pedro',
    last_name='Santos',
    is_staff=True,
    is_superuser=False,
    is_active=True
)

# Operator 3
operator3 = User.objects.create_user(
    username='operator3',
    email='operator3@bufia.com',
    password='operator123',
    first_name='Maria',
    last_name='Garcia',
    is_staff=True,
    is_superuser=False,
    is_active=True
)
```

## Files Reference

- **Dashboard Template**: `templates/machines/operator/operator_dashboard_clean.html`
- **Views**: `machines/operator_views.py`
- **URLs**: `machines/urls.py` (operator section)
- **Account Script**: `create_operator_account.py`

## Next Steps

1. ✅ Create operator account
2. ✅ Login as operator
3. ✅ Admin assigns IN-KIND rental to operator
4. ✅ Operator updates job status
5. ✅ Operator submits harvest report
6. ✅ Admin confirms rice delivery
7. ✅ Rental completes automatically
