# Complete Payment Flow Verification - User to Admin

## Overview
This document traces the complete flow from user payment to admin dashboard.

## Flow Diagram

```
USER SIDE                    SYSTEM                      ADMIN SIDE
─────────                    ──────                      ──────────

1. Click "Proceed to Payment"
   ↓
2. Redirected to Stripe
   ↓
3. Enter card details
   ↓
4. Complete payment
   ↓
                          5. Stripe Webhook Triggered
                             - payment_verified = True
                             - payment_status = 'paid'
                             - workflow_state = 'in_progress'
                             - machine.status = 'rented'
                             - actual_handover_date = now
   ↓
6. Redirected to Success Page
   - Shows transaction ID
   - Shows "In Progress" status
   ↓
7. User sees rental in
   "In Progress" section
                                                      8. Admin Dashboard Updates
                                                         - Rental appears in
                                                           "In Progress" tab
                                                         - Stats updated
                                                         - Can assign operator
```

## Detailed Step-by-Step Process

### Step 1: User Initiates Payment
**Location**: `/machines/rentals/` (User rental list)
**Action**: User clicks "Proceed to Payment" button
**Requirements**:
- Rental status must be `approved`
- Payment method must be `online`
- Payment not yet verified

### Step 2: Create Stripe Session
**Function**: `create_rental_payment()` in `bufia/views/payment_views.py`
**Process**:

```python
# Calculate amount
amount = rental.payment_amount * 100  # Convert to centavos

# Create Stripe checkout session
checkout_session = stripe.checkout.Session.create(
    payment_method_types=['card'],
    line_items=[{...}],
    mode='payment',
    success_url='payment_success?session_id={CHECKOUT_SESSION_ID}&type=rental&id={rental_id}',
    cancel_url='payment_cancelled?type=rental&id={rental_id}',
    metadata={
        'rental_id': rental_id,
        'user_id': user_id,
        'type': 'rental'
    }
)

# Redirect user to Stripe
return redirect(checkout_session.url)
```

### Step 3: User Completes Payment on Stripe
**Location**: Stripe hosted checkout page
**User Actions**:
- Enters card details
- Confirms payment
- Stripe processes payment

### Step 4: Stripe Webhook Processes Payment
**Function**: `stripe_webhook()` in `bufia/views/payment_views.py`
**Trigger**: Stripe sends `checkout.session.completed` event
**Process**:
```python
# Get rental
rental = Rental.objects.get(pk=rental_id)

# Update payment info
rental.payment_verified = True
rental.payment_method = 'online'
rental.payment_date = timezone.now()
rental.stripe_session_id = session_id
rental.payment_status = 'paid'
rental.payment_amount = paid_amount

# AUTOMATIC WORKFLOW TRANSITION
if rental.status == 'approved':
    rental.workflow_state = 'in_progress'
    rental.actual_handover_date = timezone.now()
    
    # Update machine status
    rental.machine.status = 'rented'
    rental.machine.save()

rental.save()

# Create Payment record
Payment.objects.create(
    user=user,
    payment_type='rental',
    amount=paid_amount,
    status='completed',
    stripe_session_id=session_id,
    paid_at=timezone.now()
)
```

**Database Changes**:
| Field | Before | After |
|-------|--------|-------|
| payment_verified | False | True |
| payment_status | 'to_be_determined' | 'paid' |
| payment_date | NULL | 2026-03-12 10:30:00 |
| workflow_state | 'approved' | 'in_progress' ✅ |
| actual_handover_date | NULL | 2026-03-12 10:30:00 |
| machine.status | 'available' | 'rented' |

### Step 5: User Redirected to Success Page
**Function**: `payment_success()` in `bufia/views/payment_views.py`
**URL**: `/payment/success/?session_id=xxx&type=rental&id=123`
**Process**:
```python
# Retrieve session from Stripe
session = stripe.checkout.Session.retrieve(session_id)

# Get rental
rental = Rental.objects.get(pk=item_id)

# Create notifications
UserNotification.objects.create(
    user=request.user,
    notification_type='rental_payment_completed',
    message=f'Payment received for {rental.machine.name}...'
)

# Notify admins
for admin in admins:
    UserNotification.objects.create(
        user=admin,
        notification_type='rental_payment_received',
        message=f'Payment received from {user.name}...'
    )

# Redirect to rental detail
return redirect('machines:rental_detail', pk=rental.id)
```

**User Sees**:
- Success message
- Transaction ID
- Rental details
- Status: "In Progress"

### Step 6: User Views Updated Rental List
**URL**: `/machines/rentals/`
**Template**: `templates/machines/rental_list_organized.html`
**View**: `rental_list()` in `machines/views.py`

