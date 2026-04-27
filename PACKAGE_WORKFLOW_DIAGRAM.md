# Package Rental Workflow - Visual Diagram

## Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PACKAGE RENTAL WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 1: PACKAGE CREATION (Member)                                   │
└──────────────────────────────────────────────────────────────────────┘

    [Member]
       ↓
    Create Package Request
    - Select services
    - Farm details
    - Preferred dates
    - Payment preference
       ↓
    ┌─────────────────────┐
    │ Package: PENDING    │
    │ Items: REQUESTED    │
    │ Rentals: None       │
    └─────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 2: ADMIN SCHEDULING                                            │
└──────────────────────────────────────────────────────────────────────┘

    [Admin Opens Package]
       ↓
    For Each Service:
    ┌─────────────────────────────┐
    │ 1. Select Machine           │
    │ 2. Set Quantity             │
    │ 3. Set Start/End Dates      │
    │ 4. Mark Tentative/Confirmed │
    │ 5. Add Notes                │
    └─────────────────────────────┘
       ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Admin Actions:                                          │
    │                                                         │
    │ [Save Draft]  → Saves without creating rentals         │
    │                                                         │
    │ [Confirm Schedule] → Confirms ONE service              │
    │     ↓                                                   │
    │     Item: REQUESTED → SCHEDULED                        │
    │     Creates Rental Record                              │
    │     Updates Machine Calendar                           │
    │                                                         │
    │ [Pre-Approve] → Approves confirmed items               │
    │     ↓                                                   │
    │     Package: PARTIALLY_SCHEDULED                       │
    │     Creates rentals for confirmed items                │
    │     Leaves others as REQUESTED                         │
    │                                                         │
    │ [Approve Package] → Full approval                      │
    │     ↓                                                   │
    │     Validates all items confirmed                      │
    │     Package: APPROVED                                  │
    │     All rentals created                                │
    └─────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 3: RENTAL CREATION                                             │
└──────────────────────────────────────────────────────────────────────┘

    When Schedule Confirmed:
       ↓
    ┌─────────────────────────────────────┐
    │ Create Rental Record:               │
    │                                     │
    │ • Machine: [selected]               │
    │ • User: [package requester]         │
    │ • Dates: [scheduled dates]          │
    │ • Status: APPROVED                  │
    │ • Workflow: APPROVED                │
    │ • Operator: UNASSIGNED              │
    │ • Payment Type: [from machine]      │
    │ • Payment Method: [from package]    │
    │ • Purpose: "Package: [name]..."     │
    └─────────────────────────────────────┘
       ↓
    Link Rental to Package Item
       ↓
    Update Machine Calendar
       ↓
    Create Payment Record (if cash)

┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 4: PAYMENT PROCESSING                                          │
└──────────────────────────────────────────────────────────────────────┘

    Package Approved
       ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Payment Dashboard Shows:                                │
    │                                                         │
    │ ┌─────────────────────┐  ┌──────────────────────────┐ │
    │ │ CASH SERVICES       │  │ RICE-SHARE SERVICES      │ │
    │ │                     │  │                          │ │
    │ │ Ready to Pay        │  │ Awaiting Harvest         │ │
    │ │   ↓                 │  │   ↓                      │ │
    │ │ [Pay Now]           │  │ Harvest Recorded         │ │
    │ │   ↓                 │  │   ↓                      │ │
    │ │ Submit Proof        │  │ Delivery Pending         │ │
    │ │   ↓                 │  │   ↓                      │ │
    │ │ Awaiting Verification│ │ Delivery Confirmed       │ │
    │ │   ↓                 │  │   ↓                      │ │
    │ │ PAID                │  │ SETTLED                  │ │
    │ └─────────────────────┘  └──────────────────────────┘ │
    └─────────────────────────────────────────────────────────┘
       ↓
    All Services Paid/Settled
       ↓
    Package Payment Status: PAID

┌──────────────────────────────────────────────────────────────────────┐
│ PHASE 5: SERVICE EXECUTION                                           │
└──────────────────────────────────────────────────────────────────────┘

    Rental: APPROVED
       ↓
    Operator Assigned
       ↓
    Rental Operator Status: ASSIGNED
       ↓
    Operator Starts Job
       ↓
    ┌─────────────────────────────┐
    │ Rental: IN_PROGRESS         │
    │ Item: IN_PROGRESS           │
    │ Package: IN_PROGRESS        │
    └─────────────────────────────┘
       ↓
    Operator Completes Job
       ↓
    ┌─────────────────────────────┐
    │ Rental: COMPLETED           │
    │ Item: COMPLETED             │
    └─────────────────────────────┘
       ↓
    All Items Completed?
       ↓
    YES → Package: COMPLETED

