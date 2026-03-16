# Admin Dashboard Complete Workflow
## URL: http://127.0.0.1:8000/machines/admin/dashboard/

## Dashboard Overview

The Admin Dashboard is organized into **4 main tabs** based on rental workflow stages:

### Tab 1: Pending Requests
**Purpose**: New rental requests awaiting admin approval  
**Status**: `status='pending'`  
**Actions Available**:
- Review rental details
- Approve rental
- Reject rental
- Assign operator (if approved)

### Tab 2: Approved Rentals
**Purpose**: Rentals approved but not yet started  
**Status**: `status='approved'` AND `workflow_state='approved'`  
**Actions Available**:
- Assign operator (if not assigned)
- Start operation (for in-kind rentals)
- View rental details
- Cancel if needed

### Tab 3: In Progress
**Purpose**: Active operations currently being performed  
**Status**: `workflow_state='in_progress'`  
**Actions Available**:
- Monitor operator status
- View operator updates
- Submit harvest report (for in-kind)
- Mark as completed (when done)

### Tab 4: Completed
**Purpose**: Finished, rejected, or cancelled rentals  
**Status**: `status='completed'` OR `workflow_state='completed'` OR `status='rejected'` OR `status='cancelled'`  
**Actions Available**:
- View history
- Review details
- Generate reports

---

## Complete Rental Workflows

### Workflow A: Cash/Online Payment Rentals

```
STEP 1: Member submits rental request
        ↓
STEP 2: Appears in "Pending Requests" tab
        ↓
STEP 3: Admin reviews request
        - Check machine availability
        - Verify member details
        - Check for conflicts
        ↓
STEP 4: Admin approves rental
        - Set status to "Approved"
        - Rental moves to "Approved Rentals" tab
        - Member receives notification
        ↓
STEP 5: Admin assigns operator
        - Select operator from dropdown
        - Click "Assign Operator"
        - Operator receives notification
        ↓
STEP 6: Operator updates status
        - Traveling to Site
        - Operating
        ↓
STEP 7: Rental moves to "In Progress" tab
        - Admin monitors progress
        - Operator provides updates
        ↓
STEP 8: Operation completes
        - Operator adds completion notes
        - Notifies admin
        ↓
STEP 9: Admin verifies completion
        - Check operator notes
        - Verify payment received
        ↓
STEP 10: Admin marks as completed
        - Set status to "Completed"
        - Machine becomes available
        - Rental moves to "Completed" tab
        - Member receives completion notification
```

### Workflow B: In-Kind Payment (Harvest) Rentals

```
STEP 1: Member submits harvest rental request
        ↓
STEP 2: Appears in "Pending Requests" tab
        ↓
STEP 3: Admin reviews and approves
        - Set status to "Approved"
        - Rental moves to "Approved Rentals" tab
        ↓
STEP 4: Admin assigns operator
        - Select harvester operator
        - Operator receives notification
        ↓
STEP 5: Admin starts operation (optional)
        - Click "Start Operation"
        - Rental moves to "In Progress" tab
        - workflow_state = 'in_progress'
        ↓
STEP 6: Operator performs harvesting
        - Updates status to "Operating"
        - Completes harvest
        ↓
STEP 7: Operator submits harvest report
        - Enters total sacks harvested
        - System auto-calculates BUFIA share
        - workflow_state = 'harvest_report_submitted'
        - Appears in "Harvest Settlement Queue"
        ↓
STEP 8: Admin verifies harvest data
        - Reviews total harvest
        - Confirms BUFIA share calculation
        - Checks operator notes
        ↓
STEP 9: Admin confirms rice delivery
        - Member delivers BUFIA share
        - Admin enters received sacks
        - Click "Confirm Rice Received"
        - settlement_status = 'paid'
        ↓
STEP 10: System auto-completes (if shares match)
        - status = 'completed'
        - workflow_state = 'completed'
        - Machine becomes available
        - Rental moves to "Completed" tab
        - Member receives completion notification
```

---

## Dashboard Statistics

The dashboard shows 5 key metrics:

1. **Pending Requests**: Count of rentals awaiting approval
2. **Approved Rentals**: Count of approved but not started
3. **Rentals In Progress**: Count of active operations
4. **Harvest Settlements**: Count of in-kind rentals awaiting settlement
5. **Completed Rentals**: Total completed rentals

