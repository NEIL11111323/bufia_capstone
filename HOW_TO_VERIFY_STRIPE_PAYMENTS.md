# How to Verify Stripe Payments - Admin Guide

## Why Verification is Important

Before marking a rental as complete, you need to verify that:
1. ✅ Payment was actually received in Stripe
2. ✅ Amount matches what was expected
3. ✅ Payment was successful (not failed or refunded)
4. ✅ Payment date is correct

## Step-by-Step Verification Process

### Step 1: Check the Rental Approval Page

Go to: `http://127.0.0.1:8000/machines/admin/rental/62/approve/`

You'll see a section titled **"Online Payment Verification"** with:

```
┌─────────────────────────────────────────────────┐
│ 📋 Payment Details                              │
├─────────────────────────────────────────────────┤
│ Transaction ID:    BUFI-TXN-2026-00001          │
│ Payment Date:      Mar 13, 2026 05:58 AM        │
│ Amount:            PHP 7500.00                   │
│ Payment Status:    PAID                          │
│ Stripe Session:    cs_test_xxxxx...             │
└─────────────────────────────────────────────────┘
```

### Step 2: Open Stripe Dashboard

Click the button: **"View in Stripe Dashboard"**

This will open Stripe in a new tab with the payment already filtered.

**OR** manually go to:
- Test Mode: https://dashboard.stripe.com/test/payments
- Live Mode: https://dashboard.stripe.com/payments

### Step 3: Find the Payment in Stripe

**Option A: Use the Session ID**
- Copy the Stripe Session ID from the rental page
- Paste it in the Stripe search box
- Press Enter

**Option B: Search by Amount and Date**
- Filter by amount: PHP 7500.00 (or ₱75.00 in Stripe)
- Filter by date: Mar 13, 2026
- Look for matching payment

**Option C: Search by Customer Email**
- Search for the user's email (Joel Melendres' email)
- Find payments from that date

### Step 4: Verify Payment Details in Stripe

Check these details match:

| Field | Rental Page | Stripe Dashboard | Match? |
|-------|-------------|------------------|--------|
| Amount | PHP 7500.00 | ₱75.00 (7500 centavos) | ✅ |
| Date | Mar 13, 2026 05:58 AM | Mar 13, 2026 | ✅ |
| Status | PAID | Succeeded | ✅ |
| Session ID | cs_test_xxxxx | cs_test_xxxxx | ✅ |

### Step 5: Check Payment Status in Stripe

The payment should show:
- **Status**: `Succeeded` (green checkmark)
- **NOT**: `Failed`, `Canceled`, `Refunded`, or `Disputed`

### Step 6: Verify in BUFIA System

Once confirmed in Stripe, go back to the rental approval page and:

1. Click: **"Verify Payment & Complete Rental"**
2. Confirm the popup dialog
3. Done!

## What Each Payment Status Means

### In BUFIA System:

| Status | Meaning | Action Needed |
|--------|---------|---------------|
| **NOT PAID** | User hasn't paid yet | Wait for payment |
| **PENDING VERIFICATION** | Payment received, needs verification | Verify in Stripe |
| **VERIFIED** | Payment confirmed and verified | None - Complete! |

### In Stripe Dashboard:

| Status | Meaning | What to Do |
|--------|---------|------------|
| **Succeeded** | Payment successful | ✅ Verify in BUFIA |
| **Processing** | Payment being processed | ⏳ Wait a few minutes |
| **Requires Payment Method** | Card declined | ❌ Ask user to retry |
| **Canceled** | Payment canceled | ❌ Don't verify |
| **Failed** | Payment failed | ❌ Ask user to retry |
| **Refunded** | Money returned to user | ❌ Don't verify |

## Common Scenarios

### Scenario 1: Payment Shows in BUFIA but Not in Stripe

**Possible Causes**:
- Webhook delay (wait 1-2 minutes)
- Wrong Stripe account (check test vs live mode)
- Session ID mismatch

