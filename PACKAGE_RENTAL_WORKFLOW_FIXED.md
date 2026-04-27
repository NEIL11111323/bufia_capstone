# Package Rental Workflow - Complete Guide

## Overview
This document details the complete workflow for package rentals from creation to completion, including all states, transitions, and business logic.

## Workflow States

### Package States
1. **pending** - Initial state after creation
2. **approved** - All services scheduled and approved
3. **partially_scheduled** - Some services scheduled, others pending
4. **in_progress** - At least one service is being executed
5. **completed** - All services finished
6. **cancelled** - Package cancelled by user or admin

### Package Item States
1. **requested** - Initial state, no schedule yet
2. **tentative** - Schedule set but not confirmed
3. **scheduled** - Schedule confirmed, rental created
4. **in_progress** - Service being executed
5. **completed** - Service finished
6. **cancelled** - Service cancelled
7. **not_included** - Service excluded from package

## Complete Workflow

### Phase 1: Package Creation (Member)

**Step 1: Member Creates Package**
- URL: `/machines/packages/create/`
- Member selects services needed
- Provides farm details (location, area, preferred start date)
- Sets payment preference (online/face-to-face)
- Marks as urgent if needed

**Result:**
- Package created with status: `pending`
- All items have status: `requested`
- No linked rentals yet

### Phase 2: Admin Review and Scheduling

**Step 2: Admin Opens Package**
- URL: `/machines/packages/<id>/`
- Admin sees package summary
- Views all requested services
- Can edit schedule for each service

**Step 3: Admin Schedules Services**
For each service item:
1. Select machine
2. Set quantity (if applicable)
3. Set scheduled start/end dates
4. Mark as tentative or confirmed
5. Add admin notes

**Actions Available:**
- **Save Draft** - Saves changes without creating rentals
- **Confirm Schedule** (per item) - Confirms one service
- **Pre-Approve** - Approves confirmed items, leaves others open
- **Approve Package** - Approves all confirmed items

### Phase 3: Schedule Confirmation

**Step 4: Confirm Individual Service**
- Admin clicks "Confirm Schedule" on a service
- System validates:
  - Machine is assigned
  - Start/end dates are set
  - No scheduling conflicts
- If valid:
  - Item status: `requested` → `scheduled`
  - Creates linked Rental record
  - Rental status: `approved`
  - Rental workflow_state: `approved`
  - Machine calendar updated

**Rental Record Created:**
```python
Rental(
    machine=selected_machine,
    user=package.user,
    customer_name=package.farmer_name,
    start_date=item.scheduled_start,
    end_date=item.scheduled_end,
    status='approved',
    workflow_state='approved',
    operator_status='unassigned',
    payment_type=machine.rental_price_type,
    payment_method=package.payment_preference,
    purpose="Package: [name]\nService: [service_name]..."
)
```

### Phase 4: Package Approval

**Step 5: Pre-Approve Package**
- Admin clicks "Pre-Approve"
- System:
  - Promotes all ready items to `scheduled`
  - Creates rentals for confirmed items
  - Leaves unscheduled items as `requested`
  - Package status: `partially_scheduled`

**Step 6: Full Approve Package**
- Admin clicks "Approve Package"
- System validates all items have confirmed schedules
- If any item missing schedule:
  - Shows error with list of pending items
  - Suggests using Pre-Approve instead
- If all confirmed:
  - All items: `scheduled`
  - All rentals created
  - Package status: `approved`

### Phase 5: Payment Processing

**Step 7: Payment Becomes Available**
After approval, for each cash service:
- Rental appears in "Ready to Pay" section
- Member can click "Pay Now"
- Redirected to payment page
- Submits payment proof

For rice-share services:
- Appears in "Rice Settlement" section
- Tracks harvest and delivery

**Step 8: Payment Verification**
- Admin verifies submitted payments
- Updates rental payment_status: `paid`
- Package payment_status updates automatically

### Phase 6: Service Execution

**Step 9: Operator Assignment**
- Operator assigned to rental
- Rental operator_status: `assigned`

**Step 10: Job Execution**
- Operator starts job
- Rental workflow_state: `in_progress`
- Item status: `in_progress`
- Package status: `in_progress`

**Step 11: Job Completion**
- Operator completes job
- Rental workflow_state: `completed`
- Item status: `completed`

**Step 12: Package Completion**
When all items completed:
- Package status: `completed`
- Package payment_status: `paid` (if all settled)

## Cancellation Workflow

### Member Cancellation
**Conditions:**
- Only package requester can cancel
- Cannot cancel if any service is `in_progress` or `completed`

**Process:**
1. Member clicks "Cancel Package"
2. Confirmation modal appears
3. If confirmed:
   - All linked rentals cancelled
   - All items status: `cancelled`
   - Package status: `cancelled`
   - Machine calendars updated

### Admin Rejection
**Conditions:**
- Only admin can reject
- Cannot reject if any service is `in_progress` or `completed`

**Process:**
1. Admin clicks "Reject Package"
2. Confirmation modal appears
3. If confirmed:
   - All linked rentals cancelled
   - All items status: `cancelled`
   - Package status: `cancelled`
   - Rejection note added

## Key Business Rules

### Scheduling Rules
1. **Machine Assignment Required** - Must select machine before confirming
2. **Date Range Required** - Must set start and end dates
3. **No Conflicts** - System checks for scheduling conflicts
4. **Tentative Flag** - Can mark schedule as tentative (not confirmed)

