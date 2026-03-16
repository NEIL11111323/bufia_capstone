# 🎯 ROLE-BASED SYSTEM IMPLEMENTATION PLAN

## Current Status

✅ **GOOD NEWS**: Your User model ALREADY has a `role` field!

```python
class CustomUser(AbstractUser):
    SUPERUSER = 'superuser'
    REGULAR_USER = 'regular_user'
    WATER_TENDER = 'water_tender'
    OPERATOR = 'operator'
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=REGULAR_USER,
    )
```

## Problem

The system is currently using `is_staff` to identify operators, which causes confusion:
- `is_staff` is a Django built-in for admin panel access
- Operators are being identified by `is_staff=True`
- This mixes admin permissions with operator roles

## Solution

Use the existing `role` field properly and create clean separation.

---

## 1️⃣ Three Clear Roles

| Role | Purpose | Dashboard | Navigation |
|------|---------|-----------|------------|
| **Admin** | System management | Admin Dashboard | Full system access |
| **Farmer** | Request services | Farmer Dashboard | Request equipment, view rentals |
| **Operator** | Execute jobs | Operator Dashboard | View jobs, update status, record harvest |

---

## 2️⃣ Role Detection Functions

### Current (Using is_staff - PROBLEMATIC):
```python
def _is_operator_user(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)
```

### Recommended (Using role field - CLEAN):
```python
def _is_operator_user(user):
    return user.is_authenticated and user.role == 'operator'

def _is_admin_user(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'superuser')

def _is_farmer_user(user):
    return user.is_authenticated and user.role == 'regular_user'
```

---

## 3️⃣ Dashboard Routing

### Current Implementation:
```python
@login_required
def dashboard(request):
    user = request.user
    
    # Redirect operators to their specific dashboard
    if user.is_staff and not user.is_superuser:
        return redirect('machines:operator_dashboard')
    
    # ... rest of code
```

### Recommended Implementation:
```python
@login_required
def dashboard(request):
    user = request.user
    
    # Route based on role field
    if user.role == 'operator':
        return redirect('machines:operator_dashboard')
    elif user.role == 'superuser' or user.is_superuser:
        return redirect('admin_dashboard')
    elif user.role == 'regular_user':
        return redirect('farmer_dashboard')
    elif user.role == 'water_tender':
        return redirect('water_tender_dashboard')
    else:
        # Default to farmer dashboard
        return redirect('farmer_dashboard')
```

---

## 4️⃣ Template Structure

### Current Structure:
```
templates/
├── base.html (used by everyone)
├── base_operator_v2.html (operator only)
├── machines/operator/ (operator templates)
└── users/dashboard.html (mixed admin/farmer)
```

### Recommended Structure:
```
templates/
├── base.html (common base)
├── base_admin.html (extends base.html)
├── base_farmer.html (extends base.html)
├── base_operator.html (extends base.html)
│
├── admin/
│   ├── dashboard.html
│   ├── members.html
│   ├── machines.html
│   └── reports.html
│
├── farmer/
│   ├── dashboard.html
│   ├── requests.html
│   ├── rentals.html
│   └── payments.html
│
└── operator/
    ├── dashboard.html
    ├── jobs.html
    ├── harvest.html
    └── machines.html
```

---

## 5️⃣ Navigation Per Role

### Admin Navigation:
```
Dashboard
Membership Management
  - Applications
  - Verified Members
  - Sectors
Equipment Management
  - Machines
  - Rentals
  - Maintenance
Operator Management
  - Operators
  - Assignments
Reports
  - Financial
  - Harvest
  - Membership
```

### Farmer Navigation:
```
Dashboard
Request Equipment
My Rentals
Rice Mill Appointment
Irrigation Request
Payments
Profile
```

### Operator Navigation:
```
Dashboard
My Jobs
  - All Jobs
  - Ongoing Jobs
  - Awaiting Harvest
  - Completed Jobs
Payments
  - In-Kind Payments
Equipment
  - View Machines
Notifications
```

---

## 6️⃣ Migration Plan

### Phase 1: Update Operator Detection (PRIORITY)
Change all `_is_operator_user()` functions to use `role` field:

**Files to Update**:
- `machines/operator_views.py`
- `machines/operator_notification_views.py`
- `machines/operator_decision_views.py`

**Change**:
```python
# OLD
def _is_operator_user(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

# NEW
def _is_operator_user(user):
    return user.is_authenticated and user.role == CustomUser.OPERATOR
```

### Phase 2: Update Existing Operators
Set the `role` field for existing operator accounts:

```python
# Script: update_operator_roles.py
from django.contrib.auth import get_user_model

User = get_user_model()

# Update operator1 and operator2
operators = User.objects.filter(username__in=['operator1', 'operator2', 'micho@gmail.com'])
for op in operators:
    op.role = 'operator'
    op.save()
    print(f"Updated {op.username} to operator role")
```

### Phase 3: Update Dashboard Routing
Update `users/views.py::dashboard()` to use role-based routing.

### Phase 4: Separate Templates (OPTIONAL)
Create separate base templates for each role if needed.

---

## 7️⃣ Current Operator Accounts

Need to update these accounts to use `role='operator'`:

| Username | Current Status | Action Needed |
|----------|---------------|---------------|
| operator1 | is_staff=True | Set role='operator' |
| operator2 | is_staff=True | Set role='operator' |
| micho@gmail.com | is_staff=True | Set role='operator' |

---

## 8️⃣ Benefits of Role-Based System

✅ **Clear Separation**: Each role has distinct permissions
✅ **No Confusion**: `is_staff` only for Django admin access
✅ **Easy to Extend**: Add new roles easily (e.g., 'supervisor')
✅ **Better Security**: Role-based access control
✅ **Cleaner Code**: `if user.role == 'operator'` is clearer than `if user.is_staff and not user.is_superuser`
✅ **Scalable**: Easy to add more roles in future

---

## 9️⃣ Implementation Priority

### HIGH PRIORITY (Do Now):
1. ✅ Update `_is_operator_user()` functions to use `role` field
2. ✅ Update existing operator accounts to set `role='operator'`
3. ✅ Update dashboard routing to use `role` field

### MEDIUM PRIORITY (Do Soon):
4. Create separate admin/farmer/operator helper functions
5. Update all views to use role-based checks
6. Add role field to user creation forms

### LOW PRIORITY (Nice to Have):
7. Separate base templates per role
8. Reorganize template structure
9. Add role-based middleware

---

## 🔟 Testing Plan

### Test 1: Operator Access
```python
# Login as operator1
# Expected: See operator dashboard with clean navigation
# Expected: Can update job status
# Expected: Can record harvest
# Expected: Cannot see admin features
```

### Test 2: Admin Access
```python
# Login as admin
# Expected: See admin dashboard
# Expected: Can manage all features
# Expected: Can assign operators
```

### Test 3: Farmer Access
```python
# Login as regular user
# Expected: See farmer dashboard
# Expected: Can request equipment
# Expected: Cannot see operator/admin features
```

---

## Summary

Your system ALREADY has the `role` field infrastructure! We just need to:
1. Stop using `is_staff` for operator detection
2. Use the existing `role` field instead
3. Update existing operator accounts
4. Clean up the routing logic

This will give you a clean, scalable, role-based system with proper separation of concerns.
