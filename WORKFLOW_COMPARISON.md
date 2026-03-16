# Transaction Workflow Comparison: All Payment Types

## Quick Reference

| Payment Type | Who Submits Harvest? | Who Records Payment? | Automatic Completion? |
|--------------|---------------------|---------------------|----------------------|
| **IN-KIND** | Operator OR Admin | Admin (rice delivery) | ✅ Yes (when rice delivered = required) |
| **Online** | N/A | System (Stripe) | ✅ Yes (after admin verification) |
| **Face-to-Face** | N/A | Admin (at office) | ✅ Yes (after admin records payment) |

---

## IN-KIND Payment Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    IN-KIND PAYMENT WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. MEMBER SUBMITS REQUEST
   └─> Member fills rental form
       └─> Selects IN-KIND payment
           └─> Status: PENDING

2. ADMIN APPROVES
   └─> Admin reviews request
       └─> Clicks "Approve"
           └─> Status: APPROVED
           └─> Settlement Status: PENDING

3. ADMIN ASSIGNS OPERATOR (Optional)
   └─> Admin assigns operator to job
       └─> Operator receives notification

4. ADMIN STARTS OPERATION
   └─> Admin clicks "Start Equipment Operation"
       └─> Workflow State: IN PROGRESS
       └─> Machine Status: RENTED

5. HARVEST REPORTING (Two Options)
   
   ┌─────────────────────────────────────────────────────────────┐
   │ OPTION A: OPERATOR SUBMITS DIRECTLY (Recommended)          │
   └─────────────────────────────────────────────────────────────┘
   └─> Operator logs into Operator Dashboard
       └─> Finds assigned job
           └─> Enters total harvest (e.g., 21.3 sacks)
               └─> Adds harvest notes
                   └─> Clicks "Submit Harvest Report"
                       └─> System calculates:
                           • BUFIA Share: 2.37 sacks
                           • Member Share: 18.93 sacks
                       └─> Workflow State: HARVEST REPORT SUBMITTED
                       └─> Settlement Status: WAITING FOR DELIVERY
                       └─> Admins notified

   ┌─────────────────────────────────────────────────────────────┐
   │ OPTION B: ADMIN ENTERS MANUALLY                             │
   └─────────────────────────────────────────────────────────────┘
   └─> Operator reports via Facebook/phone
       └─> Admin logs into Admin Dashboard
           └─> Opens rental approval page
               └─> Clicks "Submit Harvest Report"
                   └─> Enters harvest data
                       └─> Same calculation and updates as Option A

6. RICE DELIVERY
   └─> Member delivers rice to BUFIA office
       └─> Admin confirms delivery
           └─> Enters rice received (e.g., 2.37 sacks)
               └─> Clicks "Confirm Rice Received"

7. AUTOMATIC COMPLETION ✅
   └─> System checks: rice_received == bufia_share_required?
       └─> YES: Automatically completes rental
           • Status: COMPLETED
           • Settlement Status: PAID
           • Machine Status: AVAILABLE
           • Member notified
           • Admin sees success message
       └─> NO: Shows error, admin must verify amount
```

---

## Online Payment Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                   ONLINE PAYMENT WORKFLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. MEMBER SUBMITS REQUEST
   └─> Member fills rental form
       └─> Selects Online payment
           └─> Status: PENDING

2. ADMIN APPROVES
   └─> Admin reviews request
       └─> Clicks "Approve"
           └─> Status: APPROVED
           └─> Payment Status: PENDING

3. MEMBER PAYS ONLINE
   └─> Member clicks "Pay Now"
       └─> Redirected to Stripe checkout
           └─> Completes payment
               └─> Payment record created
               └─> Transaction ID generated
               └─> Payment Status: PAID
               └─> Admin notified

4. ADMIN VERIFIES PAYMENT
   └─> Admin views payment in dashboard
       └─> Clicks "Verify Online Payment"

5. AUTOMATIC COMPLETION ✅
   └─> System automatically:
       • Status: COMPLETED
       • Payment Verified: TRUE
       • Machine Status: AVAILABLE
       • Member notified
```

---

## Face-to-Face Payment Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                FACE-TO-FACE PAYMENT WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

1. MEMBER SUBMITS REQUEST
   └─> Member fills rental form
       └─> Selects Face-to-Face payment
           └─> Status: PENDING

2. ADMIN APPROVES
   └─> Admin reviews request
       └─> Clicks "Approve"
           └─> Status: APPROVED
           └─> Payment Status: PENDING

3. MEMBER PAYS AT OFFICE
   └─> Member visits BUFIA office
       └─> Pays cash/check
           └─> Receives receipt

4. ADMIN RECORDS PAYMENT
   └─> Admin opens rental approval page
       └─> Clicks "Record Face-to-Face Payment"
           └─> Enters:
               • Payment Amount
               • Payment Date
               • Receipt Number

5. AUTOMATIC COMPLETION ✅
   └─> System automatically:
       • Status: COMPLETED
       • Payment Status: PAID
       • Payment Verified: TRUE
       • Machine Status: AVAILABLE
       • Payment record created
       • Transaction ID generated
       • Member notified
