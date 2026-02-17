# Complete Rental Information Display Requirements

## Overview
This document outlines all rental information fields that should be displayed across different views in the BUFIA system.

## Available Rental Fields (from Model)

### Basic Information
- **Machine**: `rental.machine.name` - The equipment being rented
- **User**: `rental.user.get_full_name()` or `rental.user.username` - Who is renting
- **Start Date**: `rental.start_date` - When rental begins
- **End Date**: `rental.end_date` - When rental ends
- **Purpose**: `rental.purpose` - Why the equipment is needed
- **Status**: `rental.status` - Current rental status (pending/approved/rejected/cancelled/completed)

### Dates & Timestamps
- **Created At**: `rental.created_at` - When rental request was submitted
- **Updated At**: `rental.updated_at` - Last modification time
- **Duration**: `rental.get_duration_days()` - Number of days (calculated)

### Payment Information
- **Payment Amount**: `rental.payment_amount` - Total cost
- **Payment Date**: `rental.payment_date` - When payment was made
- **Payment Method**: `rental.payment_method` - Online or Face-to-Face
- **Payment Slip**: `rental.payment_slip` - Uploaded proof of payment
- **Payment Verified**: `rental.payment_verified` - Admin verification status
- **Stripe Session ID**: `rental.stripe_session_id` - For online payments
- **Verification Date**: `rental.verification_date` - When admin verified
- **Verified By**: `rental.verified_by` - Which admin verified

### Calculated Properties
- **Total Cost**: `rental.total_cost` - Calculated rental cost
- **Booking Status**: `rental.booking_status_display` - User-friendly status
- **Days Until Start**: `rental.days_until_start` - Days remaining before rental
- **Days Since End**: `rental.days_since_end` - Days after rental ended
- **Can Be Approved**: `rental.can_be_approved` - If admin can approve
- **Has Conflicts**: `rental.has_conflicts()` - If dates overlap with others

## Display Requirements by View

### 1. User Dashboard - Recent Rentals Table
**Currently Displayed:**
- ✅ Machine name (with icon)
- ✅ User name (with avatar)
- ✅ Rental period (start - end dates)
- ✅ Status badge

**Should Also Display:**
- ⚠️ Payment status (verified/pending)
- ⚠️ Total cost
- ⚠️ Duration (number of days)
- ⚠️ Purpose (truncated)
- ⚠️ Days until start (for upcoming rentals)

### 2. Admin Rental Dashboard
**Should Display:**
- ✅ Machine name
- ✅ User name
- ✅ Rental period
- ✅ Status
- ⚠️ Payment verification status
- ⚠️ Payment method
- ⚠️ Payment amount
- ⚠️ Created date
- ⚠️ Purpose
- ⚠️ Conflicts indicator
- ⚠️ Action buttons (Approve/Reject/View)

### 3. Rental Detail View
**Should Display ALL Information:**
- Machine details (name, type, image)
- User details (name, contact)
- Rental dates (start, end, duration)
- Purpose
- Status with timeline
- Payment information:
  - Amount
  - Method
  - Date paid
  - Verification status
  - Payment slip (if uploaded)
  - Verified by (admin name)
  - Verification date
- Timestamps (created, updated)
- Conflict warnings (if any)
- Action buttons based on status

### 4. Rental List/History View
**Should Display:**
- ✅ Machine name
- ✅ Rental period
- ✅ Status
- ⚠️ Payment status
- ⚠️ Total cost
- ⚠️ Duration
- ⚠️ Created date
- ⚠️ Filter options (by status, date range, machine)

### 5. User's My Rentals View
**Should Display:**
- Machine name with image
- Rental period
- Status
- Payment status
- Total cost
- Purpose
- Days until start (for upcoming)
- Action buttons (Cancel, View Details, Pay)

## Recommended Enhancements

### Visual Indicators
1. **Payment Status Badge**
   - 🟢 Verified (green)
   - 🟡 Pending Verification (yellow)
   - 🔴 Not Paid (red)

2. **Rental Status Badge**
   - 🟢 Approved (green)
   - 🟡 Pending (yellow)
   - 🔴 Rejected (red)
   - ⚫ Cancelled (gray)
   - 🔵 Completed (blue)

3. **Timeline Indicators**
   - 📅 Upcoming (future start date)
   - ⏳ Active (currently ongoing)
   - ✅ Completed (past end date)

### Additional Information to Display
1. **Conflict Warnings**: Show if rental dates overlap with others
2. **Machine Availability**: Real-time status
3. **Cost Breakdown**: Show calculation (days × rate)
4. **Payment Receipt**: Link to download receipt
5. **Booking Reference**: Unique rental ID for tracking

## Implementation Priority

### High Priority (Implement First)
1. ✅ Payment verification status badge
2. ✅ Total cost display
3. ✅ Duration calculation
4. ✅ Payment method indicator

### Medium Priority
1. Days until start/since end
2. Purpose field (truncated in lists)
3. Conflict warnings
4. Payment slip preview

### Low Priority
1. Detailed timeline view
2. Cost breakdown modal
3. Receipt download
4. Booking reference QR code

## Current Status

### ✅ Already Implemented
- Machine name display
- User name display
- Rental period (start - end dates)
- Status badges
- Basic table layout with gradient styling
- Thicker borders for clarity

### ⚠️ Needs Implementation
- Payment verification status
- Total cost display
- Duration display
- Purpose field
- Days until start indicator
- Payment method badge
- Conflict warnings
- Enhanced detail view

## Next Steps

1. **Update User Dashboard Template**
   - Add payment status column
   - Add total cost column
   - Add duration display
   - Add purpose tooltip

2. **Update Admin Dashboard Template**
   - Add payment verification column
   - Add payment method indicator
   - Add conflict warnings
   - Add bulk action checkboxes

3. **Create Rental Detail View**
   - Full information display
   - Payment proof viewer
   - Status timeline
   - Action buttons

4. **Add Filtering & Search**
   - Filter by status
   - Filter by payment status
   - Date range picker
   - Machine type filter

## Design Consistency

All rental displays should follow the unified design system:
- 24px border radius for containers
- Gradient backgrounds (white to light gray)
- Thicker borders (2-3px) for clarity
- Consistent color coding:
  - Primary green (#047857) for approved/verified
  - Yellow (#F59E0B) for pending
  - Red (#EF4444) for rejected/unpaid
  - Gray (#6B7280) for cancelled
  - Blue (#3B82F6) for completed

---

**Document Created**: December 4, 2025
**Status**: Requirements Complete - Ready for Implementation
