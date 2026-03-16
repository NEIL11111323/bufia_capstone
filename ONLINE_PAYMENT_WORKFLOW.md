# Online Payment Workflow for Equipment Rentals

## Complete Workflow After "Proceed to Payment"

### Step-by-Step Process

#### 1. User Submits Rental Request
- User selects machine and dates
- Chooses "Online Payment" method
- Submits rental request
- **Status**: `pending`
- **Workflow State**: `requested`
- **Payment Status**: `to_be_determined`

#### 2. Admin Reviews and Approves
- Admin reviews rental request in dashboard
- Checks date availability
- Approves the rental
- **Status**: `approved`
- **Workflow State**: `approved`
- **Payment Status**: `to_be_determined`
- User now sees "Proceed to Payment" button

#### 3. User Completes Payment
- User clicks "Proceed to Payment"
- Redirected to Stripe checkout page
- Enters card details and completes payment
- Stripe processes payment

#### 4. Automatic Processing (Webhook)
After successful payment, the system automatically:
- Sets `payment_verified = True`
- Sets `payment_status = 'paid'`
- Records `payment_date`
- **Moves to In Progress**: `workflow_state = 'in_progress'`
- Records `actual_handover_date`
- Updates machine status to `rented`
- Creates Payment record in database

**Status**: `approved`
**Workflow State**: `in_progress` ✅
**Payment Status**: `paid`

#### 5. Admin Assigns Operator (Optional)
- Admin can assign an operator to the rental
- Operator receives notification
- Operator updates status as they work

#### 6. Work Completion
Two ways to complete:

**Option A: Admin Marks Complete**
- Admin goes to rental dashboard
- Clicks "Mark as Complete"
- **Status**: `completed`
- **Workflow State**: `completed`
- Machine becomes available again

**Option B: Operator Reports Completion**
- Operator submits harvest report (for IN-KIND)
- Or marks work as done
- Admin verifies and marks complete

## What Happens in Each Status

### Approved (Payment Pending)
- Rental is approved by admin
- Waiting for user payment
- Machine is reserved but not yet rented
- User sees: "Proceed to Payment" button

### In Progress (After Payment)
- Payment completed successfully
- Machine is actively rented
- Machine status: `rented`
- Operator can be assigned
- User sees: "In Progress" badge

### Completed
- Work is finished
- Machine returned/work done
- Machine status: `available`
- User sees: "Completed" badge
- Can print receipt

## User View After Payment

After clicking "Proceed to Payment" and completing payment:

1. **Immediate**: Redirected to success page
2. **Within seconds**: Webhook processes payment
3. **Status changes to**: "In Progress"
4. **User sees**:
   - Rental moved to "In Progress" section
   - Blue badge showing "ACTIVE"
   - No more payment buttons
   - "View Details" button

## Admin View After Payment

Admin dashboard shows:
- Rental automatically moved to "In Progress" section
- Payment verified badge
- Can assign operator
- Can mark as complete when work is done

## Technical Details

### Webhook Handler
Location: `bufia/views/payment_views.py` - `stripe_webhook()`

```python
# After successful payment:
rental.payment_verified = True
rental.payment_status = 'paid'
rental.workflow_state = 'in_progress'  # Automatic transition
rental.actual_handover_date = timezone.now()
rental.machine.status = 'rented'
```

### Database Changes
- `payment_verified`: False → True
- `payment_status`: 'to_be_determined' → 'paid'
- `workflow_state`: 'approved' → 'in_progress'
- `payment_date`: NULL → current timestamp
- `actual_handover_date`: NULL → current timestamp
- Machine `status`: 'available' → 'rented'

## Benefits of Automatic Workflow

1. **Faster Processing**: No manual admin intervention needed
2. **Better UX**: User immediately sees progress
3. **Accurate Tracking**: Timestamps recorded automatically
4. **Machine Management**: Machine status updated automatically
5. **Clear Status**: User knows work can begin

## Next Steps for Admin

After payment is processed:

1. **Assign Operator** (if needed)
   - Go to rental detail page
   - Click "Assign Operator"
   - Select operator from list

2. **Monitor Progress**
   - Check operator updates
   - View in "In Progress" section

3. **Mark as Complete**
   - When work is finished
   - Click "Mark as Complete"
   - Machine becomes available

## Notifications

The system should send notifications at each step:
- ✅ Payment successful (to user)
- ✅ Rental in progress (to user)
- ✅ Operator assigned (to operator)
- ✅ Work completed (to user)

## Summary

**Before**: User pays → Stays in "Approved" → Admin manually moves to "In Progress"

**After (Current)**: User pays → Automatically moves to "In Progress" → Admin assigns operator → Admin marks complete

This creates a smooth, automated workflow that reduces manual work and provides better user experience.