---

## Filters & Search

### Status Filters:
- All
- Pending
- Approved
- Completed
- Rejected
- Cancelled

### Payment Filters:
- All
- Online Payment
- Face-to-Face Payment
- IN-KIND Payment
- Verified
- Unverified

### Search:
- Search by member name
- Search by username
- Search by machine name

---

## Admin Actions by Tab

### Pending Requests Tab Actions:

1. **Approve Rental**
   - Click "Approve" or "Review"
   - Verify details
   - Set status to "Approved"
   - Optionally assign operator

2. **Reject Rental**
   - Click "Review"
   - Set status to "Rejected"
   - Add rejection reason
   - Member receives notification

3. **View Details**
   - Click on rental
   - See full information
   - Check conflicts
   - Review member history

### Approved Rentals Tab Actions:

1. **Assign Operator**
   - Select operator from dropdown
   - Click "Assign Operator"
   - Operator receives notification

2. **Start Operation** (In-Kind only)
   - Click "Start Operation"
   - Moves to "In Progress"
   - Operator can begin work

3. **Cancel Rental**
   - Set status to "Cancelled"
   - Machine becomes available
   - Member receives notification

### In Progress Tab Actions:

1. **Monitor Progress**
   - View operator status updates
   - Check operator notes
   - Track operation timeline

2. **Submit Harvest Report** (In-Kind)
   - Enter total harvest sacks
   - System calculates shares
   - Creates harvest record

3. **Mark as Completed** (Cash/Online)
   - Verify payment received
   - Verify operation complete
   - Set status to "Completed"

4. **Confirm Rice Delivery** (In-Kind)
   - Enter received sacks
   - Verify matches BUFIA share
   - Auto-completes if correct

### Completed Tab Actions:

1. **View History**
   - Review completed rentals
   - Check completion dates
   - View operator performance

2. **Generate Reports**
   - Export rental data
   - Analyze statistics
   - Track revenue

---

## Special Features

### Harvest Settlement Queue

Located on the dashboard, shows in-kind rentals needing attention:
- Harvest reports submitted
- Awaiting rice delivery
- Pending verification

**Actions**:
- Click on rental
- Verify harvest data
- Confirm rice received
- Complete settlement

### Operator Assignment

Available in rental approval page:
- Dropdown shows all active operators
- Select operator
- Click "Assign Operator"
- Operator sees job in their dashboard

### Automatic Calculations

For in-kind rentals:
- BUFIA share calculated automatically
- Based on machine's in-kind ratio
- Member share calculated
- No manual computation needed

### Automatic Completion

For in-kind rentals:
- If received sacks = required BUFIA share
- System auto-completes rental
- Machine becomes available
- Notifications sent automatically

---

## Workflow States

| State | Description | Tab Location |
|-------|-------------|--------------|
| `requested` | Initial submission | Pending |
| `approved` | Admin approved | Approved |
| `in_progress` | Operation active | In Progress |
| `harvest_report_submitted` | Harvest data submitted | In Progress |
| `completed` | Rental finished | Completed |
| `cancelled` | Rental cancelled | Completed |

---

## Payment Verification Flow

### Online Payment:
```
Member pays online → Stripe confirms → Admin verifies → Mark completed
```

### Face-to-Face Payment:
```
Member pays in person → Admin records payment → Admin verifies → Mark completed
```

### In-Kind Payment:
```
Harvest complete → Operator reports → Admin verifies → Member delivers rice → Admin confirms → Auto-complete
```

---

## Best Practices

1. **Review Pending Requests Daily**
   - Check for new requests
   - Approve/reject promptly
   - Assign operators quickly

2. **Monitor In Progress Rentals**
   - Check operator updates
   - Respond to issues
   - Track completion timeline

3. **Verify Harvest Data Carefully**
   - Check operator calculations
   - Confirm BUFIA share
   - Verify rice delivery

4. **Complete Rentals Promptly**
   - Free up machines
   - Update member records
   - Maintain accurate statistics

5. **Use Filters Effectively**
   - Filter by payment type
   - Search by member/machine
   - Focus on priority items

---

**Status**: ✅ COMPLETE WORKFLOW DOCUMENTED
**Dashboard URL**: `/machines/admin/dashboard/`
**Key Feature**: Tab-based workflow organization
**Auto-Features**: Calculations, completions, notifications
