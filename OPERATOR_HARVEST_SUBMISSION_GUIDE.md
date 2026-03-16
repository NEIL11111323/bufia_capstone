# Operator Harvest Submission Guide

## Overview
Operators can submit harvest reports directly from their dashboard without needing to contact admin via Facebook Messenger or phone.

## Access
- **URL**: `/machines/operator/dashboard/`
- **Permission**: Requires operator/staff account
- **View**: `machines/operator_views.py` → `operator_dashboard()`

## Operator Dashboard Features

### Statistics Panel
Shows real-time job metrics:
- **Assigned Jobs** - Total jobs assigned to operator
- **Today** - Jobs scheduled for today
- **In Progress** - Currently active jobs
- **Awaiting Harvest** - IN-KIND rentals ready for harvest reporting
- **Harvest Reported** - Completed harvest submissions

### Job Cards
Each assigned rental displays:
- Machine name and type
- Member name
- Rental dates
- Payment type badge
- Workflow status
- Operator status
- Field location
- Area (hectares)
- Last update timestamp

### Two Action Panels per Job

#### 1. Job Status Update Panel (Left)
Allows operator to update:
- **Operator Status** dropdown:
  - Unassigned
  - Assigned
  - Traveling
  - Operating
  - Completed
  - Harvest Reported
- **Notes** textarea for field updates
- **Save Operator Update** button

#### 2. Harvest Submission Panel (Right)
**Only visible for IN-KIND rentals**

Form fields:
- **Total Harvest (sacks)** - Number input with decimal support (e.g., 21.3, 100.75)
- **Harvest Notes** - Textarea for harvest details
- **Submit Harvest Report** button (yellow/warning color)

Help text: "The system will automatically compute the BUFIA share and member share after submission."

## Harvest Submission Workflow

### Step 1: Operator Completes Job
- Operator operates the machine
- Harvest is completed
- Operator counts total sacks

### Step 2: Operator Submits Harvest
1. Operator logs into BUFIA system
2. Navigates to Operator Dashboard
3. Finds the rental job card
4. Scrolls to "Harvest Submission" panel (right side)
5. Enters total harvest in sacks (accepts decimals: 21, 21.3, 21.75)
6. Adds harvest notes (optional)
7. Clicks "Submit Harvest Report"

### Step 3: System Processing
System automatically:
- Validates harvest amount (must be > 0)
- Calculates BUFIA share using machine ratio (default 9:1)
  ```
  BUFIA_share = (total_harvest × organization_share) / farmer_share
  Member_share = total_harvest - BUFIA_share
  ```
- Updates rental fields:
  - `total_harvest_sacks = entered_value`
  - `bufia_share = calculated_value`
  - `member_share = calculated_value`
  - `organization_share_required = bufia_share`
  - `workflow_state = 'harvest_report_submitted'`
  - `settlement_status = 'waiting_for_delivery'`
  - `operator_status = 'harvest_reported'`
- Creates HarvestReport record
- Notifies all admins for review

### Step 4: Admin Review
- Admins receive notification
- Admins can view harvest details in Admin Dashboard
- Admins proceed to confirm rice delivery

## Example Calculation

**Input:**
- Total Harvest: 21.3 sacks
- Machine Ratio: 9:1 (farmer:organization)

**System Calculates:**
- BUFIA Share = (21.3 × 1) / 9 = 2.37 sacks
- Member Share = 21.3 - 2.37 = 18.93 sacks

**Result:**
- Operator sees success message
- Admin receives notification: "Harvest reported for [Machine]: 21.3 sacks, BUFIA share 2.37 sacks"
- Rental status updates to "Harvest Report Submitted"

## Technical Implementation

### View Function
**File**: `machines/operator_views.py`
**Function**: `submit_operator_harvest(request, rental_id)`

**Validations:**
- User must be authenticated operator
- Rental must be assigned to current operator
- Rental must be IN-KIND payment type
- Harvest amount must be valid decimal > 0

**Process:**
1. Parse and validate `total_harvest_sacks` from POST data
2. Calculate shares using `rental.calculate_harvest_shares()`
3. Update rental with harvest data and workflow states
4. Create HarvestReport record
5. Notify admins
6. Redirect to operator dashboard with success message

### URL Pattern
```python
path('operator/rental/<int:rental_id>/harvest/', 
     operator_views.submit_operator_harvest, 
     name='submit_operator_harvest')
```

### Template
**File**: `templates/machines/operator/dashboard.html`

**Form Structure:**
```html
<form method="post" action="{% url 'machines:submit_operator_harvest' rental.id %}">
    {% csrf_token %}
    <input type="number" name="total_harvest_sacks" step="0.01" min="0" required>
    <textarea name="operator_notes"></textarea>
    <button type="submit">Submit Harvest Report</button>
</form>
```

## Benefits of Direct Submission

### For Operators:
- ✅ No need to contact admin via Facebook/phone
- ✅ Submit immediately after harvest
- ✅ See real-time status updates
- ✅ Track all assigned jobs in one place
- ✅ Add detailed notes for each submission

### For Admins:
- ✅ Receive instant notifications
- ✅ Automatic calculations (no manual math)
- ✅ Complete audit trail
- ✅ Reduced communication overhead
- ✅ Faster processing time

### For System:
- ✅ Data accuracy (direct entry)
- ✅ Timestamp tracking
- ✅ Workflow automation
- ✅ Notification system integration
- ✅ Complete transaction history

## Alternative: Manual Admin Entry

If operator prefers traditional method:
1. Operator reports harvest via Facebook Messenger/phone
2. Admin logs into Admin Dashboard
3. Admin navigates to rental approval page
4. Admin clicks "Submit Harvest Report"
5. Admin enters harvest data manually
6. System processes same as operator submission

**Note**: Direct operator submission is preferred for efficiency and accuracy.

## Troubleshooting

### "You don't have permission to submit harvest reports"
- User is not logged in as operator/staff
- Solution: Login with operator account

### "Enter a valid harvest total in sacks"
- Invalid number format entered
- Solution: Enter valid decimal number (e.g., 21.3)

### "Harvest total must be greater than zero"
- Entered 0 or negative number
- Solution: Enter positive harvest amount

### Form not visible
- Rental is not IN-KIND payment type
- Solution: Harvest submission only applies to IN-KIND rentals

## Related Documentation
- `TRANSACTION_WORKFLOW_GUIDE.md` - Complete transaction workflows
- `OPERATOR_ROLE_GUIDE.md` - Operator role and permissions
- `machines/operator_views.py` - Operator view functions
- `templates/machines/operator/dashboard.html` - Operator dashboard template
