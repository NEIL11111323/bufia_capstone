# Rental Approval Page - Complete Admin Functions Guide

## Overview
The rental approval page at `/machines/admin/rental/{id}/approve/` provides all necessary functions for admins to manage rental requests from submission to completion.

## Page Layout

### Left Column: Rental Information
- **Rental & Payment Information**
- **Machine Details**
- **Renter Information**
- **Payment Status**
- **Purpose & Details**
- **Payment Proof** (if uploaded)

### Right Column: Admin Actions
- **Workflow Information**
- **Operator Assignment** (for IN-KIND and operator-required rentals)
- **Approval Decision**
- **Payment Verification** (for online payments)
- **Face-to-Face Payment Recording**
- **Operator Management**
- **Harvest Recording** (for IN-KIND)
- **Rice Delivery Confirmation** (for IN-KIND)
- **Timeline**

---

## Admin Functions by Payment Type

### 1. ONLINE PAYMENT Workflow

#### Step 1: Review Rental Request
- View rental details
- Check for schedule conflicts
- Review payment amount

#### Step 2: Approve Rental
- Select "Approve Rental" from Decision dropdown
- Add admin notes (optional)
- Click "Submit Decision"
- System sends payment link to member

#### Step 3: Wait for Payment
- Member completes online payment
- System records payment date and Stripe session

#### Step 4: Verify Payment
- Click "View in Stripe Dashboard"
- Verify payment succeeded
- Confirm amount matches
- Click "Verify Payment & Complete Rental"
- System generates Transaction ID
- Rental marked as completed

**Functions Available:**
- ✅ Approve/Reject rental
- ✅ View payment details
- ✅ Open Stripe Dashboard
- ✅ Verify payment
- ✅ Complete rental
- ✅ View transaction ID

---

### 2. FACE-TO-FACE PAYMENT Workflow

#### Step 1: Review Rental Request
- View rental details
- Check for schedule conflicts

#### Step 2: Approve Rental
- Select "Approve Rental" from Decision dropdown
- Click "Submit Decision"

#### Step 3: Record Payment
- When member pays at office
- Fill in payment recording form:
  - Amount Received
  - Payment Date
  - Received By
  - Notes (optional)
- Click "Confirm Payment Received"
- System generates Transaction ID
- Rental marked as completed

**Functions Available:**
- ✅ Approve/Reject rental
- ✅ Record payment amount
- ✅ Record payment date
- ✅ Add receipt number
- ✅ Add payment notes
- ✅ Complete rental
- ✅ View transaction ID

---

### 3. IN-KIND PAYMENT Workflow

#### Step 1: Assign Operator
- Select operator from dropdown
- Click "Assign Operator"
- System notifies operator

#### Step 2: Approve Rental
- Select "Approve Rental" from Decision dropdown
- Click "Submit Decision"

#### Step 3: Start Equipment Operation
- Click "Start Equipment Operation"
- System notifies operator to begin work
- Operator travels to location
- Operator performs work

#### Step 4: Record Harvest
- Enter total harvest in sacks
- Click "Record Harvest & Calculate Shares"
- System auto-calculates BUFIA share using machine ratio
- Example: 70:30 ratio = 30% goes to BUFIA

#### Step 5: Confirm Rice Delivery
- Member delivers rice to BUFIA office
- Enter sacks received
- Click "Confirm & Complete"
- System generates Transaction ID
- Rental marked as completed

**Functions Available:**
- ✅ Assign operator
- ✅ Change operator
- ✅ Approve/Reject rental
- ✅ Start equipment operation
- ✅ Record harvest amount
- ✅ Calculate BUFIA share automatically
- ✅ Confirm rice delivery
- ✅ Complete rental
- ✅ View settlement reference
- ✅ View transaction ID

---

## All Admin Actions Available

### Rental Management
1. **Approve Rental** - Approve the rental request
2. **Reject Rental** - Reject the rental request with notes
3. **Cancel Rental** - Cancel an approved rental
4. **Complete Rental** - Manually mark as completed

### Operator Management (IN-KIND)
5. **Assign Operator** - Assign operator to rental
6. **Change Operator** - Reassign to different operator
7. **Start Operation** - Begin equipment operation
8. **View Operator Status** - Check operator progress

### Payment Management
9. **Verify Online Payment** - Verify Stripe payment
10. **Record Face-to-Face Payment** - Record cash payment
11. **View Payment Proof** - View uploaded payment slip
12. **View Transaction ID** - View generated transaction ID

### Harvest & Settlement (IN-KIND)
13. **Record Harvest** - Enter total harvest amount
14. **Calculate Shares** - Auto-calculate BUFIA share
15. **Confirm Rice Delivery** - Confirm rice received
16. **View Settlement Reference** - View settlement ID