### Status Transitions
```
Package Item Status Flow:
requested → tentative → scheduled → in_progress → completed
    ↓           ↓           ↓            ↓
cancelled   cancelled   cancelled    cancelled

Package Status Flow:
pending → partially_scheduled → approved → in_progress → completed
    ↓              ↓               ↓            ↓
cancelled      cancelled       cancelled    cancelled
```

### Payment Rules
1. **Cash Services** - Payment required after approval
2. **Rice-Share Services** - Settlement after harvest
3. **Package Payment Status** - Aggregates all service payments
4. **Payment Methods** - Online (Gcash) or Face-to-Face

### Rental Creation Rules
1. **Only for Confirmed Items** - Rentals created only when schedule confirmed
2. **Automatic Updates** - Rental updates when schedule changes
3. **Machine Sync** - Machine status syncs with rental changes
4. **Payment Sync** - Payment records created for cash rentals

## Function Reference

### Core Workflow Functions

**`_sync_package_item_rental(package_item, approved_by)`**
- Creates or updates rental for a package item
- Links rental to package item
- Syncs machine status
- Creates payment record for cash rentals

**`_sync_package_items_to_rentals(package, acting_user)`**
- Syncs all confirmed items to rentals
- Releases rentals for unconfirmed items
- Updates package payment status

**`_approve_rental_package(package, approved_by)`**
- Promotes all ready items to scheduled
- Creates rentals for all confirmed items
- Updates package status to approved
- Refreshes totals and payment status

**`_close_rental_package(package, acting_user, action_label)`**
- Cancels all linked rentals
- Updates all items to cancelled
- Updates package to cancelled
- Adds cancellation notes

**`_promote_schedule_ready_package_items(items)`**
- Finds items with complete schedule info
- Promotes from requested/tentative to scheduled
- Returns list of promoted item IDs

**`_save_package_status(package, approver, allow_full_approval)`**
- Computes package status from items
- Updates approver and approval timestamp
- Prevents full approval unless explicitly allowed

### Validation Functions

**`_can_close_package(package)`**
- Checks if package can be cancelled/rejected
- Returns False if any service in progress or completed

**`_can_edit_package_schedule(package)`**
- Checks if schedule can be edited
- Returns False if completed, cancelled, or in progress

**`_undecided_package_items(package)`**
- Returns list of items without confirmed schedules
- Used to validate full approval

### Helper Functions

**`_package_item_rental_area(package_item)`**
- Calculates rental area for package item
- Uses item quantity or package area

**`_is_package_reserve_rental(rental)`**
- Checks if rental is from a package
- Looks for "Package:" prefix in purpose

**`_release_package_item_rental(package_item)`**
- Cancels linked rental
- Updates machine status
- Clears rental link

## Error Handling

### Common Validation Errors

1. **Missing Machine**
   - Error: "Assign a machine before confirming"
   - Solution: Select machine from dropdown

2. **Missing Dates**
   - Error: "Complete the schedule dates before confirming"
   - Solution: Set both start and end dates

3. **Scheduling Conflict**
   - Error: "Machine not available for selected dates"
   - Solution: Choose different dates or machine

4. **Incomplete Approval**
   - Error: "Cannot fully approve. Confirm schedules first for: [list]"
   - Solution: Use Pre-Approve or confirm remaining items

### Error Display
- Form-level errors shown at top
- Field-level errors shown below fields
- Validation errors shown in red alert boxes

## Status Indicators

### Package Status Badges
- **Pending** - Orange badge
- **Approved** - Blue badge
- **Partially Scheduled** - Blue badge
- **In Progress** - Teal badge
- **Completed** - Green badge
- **Cancelled** - Gray badge

### Item Status Badges
- **Requested** - Orange
- **Tentative** - Blue
- **Scheduled** - Green
- **In Progress** - Teal
- **Completed** - Green
- **Cancelled** - Gray

## Best Practices

### For Admins
1. **Review Package Details** - Check farm location, area, dates
2. **Schedule Sequentially** - Schedule services in logical order
3. **Check Availability** - Use availability calendar before confirming
4. **Use Pre-Approve** - For partial scheduling flexibility
5. **Add Notes** - Document any special considerations

### For Members
1. **Provide Complete Info** - Include accurate farm details
2. **Set Realistic Dates** - Allow time for scheduling
3. **Choose Payment Method** - Select preferred payment option
4. **Monitor Status** - Check package status regularly
5. **Pay Promptly** - Submit payment when ready

## Troubleshooting

### Package Won't Approve
- Check all items have machines assigned
- Verify all dates are set
- Ensure no scheduling conflicts
- Try Pre-Approve for partial scheduling

### Rental Not Created
- Confirm schedule is marked as confirmed (not tentative)
- Check item status is `scheduled`
- Verify machine and dates are set

### Payment Not Showing
- Ensure package is approved
- Check rental is created (linked_rental exists)
- Verify payment type is cash
- Confirm payment method is set

### Cannot Cancel
- Check if any service is in progress
- Verify no services are completed
- Ensure user has permission

## Summary

The package rental workflow provides a structured process for managing multi-service equipment rentals. Key features:

✅ **Flexible Scheduling** - Admin can schedule services individually
✅ **Partial Approval** - Pre-approve confirmed items, schedule others later
✅ **Automatic Rental Creation** - Rentals created when schedules confirmed
✅ **Payment Integration** - Seamless payment tracking per service
✅ **Status Tracking** - Clear visibility of package and item states
✅ **Cancellation Safety** - Prevents cancellation of active services

**Last Updated:** Current session
**Status:** ✅ Workflow Documented and Verified