**Solution**:
1. Wait 2 minutes and refresh Stripe
2. Check if you're in correct mode (test/live)
3. Search by amount and date instead of session ID

### Scenario 2: Amount Doesn't Match

**Example**: BUFIA shows PHP 7500.00, Stripe shows ₱75.00

**Explanation**: Stripe stores amounts in centavos (smallest currency unit)
- PHP 7500.00 = 750000 centavos = ₱7500.00 in Stripe
- PHP 75.00 = 7500 centavos = ₱75.00 in Stripe

**Solution**: Divide Stripe amount by 100 to get PHP amount

### Scenario 3: Multiple Payments for Same Rental

**Possible Causes**:
- User clicked "Pay" multiple times
- Payment retry after failure

**Solution**:
1. Check which payment succeeded
2. Verify the latest successful payment
3. Refund duplicate payments if any

### Scenario 4: Payment Date Mismatch

**Example**: BUFIA shows Mar 13, Stripe shows Mar 12

**Explanation**: Timezone difference
- BUFIA uses Philippine Time (UTC+8)
- Stripe uses UTC

**Solution**: Check if times are within 24 hours - that's normal

## Security Checklist

Before verifying any payment, confirm:

- [ ] Payment status in Stripe is "Succeeded"
- [ ] Amount matches exactly (accounting for centavos)
- [ ] Payment date is recent (within expected timeframe)
- [ ] No refund or dispute flags
- [ ] Customer email matches the user
- [ ] Session ID matches (if available)

## Stripe Dashboard Quick Guide

### How to Access:
1. Go to https://dashboard.stripe.com
2. Login with Stripe credentials
3. Switch to Test Mode (toggle in top right) for testing
4. Click "Payments" in left sidebar

### How to Search:
- **By Session ID**: Paste `cs_test_xxxxx` in search box
- **By Amount**: Use filter "Amount" → Enter amount
- **By Date**: Use filter "Created" → Select date range
- **By Email**: Type customer email in search box

### What to Look For:
- Green checkmark = Successful payment
- Red X = Failed payment
- Yellow warning = Needs attention
- Blue info = Processing

## Troubleshooting

### Problem: Can't find payment in Stripe

**Solutions**:
1. Check you're in correct mode (Test vs Live)
2. Wait 2-3 minutes for webhook to process
3. Search by amount instead of session ID
4. Check Stripe logs for webhook errors
5. Verify Stripe API keys are correct in settings

### Problem: Payment shows "Failed" in Stripe

**Solutions**:
1. Don't verify in BUFIA
2. Contact user to retry payment
3. Check if card was declined
4. User needs to use different payment method

### Problem: Payment was refunded

**Solutions**:
1. Don't verify in BUFIA
2. Mark rental as cancelled
3. Contact user about refund reason
4. User needs to make new rental request

## Best Practices

1. **Always verify in Stripe first** before clicking "Verify Payment"
2. **Check amount carefully** - ensure it matches
3. **Look for green "Succeeded" status** in Stripe
4. **Keep records** - screenshot Stripe payment for records
5. **Verify quickly** - don't keep users waiting
6. **Double-check** - when in doubt, verify twice

## Quick Reference

### Payment is REAL if:
✅ Shows in Stripe Dashboard
✅ Status = "Succeeded"
✅ Amount matches
✅ Date is recent
✅ No refund/dispute flags
✅ Session ID matches

### Payment is FAKE/INVALID if:
❌ Not in Stripe Dashboard
❌ Status = "Failed" or "Canceled"
❌ Amount doesn't match
❌ Already refunded
❌ Disputed by customer
❌ Session ID doesn't exist

## Summary

**To verify if user really paid:**

1. Open rental approval page
2. Click "View in Stripe Dashboard"
3. Confirm payment shows as "Succeeded"
4. Verify amount matches
5. Check no refunds or disputes
6. Click "Verify Payment & Complete Rental" in BUFIA

**Time needed**: 1-2 minutes per payment

**Confidence level**: 100% - Stripe is the source of truth!
