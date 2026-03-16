# BUFIA Machine Rental Transaction Workflow Guide

## Overview
This guide documents the complete transaction workflow for all machine rentals in the BUFIA system, supporting three payment types: IN-KIND Payment (Rice Share), Online Payment, and Face-to-Face Payment.

## Payment Types

### 1. IN-KIND Payment (Rice Share)

#### Workflow Steps:

**Step 1: Rental Approval**
- Member submits a machine rental request
- Admin reviews the request in the Admin Dashboard
- Admin approves the rental
- System updates:
  - `rental.status = 'approved'`
  - `rental.payment_type = 'in_kind'`
  - `rental.workflow_state = 'approved'`
  - `rental.settlement_status = 'pending'`
  - `rental.payment_status = 'pending'`

**Step 2: Equipment Operation**
- Admin clicks "Start Equipment Operation"
- The machine is operated by the BUFIA operator
- System updates:
  - `rental.workflow_state = 'in_progress'`
  - `rental.actual_handover_date = current_time`
  - `machine.status = 'rented'` (in use)

**Step 3: Harvest Reporting**
- **Option A: Operator submits directly**
  - Operator logs into their dashboard
  - Operator submits harvest report with `total_harvest_sacks` (accepts decimals: 21, 21.3, 21.75, etc.)
  - System creates HarvestReport record
  - Admins receive notification for review
  
- **Option B: Admin records manually**
  - Operator reports harvest to admin (via Facebook Messenger or in person)
  - Admin records the harvest in the system using "Submit Harvest Report"
  - Admin inputs: `total_harvest_sacks` (accepts decimals: 21, 21.3, 21.75, etc.)

**Step 4: Harvest Calculation**
- System automatically calculates shares using the formula:
  ```
  BUFIA_share = (total_harvest × organization_share) / farmer_share
  Member_share = total_harvest - BUFIA_share
  ```
- Default ratio: 9:1 (farmer:organization)
- Example:
  - Total Harvest = 21.3 sacks
  - BUFIA Share = (21.3 × 1) / 9 = 2.37 sacks
  - Member Share = 21.3 - 2.37 = 18.93 sacks
- System updates:
  - `rental.total_harvest_sacks = 21.3`
  - `rental.bufia_share = 2.37`
  - `rental.member_share = 18.93`
  - `rental.organization_share_required = 2.37`
  - `rental.workflow_state = 'harvest_report_submitted'`
  - `rental.settlement_status = 'waiting_for_delivery'`

**Step 5: Harvest Settlement Page Display**
After harvest submission, the page displays:
```
Harvest Settlement
--------------------------------
Total Harvest: 21.3 sacks
BUFIA Share Required: 2.37 sacks
Member Share: 18.93 sacks
Settlement Status: WAITING FOR DELIVERY
```

**Step 6: Rice Delivery**
- Farmer delivers the rice share to BUFIA
- Admin inputs:
  - `organization_share_received` (e.g., 2.37 sacks)

**Step 7: Automatic Completion**
- If `organization_share_received == organization_share_required` (within 0.01 tolerance):
  - System automatically updates:
    - `rental.settlement_status = 'paid'`
    - `rental.payment_status = 'paid_in_kind'`
    - `rental.status = 'completed'`
    - `rental.workflow_state = 'completed'`
    - `rental.actual_completion_time = current_time`
    - `machine.status = 'available'`
  - Admin does NOT manually complete the rental
  - Success message: "✅ Rice delivery confirmed (2.37 sacks). Settlement marked as PAID (IN-KIND). Rental automatically completed. Machine [name] is now available."

### 2. Online Payment

#### Workflow Steps:

**Step 1: Rental Approval**
- Member submits rental request
- Admin approves the rental
- System updates:
  - `rental.status = 'approved'`
  - `rental.payment_type = 'cash'`
  - `rental.payment_method = 'online'`
  - `rental.payment_status = 'pending'`

**Step 2: Payment Processing**
- Member completes online payment via Stripe
- System records:
  - `rental.stripe_session_id`
  - `rental.payment_date`
  - `rental.payment_amount`
