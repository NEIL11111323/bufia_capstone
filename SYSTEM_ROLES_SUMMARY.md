# BUFIA System - User Roles Summary

## Overview
The BUFIA system has 4 distinct user roles, each with specific functions and access levels.

---

## 🔴 1. Admin (Superuser)

### Login Credentials
- **Username:** Admin (or your admin username)
- **Role:** Superuser
- **Access Level:** Full system access

### Unique Functions
- ✅ Manage all users and memberships
- ✅ Approve/reject membership applications
- ✅ Approve/reject rental requests
- ✅ Assign operators to machine jobs
- ✅ View all financial reports
- ✅ Manage payments and transactions
- ✅ Access admin panel
- ✅ Send system notifications
- ✅ View activity logs
- ✅ Manage machines and equipment
- ✅ Configure system settings

### Dashboard
- System-wide statistics
- All users' data
- All rentals and transactions
- Financial summaries
- Reports and analytics

---

## 🟢 2. Farmer (Regular User / Member)

### Login Credentials
- **Username:** (Individual member usernames)
- **Role:** Regular User
- **Access Level:** Personal data only

### Unique Functions
- ✅ Submit membership application
- ✅ Pay ₱500 membership fee
- ✅ Request machine rentals
- ✅ Pay rental fees (online or face-to-face)
- ✅ View own rental history
- ✅ Upload payment proofs
- ✅ Receive notifications
- ✅ View own profile and membership status
- ✅ Request irrigation services
- ✅ Book rice mill appointments

### Dashboard
- Personal statistics only
- Own rentals and payments
- Membership status
- Available machines
- Personal notifications

### Restrictions
- ❌ Cannot see other members' data
- ❌ Cannot access admin functions
- ❌ Cannot approve rentals
- ❌ Cannot view financial reports
- ❌ Cannot manage other users

---

## 🔵 3. Operator (Machine Operator)

### Login Credentials
- **Username:** `operator`
- **Password:** `operator123`
- **Email:** operator@bufia.com
- **Role:** Operator
- **Access Level:** Assigned jobs only

### Unique Functions
- ✅ View assigned machine jobs
- ✅ Update job status (Not Started → In Progress → Completed)
- ✅ Submit harvest reports for IN-KIND rentals
- ✅ Enter total sacks harvested
- ✅ View job history
- ✅ Receive job assignment notifications
- ✅ Update field notes and progress
- ✅ Track today's schedule

### Dashboard
**URL:** `/operator/dashboard/`

**Statistics:**
- Assigned jobs
- Today's jobs
- Jobs in progress
- Awaiting harvest report
- Completed jobs

### Harvest Reporting (IN-KIND)
When operator completes harvest:
1. Enter total sacks harvested
2. System calculates:
   - BUFIA share: floor(total / 9)
   - Member share: remaining sacks
3. Submit for admin verification

**Example:**
```
Total: 100 sacks
BUFIA: 11 sacks (100 ÷ 9 = 11.11, floored to 11)
Member: 89 sacks
```

### Restrictions
- ❌ Cannot see other operators' jobs
- ❌ Cannot access admin functions
- ❌ Cannot approve/reject rentals
- ❌ Cannot manage memberships
- ❌ Cannot view financial reports
- ❌ Cannot assign jobs
- ❌ Cannot modify pricing

---

## 🟡 4. Water Tender

### Login Credentials
- **Username:** (Assigned water tender usernames)
- **Role:** Water Tender
- **Access Level:** Irrigation management

### Unique Functions
- ✅ Manage irrigation requests
- ✅ Schedule water distribution
- ✅ Manage assigned sectors
- ✅ Update irrigation status
- ✅ View sector-specific data

### Dashboard
- Irrigation requests
- Sector assignments
- Water distribution schedule
- Sector statistics

---

## Role Comparison Table

| Feature | Admin | Farmer | Operator | Water Tender |
|---------|-------|--------|----------|--------------|
| View own data | ✅ | ✅ | ✅ | ✅ |
| View all users | ✅ | ❌ | ❌ | ❌ |
| Manage memberships | ✅ | ❌ | ❌ | ❌ |
| Request rentals | ✅ | ✅ | ❌ | ✅ |
| Approve rentals | ✅ | ❌ | ❌ | ❌ |
| Assign operators | ✅ | ❌ | ❌ | ❌ |
| Update job status | ✅ | ❌ | ✅ | ❌ |
| Submit harvest reports | ✅ | ❌ | ✅ | ❌ |
| View financial reports | ✅ | ❌ | ❌ | ❌ |
| Manage irrigation | ✅ | ❌ | ❌ | ✅ |
| Access admin panel | ✅ | ❌ | ❌ | ❌ |

---

## Workflow Examples

### Membership Application Workflow

1. **Farmer** submits application + pays ₱500
2. **Admin** reviews application
3. **Admin** marks payment as received (if face-to-face)
4. **Admin** approves membership
5. **Farmer** receives approval notification
6. **Farmer** can now request rentals

### Machine Rental Workflow (Cash)

1. **Farmer** requests machine rental
2. **Farmer** pays rental fee
3. **Admin** verifies payment
4. **Admin** approves rental
5. **Admin** assigns **Operator** to job
6. **Operator** completes job
7. **Operator** marks as completed
8. **Admin** confirms completion

### Machine Rental Workflow (IN-KIND)

1. **Farmer** requests harvester rental
2. **Admin** approves IN-KIND rental
3. **Admin** assigns **Operator** to job
4. **Operator** completes harvest
5. **Operator** submits harvest report (e.g., 100 sacks)
6. System calculates: BUFIA gets 11, Member gets 89
7. **Admin** verifies harvest report
8. **Admin** confirms BUFIA share received
9. Rental marked as fully completed

---

## Access URLs

### Common URLs
- Login: `/login/`
- Dashboard: `/dashboard/`
- Profile: `/profile/`
- Logout: `/logout/`

### Admin-Only URLs
- Admin Panel: `/admin/`
- User Management: `/users/`
- Membership Dashboard: `/users/`
- Reports: `/reports/`
- Payment Management: `/payments/`

### Farmer URLs
- Submit Membership: `/submit-membership-form/`
- Request Rental: `/machines/rentals/create/`
- My Rentals: `/machines/rentals/`
- Pay Membership: `/create-membership-payment/`

### Operator URLs
- Operator Dashboard: `/operator/dashboard/`
- Assigned Jobs: `/operator/jobs/`
- Submit Harvest: `/operator/harvest/<id>/`

---

## Security & Permissions

### Authentication
- All pages require login (`@login_required`)
- Role-based access control
- Session management

### Authorization
- Admin: `user.is_superuser` or `user.is_staff`
- Farmer: `user.is_verified` (for rentals)
- Operator: `user.is_operator()`
- Water Tender: `user.is_water_tender()`

### Data Access
- Users can only see their own data
- Admins can see all data
- Operators see only assigned jobs
- Water Tenders see assigned sectors

---

## Testing Accounts

### Admin Account
```
Username: Admin
Password: (your admin password)
Role: Superuser
```

### Operator Account
```
Username: operator
Password: operator123
Email: operator@bufia.com
Role: Operator
```

### Test Farmer Account
```
Username: (create via membership application)
Role: Regular User
Must complete membership process
```

---

## Summary

The BUFIA system implements a clear separation of concerns:

- **Admins** manage the entire system
- **Farmers** use services and pay fees
- **Operators** handle field operations and reporting
- **Water Tenders** manage irrigation

Each role has specific functions and cannot access other roles' exclusive features, ensuring security and proper workflow management.
