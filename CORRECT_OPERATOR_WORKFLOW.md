# Correct Operator Workflow & Functionalities

## Operator Status Options (From System)

Based on the actual system interface, operators can update jobs to these statuses:

1. **Assigned** - Job has been assigned to operator
2. **Traveling to Site** - Operator is traveling to the job location
3. **Operating** - Operator is currently performing the operation

## Complete Operator Workflow

### Standard Job Workflow (Cash/Online Payment)

```
Step 1: Admin assigns job to operator
        ↓
Step 2: Operator receives notification
        ↓
Step 3: Operator views job in dashboard
        ↓
Step 4: Operator updates status to "Traveling to Site"
        ↓
Step 5: Operator arrives at location
        ↓
Step 6: Operator updates status to "Operating"
        ↓
Step 7: Operator completes the work
        ↓
Step 8: Operator notifies admin (via notes or notification)
        ↓
Step 9: Admin marks rental as completed
```

### Harvest Job Workflow (In-Kind Payment)

```
Step 1: Admin assigns harvest job to operator
        ↓
Step 2: Operator receives notification
        ↓
Step 3: Operator views job in dashboard
        ↓
Step 4: Operator updates status to "Traveling to Site"
        ↓
Step 5: Operator arrives at farm
        ↓
Step 6: Operator updates status to "Operating"
        ↓
Step 7: Operator performs harvesting operation
        ↓
Step 8: Operator submits harvest report
        - Enter total sacks harvested
        - System auto-calculates BUFIA share
        - Add completion notes
        ↓
Step 9: System updates status to "Harvest Reported"
        ↓
Step 10: Admin verifies harvest data
        ↓
Step 11: Admin confirms rice delivery
        ↓
Step 12: System marks job as completed
```

## All Operator Functions

### 1. Dashboard
**URL**: `/machines/operator/dashboard/`  
**What operator sees**:
- Active jobs count
- In progress jobs count
- Completed jobs count
- Recent assigned jobs list

### 2. All Jobs
**URL**: `/machines/operator/jobs/`  
**What operator can do**:
- View complete list of assigned jobs
- See job details (machine, member, location, dates)
- Click on job to view details

### 3. Job Detail & Status Update
**URL**: `/machines/operator/jobs/<id>/`  
**What operator can do**:
- View full job information
- Update job status:
  - Assigned
  - Traveling to Site
  - Operating
- Add notes about the operation
- Submit updates

### 4. Ongoing Jobs
**URL**: `/machines/operator/jobs/ongoing/`  
**What operator sees**:
- Only active jobs (assigned, traveling, operating)
- Work interface for current operations

### 5. Awaiting Harvest (For Harvesters)
**URL**: `/machines/operator/jobs/awaiting-harvest/`  
**What operator can do**:
- View jobs ready for harvest submission
- Only shows in-kind payment jobs
- Submit harvest reports

### 6. Submit Harvest Report
**Function**: `submit_operator_harvest()`  
**What operator does**:
- Enter total harvested sacks
- Add completion notes
- Submit for admin review

**What system does automatically**:
- Calculates BUFIA share based on machine ratio
- Calculates member share
- Updates rental status
- Creates harvest report record
- Notifies admins

### 7. Completed Jobs
**URL**: `/machines/operator/jobs/completed/`  
**What operator sees**:
- Historical record of all completed jobs
- Job details and completion dates

### 8. View Machines
**URL**: `/machines/operator/machines/`  
**What operator can do**:
- View list of all active machines
- Reference information (read-only)

### 9. Notifications
**URL**: `/machines/operator/notifications/`  
**What operator receives**:
- New job assignments
- Admin messages
- Status update confirmations

## Key Points

### ✅ What Operators CAN Do:
1. View all assigned jobs
2. Update job status (Assigned → Traveling → Operating)
3. Add notes to jobs
4. Submit harvest reports (for in-kind jobs)
5. View job history
6. View machines
7. Receive notifications

### ❌ What Operators CANNOT Do:
1. Mark jobs as "Completed" directly
   - Admin must verify and complete the job
2. Assign themselves to jobs
   - Only admins can assign operators
3. Edit job details (dates, payment, etc.)
   - Only admins can modify job details
4. Delete or cancel jobs
   - Only admins have this permission

## Completion Process

### For Standard Jobs (Cash/Online):
```
Operator: Updates to "Operating" + adds completion notes
         ↓
Admin: Reviews operator notes
         ↓
Admin: Verifies payment
         ↓
Admin: Marks rental as "Completed"
```

### For Harvest Jobs (In-Kind):
```
Operator: Updates to "Operating"
         ↓
Operator: Submits harvest report (total sacks)
         ↓
System: Auto-calculates BUFIA share
         ↓
System: Updates status to "Harvest Reported"
         ↓
Admin: Verifies harvest data
         ↓
Admin: Confirms rice delivery
         ↓
Admin: Marks rental as "Completed"
```

## Communication Flow

### Operator → Admin:
- Status updates (traveling, operating)
- Completion notes
- Harvest reports
- Issues or problems (via notes)

### Admin → Operator:
- Job assignments
- Verification confirmations
- Instructions or feedback

### System → Both:
- Automatic notifications
- Status change alerts
- Completion confirmations

## Important Notes

1. **Two-Step Completion**: Operators signal completion (via status/notes), admins verify and finalize
2. **Automatic Calculations**: BUFIA share calculated automatically for harvest jobs
3. **Audit Trail**: All status changes and updates are timestamped and recorded
4. **Real-Time Updates**: Admins see operator status changes immediately
5. **Role Separation**: Clear separation between operator actions and admin verification

---

**Status**: ✅ WORKFLOW DOCUMENTED
**Based On**: Actual system interface and implementation
**Operator Role**: Field operations and reporting
**Admin Role**: Verification and completion
