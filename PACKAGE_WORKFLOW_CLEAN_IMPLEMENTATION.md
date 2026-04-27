# Package Rental Workflow - Clean Implementation Guide

## Overview
This document defines the clean, simplified workflow for package rentals with clear state transitions and payment rules.

## Workflow States

### Package Item States
```
requested → scheduled → approved → waiting_operator_assignment → 
  ├─ ready_for_payment (cash) → payment_submitted → payment_verified → in_operation → completed
  └─ ready_for_operation (in-kind) → in_operation → harvest_recorded → rice_delivery_confirmed → completed
```

### Rental Workflow States
```python
WORKFLOW_STATE_CHOICES = [
    ('pending', 'Pending'),
    ('scheduled', 'Scheduled'),
    ('approved', 'Approved'),
    ('waiting_operator_assignment', 'Waiting Operator Assignment'),
    ('ready_for_payment', 'Ready for Payment'),  # Cash only
    ('ready_for_operation', 'Ready for Operation'),  # In-kind or cash after payment
    ('payment_submitted', 'Payment Submitted'),  # Cash only
    ('payment_verified', 'Payment Verified'),  # Cash only
    ('in_operation', 'In Operation'),
    ('harvest_recorded', 'Harvest Recorded'),  # In-kind only
    ('rice_delivery_confirmed', 'Rice Delivery Confirmed'),  # In-kind only
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]
```

## Complete Flow

### Step 1: User Creates Package
**User Action:**
- Selects needed services/machines
- Provides farm details
- Submits package request

**Result:**
- Package status: `pending`
- All items status: `requested`

### Step 2: Admin Schedules Services
**Admin Action:**
- Assigns machine to each service
- Sets schedule dates
- Confirms schedule

**Result:**
- Item status: `requested` → `scheduled`
- Rental created with workflow_state: `scheduled`

### Step 3: Admin Approves Package
**Admin Action:**
- Reviews all scheduled services
- Clicks "Approve Package"

**Result:**
- Package status: `approved`
- All rentals workflow_state: `scheduled` → `approved`

### Step 4: Admin Assigns Operators
**Admin Action:**
- Assigns operator to each machine that needs one

**Automatic Transition:**
```python
# After operator assignment
if all_operators_assigned:
    if rental.payment_type == 'cash':
        rental.workflow_state = 'ready_for_payment'
    else:  # in_kind
        rental.workflow_state = 'ready_for_operation'
```

**Result:**
- Cash rentals: workflow_state → `ready_for_payment`
- In-kind rentals: workflow_state → `ready_for_operation`

### Step 5A: Cash Rental Payment Flow

**5A.1: User Chooses Payment Method**
- User selects: Online (GCash) or Face-to-Face

**5A.2: User Makes Payment**
**Condition to show "Pay Now" button:**
```python
can_pay = (
    rental.payment_type == 'cash' and
    rental.workflow_state == 'ready_for_payment'
)
```

**User clicks "Pay Now":**
- Submits payment proof
- workflow_state: `ready_for_payment` → `payment_submitted`

**5A.3: Admin Verifies Payment**
- Admin reviews payment proof
- Marks as verified
- workflow_state: `payment_submitted` → `payment_verified`

**5A.4: Operation Starts**
- Operator starts job
- workflow_state: `payment_verified` → `in_operation`

**5A.5: Operation Completes**
- Operator finishes job
- workflow_state: `in_operation` → `completed`

### Step 5B: In-Kind Rental Flow

**5B.1: Operation Ready**
- workflow_state: `ready_for_operation`
- No payment needed

**5B.2: Operation Starts**
- Operator starts job
- workflow_state: `ready_for_operation` → `in_operation`

**5B.3: Harvest Recorded**
- Farmer reports harvest
- workflow_state: `in_operation` → `harvest_recorded`

**5B.4: Rice Delivery**
- Farmer delivers rice share
- Admin confirms delivery
- workflow_state: `harvest_recorded` → `rice_delivery_confirmed`

**5B.5: Settlement Complete**
- workflow_state: `rice_delivery_confirmed` → `completed`

## Implementation Rules

### Rule 1: Operator Assignment Check
```python
def check_operator_assignment_complete(rental):
    """Check if all machines needing operators have them assigned"""
    if not rental.machine.requires_operator_service:
        return True
    return rental.assigned_operator_id is not None

def transition_after_operator_assignment(rental):
    """Transition to next state after operator assignment"""
    if check_operator_assignment_complete(rental):
        if rental.payment_type == 'cash':
            rental.workflow_state = 'ready_for_payment'
        else:
            rental.workflow_state = 'ready_for_operation'
        rental.save()
```

### Rule 2: Payment Button Visibility
```python
# In template
{% if rental.payment_type == 'cash' and rental.workflow_state == 'ready_for_payment' %}
    <a href="{% url 'create_rental_payment' rental.pk %}" class="btn btn-success">
        Pay Now
    </a>
{% endif %}
```