- Creates Payment record with:
  - `internal_transaction_id` (auto-generated)
  - `status = 'completed'`

**Step 3: Payment Verification**
- Admin verifies the payment in Admin Dashboard
- Admin clicks "Verify Online Payment"
- System automatically updates:
  - `rental.payment_verified = True`
  - `rental.payment_status = 'paid'`
  - `rental.status = 'completed'`
  - `rental.workflow_state = 'completed'`
  - `machine.status = 'available'`

### 3. Face-to-Face Payment

#### Workflow Steps:

**Step 1: Rental Approval**
- Member submits rental request
- Admin approves the rental
- System updates:
  - `rental.status = 'approved'`
  - `rental.payment_type = 'cash'`
  - `rental.payment_method = 'face_to_face'`
  - `rental.payment_status = 'pending'`

**Step 2: Payment Recording**
- Member pays directly at the BUFIA office
- Admin records the payment by entering:
  - `payment_amount`
  - `payment_date`
  - `receipt_number`

**Step 3: Payment Confirmation**
- System automatically updates:
  - `rental.payment_status = 'paid'`
  - `rental.payment_verified = True`
  - `rental.status = 'completed'`
  - `rental.workflow_state = 'completed'`
  - `machine.status = 'available'`

## Machine Availability Logic

Machine availability depends on rental status:

- If `rental.workflow_state = 'in_progress'`:
  - `machine.status = 'rented'` (In Use)
  
- If `rental.status = 'completed'`:
  - `machine.status = 'available'`
  - Machine becomes available for new rentals immediately

## Admin Dashboard Display

The admin dashboard shows separate panels:

### 1. Pending Rental Requests
- All rentals with `status = 'pending'`
- Displays: Rental ID, Machine, Member Name, Request Date, Payment Type

### 2. Approved Rentals
- All rentals with `status = 'approved'` and `workflow_state = 'approved'`
- Displays: Rental ID, Machine, Member Name, Start Date, End Date, Payment Type, Payment Status

### 3. Rentals In Progress
- All rentals with `workflow_state = 'in_progress'`
- Displays: Rental ID, Machine, Member Name, Operator, Start Date, Status

### 4. Harvest Settlements (IN-KIND only)
- All IN-KIND rentals with:
  - `workflow_state = 'harvest_report_submitted'` OR
  - `settlement_status = 'waiting_for_delivery'`
- Displays:
  - Rental ID
  - Machine
  - Member Name
  - Total Harvest
  - BUFIA Share Required
  - Rice Delivered
  - Settlement Status

### 5. Completed Rentals
- All rentals with `status = 'completed'` OR `workflow_state = 'completed'`
- Displays: Rental ID, Machine, Member Name, Completion Date, Payment Type, Settlement Status

## Transaction History

The system stores complete transaction records including:

- `rental.id` - Rental ID
- `rental.user` - Member Name
- `rental.machine` - Machine
- `rental.payment_type` - Payment Type (in_kind, cash)
- `rental.payment_method` - Payment Method (online, face_to_face, null for in_kind)
- `rental.total_harvest_sacks` - Harvest Data (IN-KIND only)
- `rental.bufia_share` - BUFIA Share (IN-KIND only)
- `rental.organization_share_received` - Rice Delivered (IN-KIND only)
- `rental.payment_amount` - Payment Amount (Online/Face-to-Face)
- `rental.settlement_status` - Settlement Status
- `rental.settlement_reference` - Settlement Reference (IN-KIND)
- `rental.receipt_number` - Receipt Number (Face-to-Face)
- `rental.internal_transaction_id` - Transaction ID (via Payment model)
- `rental.created_at` - Transaction Date

## Key Features

### Decimal Support for Harvest
- The system accepts decimal values for harvest amounts
- Examples: 21, 21.3, 21.75, 100.5
- All calculations maintain 2 decimal places precision

### Automatic Completion
- IN-KIND rentals automatically complete when delivered rice equals required share
- No manual intervention needed from admin
- Machine automatically becomes available

### Machine Status Synchronization
- Machine status automatically updates based on rental workflow
- Prevents double-booking
- Ensures accurate availability display

