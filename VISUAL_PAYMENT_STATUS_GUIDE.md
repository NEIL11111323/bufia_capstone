# Visual Payment Status Guide for Admins

## What You'll See on the Rental Approval Page

### Scenario 1: Payment Received - Needs Verification ⚠️

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Payment Received - Verification Needed                   │
│                                                              │
│ Online payment was received on Mar 13, 2026 05:58 AM.       │
│ Please verify and complete the rental below.                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📋 Payment Details                                          │
├─────────────────────────────────────────────────────────────┤
│ Transaction ID:    BUFI-TXN-2026-00001                      │
│ Payment Date:      Mar 13, 2026 05:58 AM                    │
│ Amount:            PHP 7,500.00                              │
│ Payment Status:    PAID                                      │
│ Stripe Session:    cs_test_xxxxx...                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🛡️ How to Verify Payment:                                   │
│ 1. Check Stripe Dashboard to confirm payment                │
│ 2. Verify amount matches: PHP 7,500.00                      │
│ 3. Check payment date: Mar 13, 2026                         │
│ 4. Click button below to mark as verified                   │
└─────────────────────────────────────────────────────────────┘

[View in Stripe Dashboard] ← Click this first!

[Verify Payment & Complete Rental] ← Then click this!
```

### Scenario 2: Payment Already Verified ✅

```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Payment Verified                                          │
│                                                              │
│ Payment verified on Mar 13, 2026 06:15 AM                   │
└─────────────────────────────────────────────────────────────┘
```

### Scenario 3: Waiting for Payment ⏳

```
┌─────────────────────────────────────────────────────────────┐
│ ⏳ Waiting for Payment                                       │
│                                                              │
│ User has not completed online payment yet.                  │
└─────────────────────────────────────────────────────────────┘
```

## Payment Status Row (Always Visible)

The payment status row has a colored background:

### Pending Verification (Yellow Background)
```
┌─────────────────────────────────────────────────────────────┐
│ Payment Status: [⏳ PENDING VERIFICATION]                   │
│                 Received: Mar 13, 2026 05:58 AM             │
└─────────────────────────────────────────────────────────────┘
```

### Verified (Green Background)
```
┌─────────────────────────────────────────────────────────────┐
│ Payment Status: [✅ VERIFIED]                                │
│                 Verified: Mar 13, 2026 06:15 AM             │
└─────────────────────────────────────────────────────────────┘
```

### Not Paid (Gray Background)
```
┌─────────────────────────────────────────────────────────────┐
│ Payment Status: [⏳ NOT PAID]                                │
└─────────────────────────────────────────────────────────────┘
```

## Quick Action Guide

### When You See Yellow Alert:
1. ✅ Payment was received
2. ⚠️ Needs your verification
3. 👉 Click "View in Stripe Dashboard"
4. 👉 Verify payment succeeded
5. 👉 Click "Verify Payment & Complete Rental"

### When You See Green Alert:
1. ✅ Payment already verified
2. ✅ Rental completed
3. ✅ No action needed

### When You See Blue Alert:
1. ⏳ User hasn't paid yet
2. ⏳ Wait for payment
3. ⏳ No action needed yet

## Color Legend

| Color | Meaning | Action Required |
|-------|---------|-----------------|
| 🟡 Yellow | Payment received, needs verification | YES - Verify now |
| 🟢 Green | Payment verified and completed | NO - Already done |
| 🔵 Blue | Waiting for user to pay | NO - Just wait |
| 🔴 Red | Error or issue | YES - Investigate |

