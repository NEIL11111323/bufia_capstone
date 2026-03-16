# Admin Membership Dashboard Guide

## Overview
The new Admin Membership Dashboard provides a comprehensive view of all membership applications with proper workflow management and transaction tracking.

## Key Features

### 1. Transaction ID System
Every membership application gets a unique transaction ID:
- **Format:** `BUFIA-MEM-XXXXX` (e.g., BUFIA-MEM-00001)
- **Generated:** When membership application is created
- **Visible:** In all admin views, notifications, and confirmations
- **Purpose:** Track payments and approvals throughout the workflow

### 2. Application Status Categories

The dashboard organizes applications into 4 categories:

#### A. Pending Payment (Yellow)
- Applications submitted but payment not yet received
- Shows: Transaction ID, member info, submission date, payment method
- **Action:** Admin can mark as paid when payment is received

#### B. Payment Received (Blue) - PRIORITY
- Payment confirmed but membership not yet approved
- **This is the main action queue for admins**
- Shows: Transaction ID, payment method, payment date
- **Actions:** 
  - Approve Membership (verify user)
  - Reject Application

#### C. Approved Members (Green)
- Fully verified and active members
- Shows: Transaction ID, approval date, assigned sector, reviewer
- **Status:** Can now rent machines and use all services

#### D. Rejected Applications (Red)
- Applications that were rejected
- Shows: Transaction ID, rejection date, reason, reviewer
- **Status:** User must reapply

### 3. Workflow Process

#### For Online Payments:
```
1. User submits form → Transaction ID generated (BUFIA-MEM-XXXXX)
2. User pays ₱500 online → Payment status: "paid"
3. Appears in "Payment Received" section
4. Admin clicks "Approve Membership"
5. Admin assigns sector
6. User becomes verified → Can rent machines
```

#### For Face-to-Face Payments:
```
1. User submits form → Transaction ID generated (BUFIA-MEM-XXXXX)
2. Appears in "Pending Payment" section
3. User visits office with ₱500 cash
4. Admin clicks "Mark as Paid" → Payment status: "paid"
5. Moves to "Payment Received" section
6. Admin clicks "Approve Membership"
7. Admin assigns sector
8. User becomes verified → Can rent machines
```

### 4. Important Rules

#### Payment Required Before Approval
- **Cannot approve membership without payment**
- System validates payment status before allowing verification
- If admin tries to verify unpaid application, they get warning message

#### Two-Step Process
1. **Step 1:** Mark payment as received (for face-to-face) or automatic (for online)
2. **Step 2:** Approve membership and assign sector

This ensures:
- All payments are tracked
- No member is verified without paying
- Clear audit trail with transaction IDs

### 5. Admin Actions

#### Mark as Paid (Face-to-Face Payments)
**Location:** Pending Payment section
**Button:** "Mark as Paid"
**Process:**
1. Click "Mark as Paid" button
2. Review payment details and transaction ID
3. Confirm payment received
4. Application moves to "Payment Received" section
5. User receives notification with transaction ID

#### Approve Membership
**Location:** Payment Received section
**Button:** "Approve Membership"
**Process:**
1. Click "Approve Membership" button
2. Review member information and transaction ID
3. Select appropriate sector from dropdown
4. Confirm approval
5. User becomes verified
6. User receives notification with transaction ID

#### Reject Application
**Location:** Payment Received or Pending Payment sections
**Button:** "Reject"
**Process:**
1. Click "Reject" button
2. Enter rejection reason
3. Confirm rejection
4. User receives notification with reason
5. Application moves to "Rejected" section

### 6. Dashboard Statistics

Top of dashboard shows 4 cards:
- **Pending Payment:** Count of applications awaiting payment
- **Payment Received:** Count of paid applications awaiting approval (ACTION NEEDED)
- **Approved Members:** Total verified members
- **Rejected:** Total rejected applications

### 7. Notifications

All actions trigger notifications with transaction IDs:

#### When Payment Marked as Paid:
- **To User:** "Your ₱500 membership fee payment has been confirmed (Transaction ID: BUFIA-MEM-XXXXX). Your application is now pending final approval."

#### When Membership Approved:
- **To User:** "Your membership has been approved on [DATE] (Transaction ID: BUFIA-MEM-XXXXX). You can now rent machines and access all BUFIA services."

#### When Payment Received Online:
- **To Admins:** "Membership payment received from [NAME] (Transaction ID: BUFIA-MEM-XXXXX). Application is ready for review."

### 8. Access Control

#### Non-Verified Users:
- ✅ CAN view all machines and features
- ✅ CAN browse services and pricing
- ❌ CANNOT create rental requests
- ❌ CANNOT make transactions
- **Notification:** When they try to rent, they see: "⚠️ Membership verification required! Please pay the ₱500 membership fee..."

#### Verified Users:
- ✅ Full access to all features
- ✅ Can rent machines
- ✅ Can make transactions
- ✅ Can use all BUFIA services

### 9. URL Routes

- **Dashboard:** `/users/` (redirects to membership dashboard)
- **Mark as Paid:** `/users/<user_id>/mark-paid/`
- **Verify User:** `/users/<user_id>/verify/`
- **Reject:** `/users/<user_id>/reject/`
- **Members Masterlist:** `/members/masterlist/`

### 10. Best Practices

#### Daily Workflow:
1. Check "Payment Received" section first (blue card)
2. Process all paid applications
3. Assign appropriate sectors
4. Check "Pending Payment" section
5. Follow up with members who haven't paid

#### Payment Verification:
- For face-to-face: Only mark as paid after physically receiving ₱500
- For online: Payment is automatic, just verify and approve
- Always check transaction ID matches

#### Sector Assignment:
- Required for all members
- Select based on farm location
- Can be updated later if needed

### 11. Troubleshooting

#### "Cannot verify - payment not received"
- **Cause:** Trying to approve before marking payment as paid
- **Solution:** First mark payment as paid, then approve

#### Transaction ID not showing
- **Cause:** Old application created before system update
- **Solution:** Transaction ID generates automatically on first save

#### User still can't rent after approval
- **Check:** User.is_verified = True
- **Check:** MembershipApplication.is_approved = True
- **Check:** Payment status = "paid"

### 12. Database Fields Reference

#### MembershipApplication Model:
- `payment_status`: 'pending', 'paid', 'waived'
- `payment_method`: 'online', 'face_to_face'
- `payment_date`: Timestamp of payment
- `is_approved`: Boolean for approval status
- `is_rejected`: Boolean for rejection status
- `review_date`: Date of admin review
- `reviewed_by`: Admin who reviewed

#### CustomUser Model:
- `is_verified`: Boolean - controls access to rentals
- `membership_form_submitted`: Boolean
- `membership_form_date`: Date of submission
- `membership_approved_date`: Date of approval

## Summary

The new dashboard provides:
- ✅ Clear workflow with transaction IDs
- ✅ Organized by status for easy processing
- ✅ Payment verification before approval
- ✅ Automatic notifications with tracking
- ✅ Complete audit trail
- ✅ Prevents unauthorized access to rentals

This ensures all members pay the ₱500 fee before being verified and gaining access to rental services.