┌──────────────────────────────────────────────────────────────────────┐
│ CANCELLATION WORKFLOW                                                │
└──────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────┐         ┌─────────────────────┐
    │ MEMBER CANCELLATION │         │ ADMIN REJECTION     │
    └─────────────────────┘         └─────────────────────┘
            ↓                               ↓
    Check Conditions:               Check Conditions:
    • Is requester?                 • Is admin?
    • No in-progress services?      • No in-progress services?
    • No completed services?        • No completed services?
            ↓                               ↓
    [Cancel Package] Button         [Reject Package] Button
            ↓                               ↓
    Confirmation Modal              Confirmation Modal
            ↓                               ↓
    ┌─────────────────────────────────────────────────────┐
    │ Cancellation Process:                               │
    │                                                     │
    │ 1. Cancel all linked rentals                        │
    │    • Rental status: CANCELLED                       │
    │    • Rental workflow: CANCELLED                     │
    │    • Operator status: UNASSIGNED                    │
    │                                                     │
    │ 2. Update all package items                         │
    │    • Item status: CANCELLED                         │
    │    • Clear machine assignment                       │
    │    • Clear schedule dates                           │
    │    • Clear rental link                              │
    │    • Add cancellation note                          │
    │                                                     │
    │ 3. Update package                                   │
    │    • Package status: CANCELLED                      │
    │    • Set approver (if admin)                        │
    │    • Set approval timestamp                         │
    │                                                     │
    │ 4. Update machine calendars                         │
    │    • Release reserved dates                         │
    │    • Sync machine status                            │
    │                                                     │
    │ 5. Refresh totals                                   │
    │    • Recalculate total amount                       │
    │    • Update payment status                          │
    └─────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ STATUS TRANSITION DIAGRAM                                            │
└──────────────────────────────────────────────────────────────────────┘

PACKAGE ITEM STATUS:
┌───────────┐
│ REQUESTED │ ← Initial state
└─────┬─────┘
      ↓ (Admin sets schedule)
┌───────────┐
│ TENTATIVE │ ← Schedule set but not confirmed
└─────┬─────┘
      ↓ (Admin confirms)
┌───────────┐
│ SCHEDULED │ ← Rental created, calendar reserved
└─────┬─────┘
      ↓ (Operator starts)
┌─────────────┐
│ IN_PROGRESS │ ← Service being executed
└──────┬──────┘
       ↓ (Operator completes)
┌───────────┐
│ COMPLETED │ ← Service finished
└───────────┘

Any state can transition to:
┌───────────┐
│ CANCELLED │ ← Package cancelled/rejected
└───────────┘

PACKAGE STATUS:
┌─────────┐
│ PENDING │ ← Initial state
└────┬────┘
     ↓ (Some items scheduled)
┌──────────────────────┐
│ PARTIALLY_SCHEDULED  │ ← Some confirmed, others pending
└──────────┬───────────┘
           ↓ (All items scheduled)
┌──────────┐
│ APPROVED │ ← All services scheduled
└────┬─────┘
     ↓ (Any service starts)
┌─────────────┐
│ IN_PROGRESS │ ← At least one service active
└──────┬──────┘
       ↓ (All services complete)
┌───────────┐
│ COMPLETED │ ← All services finished
└───────────┘

Any state can transition to:
┌───────────┐
│ CANCELLED │ ← Package cancelled/rejected
└───────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PAYMENT STATUS FLOW                                                  │
└──────────────────────────────────────────────────────────────────────┘

Package Payment Status:
┌─────────────────┐
│ NOT_REQUIRED    │ ← No services scheduled yet
└────────┬────────┘
         ↓ (Services scheduled)
┌─────────────────┐
│ PENDING         │ ← Services scheduled, no payments
└────────┬────────┘
         ↓ (Some payments received)
┌─────────────────┐
│ PARTIALLY_PAID  │ ← Some services paid
└────────┬────────┘
         ↓ (All payments received)
┌─────────────────┐
│ PAID            │ ← All services paid/settled
└─────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ KEY DECISION POINTS                                                  │
└──────────────────────────────────────────────────────────────────────┘

1. SCHEDULE CONFIRMATION
   ┌─────────────────────────────────────┐
   │ Has machine?                        │
   │ Has start/end dates?                │
   │ Not marked tentative?               │
   │ Status is scheduled/in_progress?    │
   └─────────────────────────────────────┘
          ↓ YES                ↓ NO
   Create Rental         Cannot Confirm

2. PACKAGE APPROVAL
   ┌─────────────────────────────────────┐
   │ All items have confirmed schedules? │
   └─────────────────────────────────────┘
          ↓ YES                ↓ NO
   Full Approval        Use Pre-Approve

3. CANCELLATION ALLOWED
   ┌─────────────────────────────────────┐
   │ Any service in_progress?            │
   │ Any service completed?              │
   └─────────────────────────────────────┘
          ↓ YES                ↓ NO
   Cannot Cancel        Can Cancel

┌──────────────────────────────────────────────────────────────────────┐
│ SUMMARY                                                              │
└──────────────────────────────────────────────────────────────────────┘

The package rental workflow provides:

✅ Flexible scheduling - Schedule services individually
✅ Partial approval - Approve confirmed items, schedule others later
✅ Automatic rental creation - Rentals created when confirmed
✅ Payment tracking - Per-service payment monitoring
✅ Status visibility - Clear state indicators
✅ Safe cancellation - Prevents cancellation of active work

**Workflow is complete and functional - no fixes needed!**
