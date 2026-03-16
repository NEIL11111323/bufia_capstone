# Operator Functions Guide

## Overview
This guide explains all the functions available to operators in the BUFIA system and what each navigation page does.

## Navigation Structure

### 1. OPERATOR Section

#### Dashboard
**URL**: `/machines/operator/dashboard/`
**Function**: Main operator dashboard showing all assigned jobs

**What You See**:
- Statistics cards showing:
  - Total Assigned Jobs
  - Jobs In Progress
  - Jobs Awaiting Harvest
  - Completed Jobs
- List of all your assigned equipment rental jobs
- Job cards with detailed information for each rental

**What You Can Do**:
- View all your assigned jobs at a glance
- See job status and details
- Update job status (Assigned, Traveling, Operating, Harvest Reported)
- Submit harvest reports for IN-KIND rentals
- Add notes about job progress

---

### 2. MY OPERATIONS Section

#### All Assigned Jobs
**URL**: `/machines/operator/dashboard/`
**Function**: Shows ALL jobs assigned to you (default view)

**Filters**: None (shows everything)

**Job Types Shown**:
- Newly assigned jobs
- Jobs in progress
- Jobs awaiting harvest
- Jobs with submitted harvest reports

---

#### In Progress
**URL**: `/machines/operator/dashboard/?status=in_progress`
**Function**: Shows only jobs you're currently working on

**Filters**: 
- Operator Status = "Traveling" OR "Operating"

**What You See**:
- Jobs where you're traveling to the location
- Jobs where you're actively operating the equipment

**Use Case**: Focus on your current active work

---

#### Awaiting Harvest
**URL**: `/machines/operator/dashboard/?status=awaiting_harvest`
**Function**: Shows IN-KIND jobs ready for harvest report submission

**Filters**:
- Payment Type = "IN-KIND"
- Workflow State = "In Progress"
- Operator Status = "Operating"

**What You See**:
- Jobs where operation is complete
- Jobs waiting for harvest report
- Only IN-KIND payment type rentals

**Use Case**: Know which jobs need harvest reports submitted

---

### 3. EQUIPMENT Section

#### View Machines
**URL**: `/machines/`
**Function**: View all available machines in the system

**What You See**:
- List of all machines (tractors, harvesters, etc.)
- Machine details (type, model, status)
- Machine availability

**What You Can Do**:
- View machine specifications
- Check machine status
- See machine details

**Note**: Operators can view but cannot modify machine information

---

## Core Operator Functions

### Function 1: Update Job Status
**Location**: Each job card on dashboard
**Form**: "Update Job Status" section

**Available Statuses**:
1. **Assigned** - Job assigned but not started
2. **Traveling** - On the way to job location
3. **Operating** - Currently operating the equipment
4. **Harvest Reported** - Harvest report submitted (auto-set)

**Fields**:
- Status dropdown
- Notes textarea (optional)

**What Happens**:
- Updates job status in real time
- Records timestamp of update
- Notifies admins of status change
- When status = "Operating", automatically:
  - Sets workflow state to "In Progress"
  - Records actual handover date
  - Updates machine status to "In Use"

**Code Location**: `machines/operator_views.py` → `update_operator_job()`

---

### Function 2: Submit Harvest Report
**Location**: Each IN-KIND job card on dashboard
**Form**: "Submit Harvest Report" section

**Availability**: Only for IN-KIND payment type rentals

**Fields**:
- Total Harvest (sacks) - decimal number (e.g., 21.3)
- Harvest Notes - textarea (optional)

**What Happens**:
1. System calculates BUFIA share automatically (Total ÷ 9)
2. System calculates Member share (Total - BUFIA share)
3. Updates rental with harvest data
4. Creates HarvestReport record
5. Sets workflow state to "Harvest Report Submitted"
6. Sets operator status to "Harvest Reported"
7. Notifies admins for rice delivery confirmation

**Example Calculation**:
- Total Harvest: 21.3 sacks
- BUFIA Share: 2.37 sacks (21.3 ÷ 9)
- Member Share: 18.93 sacks (21.3 - 2.37)

**Code Location**: `machines/operator_views.py` → `submit_operator_harvest()`

---

## Job Card Information

Each job card displays:

### Header Section
- Machine name
- Member name
- Rental dates (start - end)
- Payment type badge (IN-KIND, Online, Face-to-Face)
- Workflow status badge
- Operator status badge

### Information Grid
- Machine Type (e.g., Tractor, Harvester)
- Field Location
- Area (in hectares)
- Last Update timestamp