```

---

## Role Responsibilities

### Member/User
| Action | IN-KIND | Online | Face-to-Face |
|--------|---------|--------|--------------|
| Submit rental request | ✅ | ✅ | ✅ |
| Make payment | Deliver rice | Pay via Stripe | Pay at office |
| Receive notifications | ✅ | ✅ | ✅ |
| View rental status | ✅ | ✅ | ✅ |

### Operator
| Action | IN-KIND | Online | Face-to-Face |
|--------|---------|--------|--------------|
| View assigned jobs | ✅ | ❌ | ❌ |
| Update job status | ✅ | ❌ | ❌ |
| Submit harvest report | ✅ | ❌ | ❌ |
| Operate equipment | ✅ | ❌ | ❌ |

### Admin
| Action | IN-KIND | Online | Face-to-Face |
|--------|---------|--------|--------------|
| Approve/reject requests | ✅ | ✅ | ✅ |
| Assign operator | ✅ | ❌ | ❌ |
| Start operation | ✅ | ❌ | ❌ |
| Submit harvest (if needed) | ✅ | ❌ | ❌ |
| Confirm rice delivery | ✅ | ❌ | ❌ |
| Verify payment | ❌ | ✅ | ❌ |
| Record payment | ❌ | ❌ | ✅ |

---

## Dashboard Views

### Admin Dashboard Panels

1. **Pending Rental Requests**
   - All payment types
   - Status: PENDING
   - Action: Approve/Reject

2. **Approved Rentals**
   - All payment types
   - Status: APPROVED
   - Waiting for payment or operation start

3. **Rentals In Progress**
   - IN-KIND only
   - Workflow State: IN PROGRESS
   - Equipment being operated

4. **Harvest Settlements**
   - IN-KIND only
   - Workflow State: HARVEST REPORT SUBMITTED
   - Waiting for rice delivery

5. **Completed Rentals**
   - All payment types
   - Status: COMPLETED
   - Historical records

### Operator Dashboard

Shows only:
- Assigned IN-KIND rentals
- Job status updates
- Harvest submission forms
- Statistics (assigned, today, in progress, awaiting harvest, reported)

### Member Dashboard

Shows only:
- Own rental requests
- Payment status
- Rental history
- Notifications

---

## Key Differences

### IN-KIND vs Cash Payments

| Feature | IN-KIND | Online/Face-to-Face |
|---------|---------|---------------------|
| **Payment timing** | After harvest | Before/during rental |
| **Operator involvement** | Required | Not required |
| **Harvest reporting** | Required | Not applicable |
| **Settlement** | After rice delivery | Immediate after payment |
| **Calculation** | Automatic share calculation | Fixed amount |
| **Completion trigger** | Rice delivery = required share | Payment verification |

### Operator Submission vs Admin Entry

| Aspect | Operator Submits | Admin Enters |
|--------|------------------|--------------|
| **Speed** | Immediate | Delayed (waiting for communication) |
| **Accuracy** | Direct from field | Relayed information |
| **Communication** | System only | Facebook/phone + system |
| **Audit trail** | Complete | Complete |
| **Preferred** | ✅ Yes | Only if operator unavailable |

---

## Automatic Completion Logic

### IN-KIND
```python
if organization_share_received == organization_share_required:
    # Within 0.01 tolerance
    rental.status = 'completed'
    rental.settlement_status = 'paid'
    machine.status = 'available'
```

### Online
```python
if payment_verified and payment_status == 'paid':
    rental.status = 'completed'
    machine.status = 'available'
```

### Face-to-Face
```python
if payment_amount > 0 and receipt_number:
    rental.status = 'completed'
    rental.payment_status = 'paid'
    machine.status = 'available'
```

---

## Success Messages

### IN-KIND (Automatic Completion)
```
✅ Rice delivery confirmed (2.37 sacks). 
Settlement marked as PAID (IN-KIND). 
Rental automatically completed. 
Machine [name] is now available.
```

### Online (After Verification)
```
✅ Online payment verified. 
Rental marked as completed.
```

### Face-to-Face (After Recording)
```
✅ Face-to-face payment recorded. 
Rental marked as completed.
```

---

## URLs Reference

### Admin URLs
- Dashboard: `/machines/admin/dashboard/`
- Approve rental: `/machines/admin/rental/<id>/approve/`
- Start operation: `/machines/admin/rental/<id>/start-operation/`
- Submit harvest: `/machines/admin/rental/<id>/harvest-report/`
- Confirm rice: `/machines/admin/rental/<id>/confirm-rice-received/`
- Verify online: `/machines/admin/rental/<id>/verify-online-payment/`
- Record F2F: `/machines/admin/rental/<id>/record-face-to-face-payment/`

### Operator URLs
- Dashboard: `/machines/operator/dashboard/`
- Update job: `/machines/operator/rental/<id>/update/`
- Submit harvest: `/machines/operator/rental/<id>/harvest/`

### Member URLs
- Rental list: `/machines/rentals/`
- Rental detail: `/machines/rentals/<id>/`
- Create rental: `/machines/rentals/create/`
- Pay online: `/payment/rental/<id>/`