### Transaction Tracking
- Every payment generates a unique transaction ID
- Complete audit trail for all transactions
- Easy reference for member inquiries

## Database Fields Reference

### Rental Model Key Fields:
- `payment_type`: 'cash' or 'in_kind'
- `payment_method`: 'online', 'face_to_face', or null
- `payment_status`: 'pending', 'paid', 'paid_in_kind'
- `settlement_status`: 'pending', 'waiting_for_delivery', 'paid'
- `workflow_state`: 'requested', 'approved', 'in_progress', 'harvest_report_submitted', 'completed'
- `status`: 'pending', 'approved', 'completed', 'rejected', 'cancelled'
- `total_harvest_sacks`: Decimal field for harvest amount
- `bufia_share`: Calculated BUFIA share
- `member_share`: Calculated member share
- `organization_share_required`: Required rice delivery
- `organization_share_received`: Actual rice delivered
- `settlement_reference`: Unique settlement reference
- `receipt_number`: Receipt number for face-to-face payments

### Machine Model Key Fields:
- `rental_price_type`: 'cash' or 'in_kind'
- `in_kind_farmer_share`: Default 9
- `in_kind_organization_share`: Default 1
- `allow_online_payment`: Boolean
- `allow_face_to_face_payment`: Boolean
- `settlement_type`: 'immediate' or 'after_harvest'

## Admin Actions

### For IN-KIND Rentals:
1. **Approve Rental** - Admin approves the rental request
2. **Assign Operator** (Optional) - Admin assigns an operator to the job
3. **Start Equipment Operation** - Admin marks equipment as in use
4. **Submit Harvest Report** - Admin OR Operator submits harvest data
5. **Confirm Rice Received** - Admin confirms delivery (triggers automatic completion)

### For Online Payments:
1. **Approve Rental** - Admin approves the rental request
2. **Verify Online Payment** - Admin verifies payment (triggers automatic completion)

### For Face-to-Face Payments:
1. **Approve Rental** - Admin approves the rental request
2. **Record Face-to-Face Payment** - Admin records payment (triggers automatic completion)

## Operator Actions

### For Assigned IN-KIND Rentals:
1. **Update Job Status** - Operator updates status (assigned → traveling → operating)
2. **Submit Harvest Report** - Operator directly submits harvest data from operator dashboard
   - Inputs: `total_harvest_sacks` (e.g., 21.3)
   - System calculates BUFIA share and member share
   - Admins receive notification for review
3. **Add Notes** - Operator can add notes about the job

## Role-Based Access

### Admin Role
- **Full Access** to all rental management functions
- Approves/rejects rental requests
- Assigns operators to jobs
- Starts equipment operation
- Submits harvest reports (if operator doesn't submit)
- Confirms rice delivery
- Verifies online payments
- Records face-to-face payments
- Views complete admin dashboard with all panels

### Operator Role
- **Limited Access** to assigned jobs only
- Views operator dashboard with assigned rentals
- Updates job status (traveling, operating, completed)
- **Directly submits harvest reports** from operator dashboard
- Adds notes about job progress
- Cannot approve/reject rentals
- Cannot confirm rice delivery (admin only)

### Member/User Role
- Submits rental requests
- Makes online payments
- Pays face-to-face at office
- Delivers rice for IN-KIND settlements
- Views their own rental history and status
- Receives notifications about rental status changes

### Models:
- `machines/models.py` - Rental, Machine, HarvestReport, Settlement models

### Views:
- `machines/admin_views.py` - Admin dashboard and workflow actions
- `machines/operator_views.py` - Operator dashboard and harvest submission
- `bufia/views/payment_views.py` - Payment processing

### Forms:
- `machines/forms_enhanced.py` - HarvestReportForm, ConfirmRiceReceivedForm, FaceToFacePaymentForm

### Templates:
- `templates/machines/admin/rental_dashboard.html` - Admin dashboard
- `templates/machines/admin/rental_approval.html` - Rental approval page
- `templates/machines/operator/dashboard.html` - Operator dashboard

### URLs:
- `machines/urls.py` - Rental and admin URLs
- `bufia/urls.py` - Payment URLs