### Harvest Info (if submitted)
- Total harvest sacks
- BUFIA share sacks
- Member share sacks

### Action Section
Two forms side-by-side:
1. Update Job Status form (left)
2. Submit Harvest Report form (right, IN-KIND only)

---

## Workflow Example

### Typical Job Flow for Operator:

1. **Job Assignment**
   - Admin assigns you to a rental
   - You receive notification
   - Job appears on your dashboard with status "Assigned"

2. **Travel to Location**
   - Update status to "Traveling"
   - Add notes about estimated arrival time

3. **Start Operation**
   - Update status to "Operating"
   - System automatically:
     - Sets workflow to "In Progress"
     - Records handover date
     - Updates machine status to "In Use"

4. **Complete Operation**
   - For IN-KIND rentals:
     - Submit harvest report with total sacks
     - System calculates shares automatically
     - Status changes to "Harvest Reported"
   - For Online/Face-to-Face rentals:
     - Update status to indicate completion
     - Admin handles payment verification

5. **Admin Confirmation**
   - Admin confirms rice delivery (IN-KIND)
   - Admin marks rental as completed
   - Machine becomes available again

---

## Important Notes

### Permissions
- Operators can ONLY see and update their assigned jobs
- Operators cannot assign jobs to themselves
- Operators cannot modify machine information
- Operators cannot access admin functions

### IN-KIND vs Other Payment Types
- **IN-KIND**: Requires harvest report submission
- **Online/Face-to-Face**: No harvest report needed

### Automatic Calculations
- BUFIA share is always calculated as: Total Harvest ÷ 9
- Member share is always: Total Harvest - BUFIA Share
- All calculations rounded to 2 decimal places

### Notifications
- Admins are notified when you:
  - Update job status
  - Submit harvest report
- You are notified when:
  - New job is assigned to you
  - Admin makes changes to your job

---

## Technical Details

### View Functions
All operator functions are in `machines/operator_views.py`:

1. `operator_dashboard()` - Main dashboard with filtering
2. `update_operator_job()` - Update job status
3. `submit_operator_harvest()` - Submit harvest report
4. `assign_operator()` - Admin function to assign operators

### URL Patterns
Defined in `machines/urls.py`:
```python
path('operator/dashboard/', operator_views.operator_dashboard, name='operator_dashboard')
path('operator/rental/<int:rental_id>/update/', operator_views.update_operator_job, name='update_operator_job')
path('operator/rental/<int:rental_id>/harvest/', operator_views.submit_operator_harvest, name='submit_operator_harvest')
```

### Template
- Main template: `templates/machines/operator/operator_dashboard_clean.html`
- Extends: `templates/base.html`
- Uses conditional navigation for operators

### Database Fields
Operator-related fields in `Rental` model:
- `assigned_operator` - ForeignKey to User
- `operator_status` - Choice field (assigned, traveling, operating, harvest_reported)
- `operator_notes` - TextField
- `operator_last_update_at` - DateTimeField
- `operator_reported_at` - DateTimeField

---

## Troubleshooting

### "No Jobs Assigned" Message
- You haven't been assigned any jobs yet
- Contact admin to assign jobs to you

### Cannot Submit Harvest Report
- Check if payment type is IN-KIND
- Check if you've already submitted a report
- Ensure you're in "Operating" status

### Navigation Disappears
- This has been fixed in the latest update
- Navigation should persist across all pages
- If issue persists, clear browser cache

### Cannot Update Status
- Ensure you're logged in as operator
- Check if job is assigned to you
- Verify job is not completed/cancelled

---

## Quick Reference

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/machines/operator/dashboard/` | View all jobs |
| In Progress | `/machines/operator/dashboard/?status=in_progress` | Active jobs only |
| Awaiting Harvest | `/machines/operator/dashboard/?status=awaiting_harvest` | Jobs needing harvest reports |
| View Machines | `/machines/` | Browse equipment |

| Function | Location | Purpose |
|----------|----------|---------|
| Update Status | Job card | Change job status |
| Submit Harvest | Job card (IN-KIND) | Report harvest results |
| Add Notes | Both forms | Document progress |

---

## Support

For issues or questions:
1. Contact system administrator
2. Check this guide for function explanations
3. Review `OPERATOR_SETUP_GUIDE.md` for account setup
4. Review `OPERATOR_HARVEST_SUBMISSION_GUIDE.md` for harvest workflow
