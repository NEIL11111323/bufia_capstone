# Payment + Admin Approval Workflow

## Updated Rental Process Flow

### ✅ New Workflow (Payment Does NOT Auto-Approve)

```
User Creates Rental Request
         │
         ▼
    Status: PENDING
         │
         ▼
User Completes Payment ────────────┐
         │                         │
         ▼                         │
Payment Verified = TRUE            │
Status: STILL PENDING              │
         │                         │
         ▼                         │
Notify User: "Payment received,    │
pending admin approval"            │
         │                         │
         ▼                         │
Notify Admins: "Paid rental        │
waiting for approval" ◄────────────┘
         │
         ▼
Admin Reviews Rental
         │
    ┌────┴────┐
    │         │
Approve    Reject
    │         │
    ▼         ▼
Status:   Status:
APPROVED  REJECTED
    │         │
    ▼         ▼
Notify    Notify
User      User
```

## Key Changes Made

### 1. Payment Success Handler Updated

**Before:**
```python
rental.status = 'approved'  # Auto-approved after payment ❌
```

**After:**
```python
rental.payment_verified = True
rental.payment_method = 'online'
rental.payment_date = timezone.now()
rental.stripe_session_id = session_id
# Status remains 'pending' for admin approval ✅
```

### 2. Notifications Added

**User Notification:**
```
"✅ Payment received for [Machine Name]. 
Your rental is now pending admin approval."
```

**Admin Notification:**
```
"💰 Payment received for rental request from [User Name] 
for [Machine Name]. Please review and approve."
```

### 3. Rental Status Flow

| Step | Status | Payment Verified | Can Use Machine |
|------|--------|------------------|-----------------|
| 1. Submit Request | `pending` | `False` | ❌ No |
| 2. Complete Payment | `pending` | `True` | ❌ No |
| 3. Admin Approves | `approved` | `True` | ✅ Yes |
| 4. Admin Rejects | `rejected` | `True` | ❌ No (Refund) |

## Benefits of This Workflow

### For Users:
✅ Payment confirms their commitment  
✅ Clear status tracking  
✅ Know exactly when they can use the machine  
✅ Protection against unauthorized charges  

### For Admins:
✅ Final control over machine availability  
✅ Can verify machine condition before approval  
✅ Can check for conflicts one more time  
✅ Payment already secured before approval  

### For Business:
✅ Reduced no-shows (payment commitment)  
✅ Better cash flow (payment upfront)  
✅ Quality control (admin final check)  
✅ Flexibility to handle special cases  

## Admin Approval Process

### Step 1: View Paid Rentals

Admins can filter rentals by:
- Status: `pending`
- Payment Verified: `True`

This shows all paid rentals waiting for approval.

### Step 2: Review Rental Details

Check:
- ✅ Machine is actually available
- ✅ No maintenance scheduled
- ✅ No conflicts with other rentals
- ✅ Machine is in good condition
- ✅ User is verified member

### Step 3: Approve or Reject

**If Approved:**
```python
rental.status = 'approved'
rental.save()
# User can now use the machine
```

**If Rejected:**
```python
rental.status = 'rejected'
rental.save()
# Initiate refund process
```

## Refund Process (If Rejected After Payment)

### Option 1: Automatic Refund via Stripe

```python
# In admin approval view
if reject_rental and rental.payment_verified:
    # Refund via Stripe
    if rental.stripe_session_id:
        payment_intent = stripe.PaymentIntent.retrieve(
            rental.stripe_session_id
        )
        refund = stripe.Refund.create(
            payment_intent=payment_intent.id,
            reason='requested_by_customer'
        )
        
        rental.status = 'rejected'
        rental.refund_issued = True
        rental.save()
```

### Option 2: Manual Refund

Admin can:
1. Mark rental as rejected
2. Process refund manually through Stripe dashboard
3. Update rental record with refund details

## Updated Rental Detail View

Show payment status clearly:

