# Operator Role Guide - BUFIA System

## Overview
The Operator role is designed for machine operators who handle field operations and harvest reporting. This role has unique functions separate from Admin and Farmer roles.

## Account Details
- **Username:** `operator`
- **Password:** `operator123`
- **Email:** operator@bufia.com
- **Role:** Operator
- **Login URL:** http://127.0.0.1:8000/login/

---

## Role Comparison

### 🔴 Admin (Superuser)
- Manage all users and memberships
- Approve/reject rental requests
- View all financial reports
- Assign operators to jobs
- Full system access

### 🟢 Farmer (Regular User)
- Submit membership applications
- Request machine rentals
- Pay rental fees
- View own rental history
- Receive notifications

### 🔵 Operator (Machine Operator)
- View assigned jobs only
- Update job status and progress
- Submit harvest reports for IN-KIND rentals
- Track completed jobs
- Limited dashboard access

---

## Operator Unique Functions

### 1. Operator Dashboard
**URL:** `/operator/dashboard/`

**Features:**
- Statistics cards showing:
  - Total assigned jobs
  - Today's jobs
  - Jobs in progress
  - Jobs awaiting harvest report
  - Completed jobs with harvest reported

**What Operators See:**
- Only jobs assigned to them
- Job details (machine, farmer, dates, location)
- Current status of each job
- Action buttons for their tasks

---

### 2. View Assigned Jobs

**Access:** Operator Dashboard

**Information Displayed:**
- Machine name and type
- Farmer/member name
- Rental dates (start - end)
- Field location
- Rental type (Cash or IN-KIND)
- Current workflow status
- Operator-specific status

**Job Statuses:**
- ⏳ Pending Assignment
- 🚜 Ready to Start
- ⚙️ In Progress
- 🌾 Awaiting Harvest Report
- ✅ Completed

---

### 3. Update Job Status

**Function:** Mark jobs as "In Progress" when starting field work

**Process:**
1. Operator arrives at field
2. Clicks "Start Job" button
3. System updates status to "In Progress"
4. Timestamp recorded for job start
5. Farmer receives notification

**Fields Operators Can Update:**
- Job status (Not Started → In Progress → Completed)
- Field notes/observations
- Actual start time
- Progress updates

---

### 4. Submit Harvest Reports (IN-KIND Rentals Only)

**When:** After completing harvest operations

**Process:**
1. Navigate to completed job
2. Click "Submit Harvest Report"
3. Enter total sacks harvested
4. System auto-calculates:
   - BUFIA share: floor(total_sacks / 9)
   - Member share: total_sacks - BUFIA_share
5. Submit report
6. Admin receives notification for verification

**Example Calculation:**
```
Total Harvested: 100 sacks
BUFIA Share: floor(100 / 9) = 11 sacks
Member Share: 100 - 11 = 89 sacks
```

**Required Information:**
- Total sacks harvested (required)
- Harvest date (auto-filled)
- Additional notes (optional)

---

### 5. View Job History

**Access:** Operator Dashboard → "Completed Jobs" tab

**Information:**
- All completed jobs
- Harvest reports submitted
- Dates and locations
- Farmers served
- Total sacks harvested (for IN-KIND)

---

## Access Restrictions

### ❌ Operators CANNOT:
- View or manage other operators' jobs
- Access admin functions
- Approve/reject rental requests
- Manage user memberships
- View financial reports
- Access payment management
- Modify rental fees or pricing
- Assign jobs to themselves or others
- Delete or cancel rentals

### ✅ Operators CAN:
- View only their assigned jobs
- Update status of their jobs
- Submit harvest reports
- View their job history
- Receive job notifications
- Update their own profile

---

## Workflow Example

### Cash Rental Workflow (Operator Perspective)

1. **Job Assignment**
   - Admin assigns rental to operator
   - Operator receives notification
   - Job appears in "Assigned Jobs"

2. **Job Start**
   - Operator arrives at field
   - Clicks "Start Job"
   - Status: Ready → In Progress

3. **Job Completion**
   - Operator completes work
   - Clicks "Mark as Completed"
   - Status: In Progress → Completed
   - Admin receives completion notification

---

### IN-KIND Rental Workflow (Operator Perspective)

1. **Job Assignment**
   - Admin assigns harvester rental to operator
   - Operator sees IN-KIND badge
   - Job appears in dashboard

2. **Harvest Operation**
   - Operator starts harvest
   - Updates status to "In Progress"
   - Completes harvest work

3. **Harvest Report Submission**
   - Operator counts total sacks
   - Submits harvest report with total
   - System calculates shares:
     - BUFIA: 11 sacks (from 100 total)
     - Member: 89 sacks
   - Admin receives report for verification

4. **Settlement**
   - Admin verifies harvest report
   - BUFIA collects their share
   - Job marked as fully completed

---

## Dashboard Statistics Explained

### Assigned Jobs
Total number of jobs currently assigned to the operator (all statuses)

### Today
Jobs scheduled for today's date

### In Progress
Jobs currently being worked on by the operator

### Awaiting Harvest
IN-KIND jobs completed but harvest report not yet submitted

### Harvest Reported
IN-KIND jobs with harvest reports submitted (pending admin verification)

---

## Notifications

Operators receive notifications for:
- ✅ New job assignments
- 📅 Jobs starting today
- ⚠️ Overdue jobs
- ✅ Job completion confirmations
- 📊 Harvest report status updates

---

## Best Practices for Operators

1. **Check Dashboard Daily**
   - Review assigned jobs
   - Check today's schedule
   - Update job statuses promptly

2. **Accurate Harvest Reporting**
   - Count sacks carefully
   - Submit reports immediately after harvest
   - Include relevant notes

3. **Timely Status Updates**
   - Mark jobs "In Progress" when starting
   - Update completion status promptly
   - Communicate delays to admin

4. **Field Notes**
   - Document any issues encountered
   - Note field conditions
   - Report equipment problems

---

## Technical Implementation

### Model Changes
```python
# users/models.py
class CustomUser(AbstractUser):
    OPERATOR = 'operator'
    
    ROLE_CHOICES = [
        (OPERATOR, 'Operator'),
        # ... other roles
    ]
    
    def is_operator(self):
        return self.role == self.OPERATOR
```

### URL Routes
```python
# Operator-specific URLs
/operator/dashboard/          # Main dashboard
/operator/jobs/               # Job list
/operator/jobs/<id>/          # Job detail
/operator/jobs/<id>/start/    # Start job
/operator/jobs/<id>/complete/ # Complete job
/operator/harvest/<id>/       # Submit harvest report
```

### Permissions
- Operators use `@login_required` decorator
- Additional check: `request.user.is_operator()`
- Can only access their own assigned jobs
- No admin panel access

---

## Support

For operator account issues:
1. Contact system administrator
2. Check notification settings
3. Verify job assignments
4. Report technical problems

---

## Summary

The Operator role provides a focused, task-oriented interface for machine operators to:
- Manage their assigned jobs efficiently
- Submit accurate harvest reports
- Track their work history
- Communicate job status to admins and farmers

This separation of concerns ensures operators can focus on field operations without access to administrative or financial functions.