### Rule 3: Payment Validation
```python
# In payment view
def create_rental_payment(request, rental_id):
    rental = get_object_or_404(Rental, pk=rental_id)
    
    # Validate payment eligibility
    if rental.payment_type != 'cash':
        messages.error(request, 'This rental does not require cash payment.')
        return redirect('rental_detail', rental_id)
    
    if rental.workflow_state != 'ready_for_payment':
        messages.error(request, 'This rental is not yet ready for payment.')
        return redirect('rental_detail', rental_id)
    
    # Process payment...
```

### Rule 4: Workflow State Transitions
```python
def advance_rental_workflow(rental, new_state):
    """Advance rental to next workflow state with validation"""
    
    valid_transitions = {
        'pending': ['scheduled', 'cancelled'],
        'scheduled': ['approved', 'cancelled'],
        'approved': ['waiting_operator_assignment', 'cancelled'],
        'waiting_operator_assignment': ['ready_for_payment', 'ready_for_operation', 'cancelled'],
        'ready_for_payment': ['payment_submitted', 'cancelled'],
        'payment_submitted': ['payment_verified', 'ready_for_payment', 'cancelled'],
        'payment_verified': ['in_operation', 'cancelled'],
        'ready_for_operation': ['in_operation', 'cancelled'],
        'in_operation': ['harvest_recorded', 'completed', 'cancelled'],
        'harvest_recorded': ['rice_delivery_confirmed', 'cancelled'],
        'rice_delivery_confirmed': ['completed'],
        'completed': [],
        'cancelled': [],
    }
    
    current_state = rental.workflow_state
    
    if new_state not in valid_transitions.get(current_state, []):
        raise ValueError(f'Invalid transition from {current_state} to {new_state}')
    
    rental.workflow_state = new_state
    rental.save()
```

## Payment Dashboard Sections

### Section 1: Preparation
**Awaiting Operator Assignment**
- Shows rentals in `waiting_operator_assignment` state
- Admin can assign operators here

### Section 2: Payment (Cash Rentals Only)
**Ready for Payment**
- Shows rentals in `ready_for_payment` state
- User can choose payment method
- User can click "Pay Now" (if online)
- Admin can record face-to-face payment

**Payment Submitted**
- Shows rentals in `payment_submitted` state
- Admin can verify payment

**Payment Verified**
- Shows rentals in `payment_verified` state
- Ready to start operation

### Section 3: Operation
**Ready for Operation**
- Shows in-kind rentals ready to start
- Shows cash rentals after payment verified

**In Operation**
- Shows active operations
- Operator working on job

### Section 4: Settlement (In-Kind Only)
**Harvest Recorded**
- Shows rentals with harvest reported
- Awaiting rice delivery

**Rice Delivery Confirmed**
- Shows completed deliveries
- Settlement complete

### Section 5: Completed
**All Completed Services**
- Shows all finished rentals
- Historical record

## Key Benefits of This Flow

### ✅ Clear State Progression
- Each state has a clear purpose
- No ambiguity about what happens next

### ✅ Payment After Operator Assignment
- Cash rentals can be paid in advance
- No need to wait for operation day
- Better cash flow for organization

### ✅ Separate Cash and In-Kind Flows
- Cash: payment → operation
- In-kind: operation → harvest → delivery

### ✅ Simple Payment Rule
```python
can_pay = (
    payment_type == 'cash' and 
    workflow_state == 'ready_for_payment'
)
```

### ✅ Automatic Transitions
- Operator assignment triggers next state
- No manual state management needed

## Implementation Checklist

### Database Changes
- [ ] Add `workflow_state` field to Rental model
- [ ] Add `requires_operator_service` field to Machine model
- [ ] Create migration

### Model Methods
- [ ] `check_operator_assignment_complete()`
- [ ] `transition_after_operator_assignment()`
- [ ] `advance_rental_workflow()`
- [ ] `can_make_payment()` property

### View Updates
- [ ] Update operator assignment view to trigger state transition
- [ ] Add payment validation in payment view
- [ ] Update package detail view to use workflow states

### Template Updates
- [ ] Update payment button condition
- [ ] Reorganize payment dashboard by workflow state
- [ ] Add state indicators

### Testing
- [ ] Test complete cash flow
- [ ] Test complete in-kind flow
- [ ] Test operator assignment transitions
- [ ] Test payment validation
- [ ] Test state transition validation

## Summary

This clean workflow provides:
1. **Clear progression**: Each state leads logically to the next
2. **Early payment**: Cash rentals can be paid after operator assignment
3. **Separate flows**: Cash and in-kind have distinct paths
4. **Simple rules**: Payment eligibility is straightforward
5. **Automatic transitions**: System handles state changes

**Key Rule:** Payment becomes available immediately after operator assignment for cash rentals, not on operation day.

**Last Updated:** Current session
**Status:** Implementation Guide Ready