```html
<div class="rental-status-card">
    <h4>Rental Status</h4>
    
    <!-- Status Badge -->
    <span class="badge bg-{{ rental.status|yesno:'success,warning,danger' }}">
        {{ rental.get_status_display }}
    </span>
    
    <!-- Payment Status -->
    {% if rental.payment_verified %}
    <div class="alert alert-success mt-2">
        <i class="fas fa-check-circle"></i> Payment Verified
        <br>
        <small>Paid on: {{ rental.payment_date|date:"M d, Y h:i A" }}</small>
    </div>
    {% else %}
    <div class="alert alert-warning mt-2">
        <i class="fas fa-exclamation-triangle"></i> Payment Pending
        <br>
        <a href="{% url 'create_rental_payment' rental.id %}" class="btn btn-primary btn-sm mt-2">
            Complete Payment
        </a>
    </div>
    {% endif %}
    
    <!-- Approval Status -->
    {% if rental.status == 'pending' and rental.payment_verified %}
    <div class="alert alert-info mt-2">
        <i class="fas fa-clock"></i> Waiting for Admin Approval
        <br>
        <small>Your payment has been received. An admin will review your request shortly.</small>
    </div>
    {% elif rental.status == 'approved' %}
    <div class="alert alert-success mt-2">
        <i class="fas fa-check-circle"></i> Approved!
        <br>
        <small>You can use the machine from {{ rental.start_date }} to {{ rental.end_date }}</small>
    </div>
    {% elif rental.status == 'rejected' %}
    <div class="alert alert-danger mt-2">
        <i class="fas fa-times-circle"></i> Rejected
        <br>
        <small>A refund will be processed if payment was made.</small>
    </div>
    {% endif %}
</div>
```

## Admin Dashboard Updates

### Filter Options

Add filter for paid but pending rentals:

```python
# In admin view
paid_pending_rentals = Rental.objects.filter(
    status='pending',
    payment_verified=True
).order_by('created_at')
```

### Priority Queue

Show paid rentals first in approval queue:

```python
# Prioritize paid rentals
priority_rentals = Rental.objects.filter(
    status='pending',
    payment_verified=True
).order_by('payment_date')

# Then unpaid rentals
unpaid_rentals = Rental.objects.filter(
    status='pending',
    payment_verified=False
).order_by('created_at')
```

## Testing the New Workflow

### Test Case 1: Normal Flow
```
1. User creates rental ✅
2. User pays ✅
3. Status = pending, payment_verified = True ✅
4. Admin approves ✅
5. Status = approved ✅
6. User can use machine ✅
```

### Test Case 2: Rejection After Payment
```
1. User creates rental ✅
2. User pays ✅
3. Admin rejects (machine broken) ✅
4. Status = rejected ✅
5. Refund initiated ✅
6. User notified ✅
```

### Test Case 3: No Payment
```
1. User creates rental ✅
2. User doesn't pay ❌
3. Status = pending, payment_verified = False
4. Admin can't approve (no payment)
5. Rental expires after X days
```

## Configuration Options

### Option 1: Require Payment Before Approval
```python
# In admin approval view
if not rental.payment_verified:
    messages.error(request, 'Cannot approve rental without payment')
    return redirect('machines:rental_list')
```

### Option 2: Allow Approval Without Payment (Face-to-Face)
```python
# For face-to-face payments
if rental.payment_method == 'face_to_face':
    # Admin can approve without online payment
    rental.status = 'approved'
    rental.save()
```

### Option 3: Auto-Expire Unpaid Rentals
```python
# In management command (run daily)
from datetime import timedelta

expired_rentals = Rental.objects.filter(
    status='pending',
    payment_verified=False,
    created_at__lt=timezone.now() - timedelta(days=3)
)

expired_rentals.update(status='cancelled')
```

## Summary

### What Changed:
✅ Payment no longer auto-approves rentals  
✅ Status remains "pending" after payment  
✅ Admin must manually approve even after payment  
✅ Users and admins get proper notifications  
✅ Clear distinction between payment and approval  

### Why This Is Better:
✅ Admin has final control  
✅ Can verify machine availability  
✅ Can check machine condition  
✅ Payment secures user commitment  
✅ Reduces no-shows  
✅ Better business process  

### Next Steps:
1. ✅ Payment handler updated
2. ✅ Webhook handler updated
3. ✅ Notifications added
4. [ ] Update rental detail template
5. [ ] Update admin dashboard
6. [ ] Add refund functionality
7. [ ] Test the workflow

---

**Document Version**: 1.0  
**Last Updated**: December 2, 2024  
**Status**: ✅ Payment Handler Updated
