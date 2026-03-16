# Admin Payment Verification Process

## Current Situation (Based on Screenshot)

You're on: `http://127.0.0.1:8000/machines/admin/rental/62/approve/`

**Rental Status**:
- Status: `APPROVED (AWAITING ONLINE PAYMENT VERIFICATION)`
- Workflow: `Online Payment`
- Payment: `ONLINE PAYMENT` - PHP 7500.00
- Transaction ID: `BUFI-TXN-2026-00001`
- Transaction Date: `Mar 13, 2026 05:58 AM`
- Verified: `⏳ No` (Yellow badge)

## What Needs to Happen

The rental has been:
1. ✅ Submitted by user
2. ✅ Approved by admin (you)
3. ✅ Paid by user online (via Stripe)
4. ✅ Automatically moved to "In Progress" by webhook

Now the admin needs to:
5. **Verify the online payment and mark as complete**

## How to Complete the Process

### Option 1: Use the "Verify Online Payment" Button (Recommended)

On the same page, scroll down to the "Admin Actions" section on the right side.

You should see a section titled:
```
🔹 Online Payment Verification
```

Under this section, there should be a button:
```
[Verify Online Payment and Complete Rental]
```

**Click this button** to:
- Mark payment as verified
- Set status to `completed`
- Set workflow_state to `completed`
- Free up the machine for new bookings
- Send completion notification to user

### Option 2: Use the Decision Dropdown

If you want to manually mark it as complete:

1. In the "Decision" dropdown, select: `Completed`
2. Add admin notes (optional)
3. Click "Submit Decision"

This will also mark the rental as complete.

## What Happens After Verification

### Database Changes:
| Field | Before | After |
|-------|--------|-------|
| payment_verified | False | True ✅ |
| status | 'approved' | 'completed' ✅ |
| workflow_state | 'in_progress' | 'completed' ✅ |
| verification_date | NULL | Current timestamp |
| verified_by | NULL | Admin user |
| actual_completion_time | NULL | Current timestamp |
| machine.status | 'rented' | 'available' ✅ |

### User Notification:
User receives notification:
```
✅ Your online payment for TRACTOR has been verified.
Transaction ID: BUFI-TXN-2026-00001.
```

### Admin Dashboard:
- Rental moves from "In Progress" to "Completed" section
- Machine becomes available for new bookings
- Statistics updated

## Complete Workflow Summary

```
USER ACTIONS                 ADMIN ACTIONS                SYSTEM STATUS
───────────                  ─────────────                ─────────────

1. Submit rental request  →                              status: pending
                                                          
                          →  2. Approve rental        →  status: approved
                                                          workflow: approved
                                                          
3. Pay online (Stripe)    →                              payment_verified: True
                                                          payment_status: paid
                                                          workflow: in_progress ✅
                                                          (automatic via webhook)
                                                          
                          →  4. Verify payment       →  status: completed ✅
                             and mark complete           workflow: completed ✅
                                                          machine: available ✅
```

## Why Two Steps (Approve + Verify)?

This two-step process provides:

1. **Admin Control**: Admin approves the rental request first
2. **Payment Confirmation**: User pays after approval
3. **Final Verification**: Admin verifies payment was received correctly
4. **Completion**: Rental is marked as complete

## Current Issue

Based on your screenshot, the rental is stuck at step 3 (payment received, but not verified).

**Solution**: Click the "Verify Online Payment and Complete Rental" button to move to step 4.

## Alternative: Automatic Completion

If you want payments to be automatically marked as complete without admin verification, we can modify the webhook to:

```python
# In stripe_webhook function
if rental.status == 'approved':
    rental.workflow_state = 'in_progress'
    rental.actual_handover_date = timezone.now()
    
    # NEW: Automatically mark as completed for online payments
    rental.status = 'completed'
    rental.workflow_state = 'completed'
    rental.payment_verified = True
    rental.verification_date = timezone.now()
    rental.actual_completion_time = timezone.now()
    
    rental.machine.status = 'available'  # Free up machine immediately
    rental.machine.save()
```

This would skip the manual verification step entirely.

## Recommendation

**Current System (Manual Verification)** is better because:
- Admin can review each payment
- Catch any payment issues
- Verify amounts match
- Add notes if needed

**Automatic Completion** is faster but:
- No admin oversight
- Can't catch payment discrepancies
- Less control over workflow

## Next Steps

1. Go to: `http://127.0.0.1:8000/machines/admin/rental/62/approve/`
2. Scroll to "Online Payment Verification" section
3. Click "Verify Online Payment and Complete Rental"
4. Rental will be marked as complete
5. Machine becomes available
6. User receives completion notification

Done!