**Query**:
```python
in_progress_rentals = user_rentals.filter(
    workflow_state='in_progress'
).order_by('start_date', 'created_at')
```

**User Sees**:
- Rental moved from "Approved" to "In Progress" section
- Blue badge: "ACTIVE"
- No payment buttons (already paid)
- "View Details" button

### Step 7: Admin Dashboard Updates
**URL**: `/machines/admin/rentals/`
**Template**: `templates/machines/admin/rental_dashboard.html`
**View**: `admin_rental_dashboard()` in `machines/admin_views.py`

**Queries**:
```python
# Statistics
stats = {
    'pending_requests': Rental.objects.filter(status='pending').count(),
    'approved_rentals': Rental.objects.filter(
        status='approved', 
        workflow_state='approved'
    ).count(),
    'rentals_in_progress': Rental.objects.filter(
        workflow_state='in_progress'  # ✅ Includes our rental
    ).count(),
    'completed_rentals': Rental.objects.filter(
        Q(status='completed') | Q(workflow_state='completed')
    ).count(),
}

# Tab counts
tab_counts = {
    'pending': filtered_rentals.filter(status='pending').count(),
    'approved': filtered_rentals.filter(
        status='approved', 
        workflow_state='approved'
    ).count(),
    'in_progress': filtered_rentals.filter(
        workflow_state='in_progress'  # ✅ Our rental appears here
    ).count(),
    'completed': filtered_rentals.filter(...).count(),
}

# Get rentals for active tab
if active_tab == 'in_progress':
    rentals = filtered_rentals.filter(
        workflow_state='in_progress'  # ✅ Returns our rental
    )
```

**Admin Sees**:
- "In Progress" count increased by 1
- Rental appears in "In Progress" tab
- Payment verified badge (green checkmark)
- Can assign operator
- Can mark as complete

## Verification Checklist

### ✅ User Side
- [ ] "Proceed to Payment" button visible for approved rentals
- [ ] Redirects to Stripe checkout
- [ ] After payment, redirects to success page
- [ ] Rental appears in "In Progress" section
- [ ] No more payment buttons shown
- [ ] Transaction ID displayed

### ✅ System Side
- [ ] Webhook receives payment event
- [ ] `payment_verified` set to True
- [ ] `payment_status` set to 'paid'
- [ ] `workflow_state` changed to 'in_progress'
- [ ] `actual_handover_date` recorded
- [ ] Machine status changed to 'rented'
- [ ] Payment record created
- [ ] Notifications sent to user and admins

### ✅ Admin Side
- [ ] "In Progress" count increases
- [ ] Rental appears in "In Progress" tab
- [ ] Payment verified badge shown
- [ ] Can assign operator
- [ ] Can mark as complete
- [ ] Notification received

## Key Files Modified

1. **bufia/views/payment_views.py** (Line 538-548)
   - Updated webhook to automatically move to 'in_progress'
   - Updates machine status to 'rented'

2. **machines/views.py** (Line 492-570)
   - Updated rental_list view
   - Changed template to rental_list_organized.html
   - Provides correct context variables

3. **templates/machines/rental_list_organized.html**
   - New organized template
   - Shows rentals by status sections
   - Fixed payment URL

## Testing Steps

1. **As User**:
   ```
   1. Login as regular user
   2. Go to /machines/rentals/
   3. Find approved rental with "Proceed to Payment"
   4. Click button
   5. Complete payment on Stripe (use test card: 4242 4242 4242 4242)
   6. Verify redirect to success page
   7. Check rental moved to "In Progress"
   ```

2. **As Admin**:
   ```
   1. Login as admin
   2. Go to /machines/admin/rentals/
   3. Click "In Progress" tab
   4. Verify rental appears with payment verified badge
   5. Click "Assign Operator" (optional)
   6. Click "Mark as Complete" when done
   ```

## Expected Results

**Before Payment**:
- Status: `approved`
- Workflow State: `approved`
- Payment Status: `to_be_determined`
- Machine Status: `available`

**After Payment** (Automatic):
- Status: `approved`
- Workflow State: `in_progress` ✅
- Payment Status: `paid`
- Machine Status: `rented`

**After Admin Marks Complete**:
- Status: `completed`
- Workflow State: `completed`
- Machine Status: `available`

## Summary

The complete flow is now automated:
1. User pays → Webhook processes → Automatically moves to "In Progress"
2. Admin sees rental in "In Progress" tab
3. Admin can assign operator and manage the rental
4. Admin marks as complete when work is done

No manual intervention needed between payment and "In Progress" status!