### Information & Tracking
17. **View Rental Details** - All rental information
18. **View Timeline** - Track rental progress
19. **Add Admin Notes** - Add internal notes
20. **Check Conflicts** - View schedule conflicts

---

## Payment Status Indicators

### Online Payment
- 🟡 **Waiting for Payment** - Member hasn't paid yet
- 🟠 **Payment Received - Verification Needed** - Payment received, needs verification
- 🟢 **Payment Verified** - Payment verified and completed

### Face-to-Face Payment
- 🟡 **Waiting for Payment** - Member hasn't paid yet
- 🟢 **Payment Recorded** - Payment recorded and completed

### IN-KIND Payment
- 🟡 **Pending** - Waiting for approval
- 🔵 **Approved** - Approved, waiting for operation
- 🟣 **In Progress** - Operation in progress
- 🟠 **Waiting for Delivery** - Harvest recorded, waiting for rice
- 🟢 **Paid (IN-KIND)** - Rice delivered and completed

---

## Operator Status Indicators

- 🟡 **Assigned** - Operator assigned, not started
- 🔵 **Traveling** - Operator traveling to location
- 🟣 **Operating** - Operator performing work
- 🟠 **Harvest Reported** - Operator submitted harvest
- 🟢 **Completed** - Work completed

---

## Transaction ID System

### Format
- **Online/Face-to-Face**: `BUF-TXN-YYYY-XXXXX`
- **IN-KIND Settlement**: `BUF-STL-YYYY-XXXXX`

### When Generated
- **Online**: When admin verifies payment
- **Face-to-Face**: When admin records payment
- **IN-KIND**: When admin confirms rice delivery

### Where Displayed
- Rental approval page
- Payment confirmation
- User notifications
- Reports and receipts

---

## Workflow States

### Rental Status
- `pending` - Awaiting admin approval
- `approved` - Approved by admin
- `completed` - Fully completed
- `rejected` - Rejected by admin
- `cancelled` - Cancelled

### Workflow State
- `requested` - Initial submission
- `approved` - Admin approved
- `in_progress` - Operation in progress (IN-KIND)
- `harvest_report_submitted` - Harvest recorded (IN-KIND)
- `completed` - Fully completed
- `cancelled` - Cancelled

### Payment Status
- `pending` - Awaiting payment
- `paid` - Payment completed
- `paid_in_kind` - IN-KIND settlement completed
- `to_be_determined` - Harvest recorded, calculating

### Settlement Status (IN-KIND)
- `pending` - Not started
- `waiting_for_delivery` - Waiting for rice delivery
- `paid` - Rice delivered and confirmed

---

## Admin Notifications

Admins receive notifications for:
- ✉️ New rental requests
- ✉️ Payment completed (online)
- ✉️ Operator status updates
- ✉️ Harvest reports submitted
- ✉️ Schedule conflicts detected

---

## Best Practices

### For Online Payments
1. Always verify in Stripe Dashboard before clicking "Verify & Complete"
2. Check amount matches exactly
3. Verify payment status is "Succeeded"
4. Transaction ID is auto-generated upon verification

### For Face-to-Face Payments
1. Record payment immediately when received
2. Enter exact amount received
3. Add receipt number for tracking
4. Include notes for any special circumstances

### For IN-KIND Rentals
1. Assign operator before approving
2. Start operation only when ready
3. Record accurate harvest amounts
4. Verify rice delivery before confirming
5. Check BUFIA share calculation is correct

### General
1. Always add admin notes for rejections
2. Check for schedule conflicts before approving
3. Review all rental details carefully
4. Keep timeline updated
5. Communicate with members when needed

---

## Troubleshooting

### Payment Not Showing
- Refresh the page
- Check Stripe Dashboard
- Verify payment session ID

### Operator Not Assigned
- Check operator availability
- Verify operator has correct role
- Ensure rental is approved first

### Harvest Calculation Wrong
- Check machine IN-KIND ratio settings
- Verify harvest amount entered correctly
- Recalculate if needed

### Transaction ID Missing
- Ensure payment is verified/recorded
- Check payment status is "paid"
- Refresh the page

---

## Security & Permissions

### Required Permissions
- Admin or Staff role required
- Cannot be accessed by regular members
- Operators have limited access to their assigned rentals

### Audit Trail
- All actions logged with timestamp
- Admin user recorded for each action
- Timeline shows complete history
- Transaction IDs provide traceability

---

## Summary

The rental approval page provides a complete, organized interface for admins to:
- ✅ Review and approve rental requests
- ✅ Manage all payment types (online, face-to-face, IN-KIND)
- ✅ Assign and manage operators
- ✅ Track rental progress
- ✅ Record harvest and settlements
- ✅ Generate transaction IDs
- ✅ Complete rentals efficiently

All functions are organized by workflow type and presented in a logical, step-by-step manner for maximum efficiency and minimal errors.
