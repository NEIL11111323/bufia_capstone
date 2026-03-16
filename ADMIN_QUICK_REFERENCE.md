# Admin Quick Reference - Payment Verification

## 🚀 Quick Start

### When You See a Payment Notification

1. **Go to**: Admin Dashboard → Equipment Rentals
2. **Click**: "In Progress" tab
3. **Find**: Rental with yellow "⚠️ Payment Received" alert
4. **Click**: "View Details" or rental ID

### On the Rental Approval Page

Look for the **yellow alert box** at the top:
```
⚠️ Payment Received - Verification Needed
Online payment was received on [date].
Please verify and complete the rental below.
```

## ✅ 3-Step Verification Process

### Step 1: Check Payment Details (5 seconds)
Scroll to "Online Payment Verification" section and verify:
- ✅ Transaction ID exists
- ✅ Payment Date is recent
- ✅ Amount matches expected price
- ✅ Status shows "PENDING VERIFICATION"

### Step 2: Verify in Stripe (30 seconds)
1. Click **"View in Stripe Dashboard"** button
2. Confirm payment shows **"Succeeded"** (green checkmark)
3. Verify amount matches
4. Check no refunds or disputes

### Step 3: Complete in BUFIA (5 seconds)
1. Return to BUFIA rental page
2. Click **"Verify Payment & Complete Rental"**
3. Confirm the dialog
4. Done! ✅

**Total Time**: ~40 seconds per rental

## 📊 Payment Status Guide

| What You See | What It Means | What To Do |
|--------------|---------------|------------|
| 🟡 **PENDING VERIFICATION** | Payment received, needs your verification | Verify in Stripe, then complete |
| 🟢 **VERIFIED** | Already verified and completed | Nothing - already done! |
| ⚪ **NOT PAID** | User hasn't paid yet | Wait for payment |

## 🔍 How to Know Payment is Real

### In BUFIA System:
- ✅ Transaction ID exists (BUFI-TXN-2026-XXXXX)
- ✅ Payment Date is filled
- ✅ Stripe Session ID exists (cs_test_xxxxx)
- ✅ Amount matches machine price

### In Stripe Dashboard:
- ✅ Payment status = **"Succeeded"** (green)
- ✅ Amount matches (remember: divide by 100 for PHP)
- ✅ No refund or dispute flags
- ✅ Customer email matches user

## ⚠️ Red Flags - DO NOT Verify If:

- ❌ Payment shows "Failed" in Stripe
- ❌ Payment shows "Refunded" in Stripe
- ❌ Amount doesn't match
- ❌ Payment is disputed
- ❌ Can't find payment in Stripe at all

**Action**: Contact user to retry payment

## 🔗 Quick Links

### Stripe Dashboard
- **Test Mode**: https://dashboard.stripe.com/test/payments
- **Live Mode**: https://dashboard.stripe.com/payments

### BUFIA Pages
- **Admin Dashboard**: `/machines/admin/rentals/`
- **Rental Approval**: `/machines/admin/rental/{id}/approve/`
- **Payment List**: `/admin/payments/`

## 💡 Pro Tips

1. **Verify Quickly**: Don't keep users waiting
2. **Check Stripe First**: Always verify in Stripe before clicking "Verify Payment"
3. **Look for Green**: Only "Succeeded" status in Stripe is valid
4. **Match Amounts**: PHP 7500.00 in BUFIA = ₱7500.00 in Stripe
5. **Keep Records**: Screenshot Stripe payment for your records

## 🆘 Common Issues

### "Can't find payment in Stripe"
- Wait 2 minutes and refresh
- Check you're in correct mode (Test vs Live)
- Search by amount instead of session ID

### "Amount doesn't match"
- Stripe shows in centavos (divide by 100)
- PHP 7500.00 = 750000 centavos = ₱7500.00

### "Multiple payments for same rental"
- User clicked "Pay" multiple times
- Verify the latest successful one
- Refund duplicates if needed

## 📱 Mobile Quick Guide

If checking on mobile:
1. Open rental in BUFIA
2. Note the Stripe Session ID
3. Open Stripe app
4. Search for session ID
5. Verify status = "Succeeded"
6. Return to BUFIA and complete

## 🎯 Success Checklist

Before clicking "Verify Payment":
- [ ] Checked payment in Stripe Dashboard
- [ ] Status shows "Succeeded" (green)
- [ ] Amount matches exactly
- [ ] No refund or dispute flags
- [ ] Payment date is recent
- [ ] Customer email matches user

## 📞 Need Help?

**Can't verify payment?**
- Check Stripe webhook logs
- Verify API keys are correct
- Contact technical support

**Payment looks suspicious?**
- Don't verify
- Contact user for clarification
- Check Stripe for fraud indicators

## 🎓 Remember

**The Golden Rule**: 
> If you can't find the payment in Stripe with "Succeeded" status, DON'T verify it in BUFIA!

**Stripe is the source of truth** - always verify there first!

---

## Quick Command Reference

### Check System Status
```bash
python manage.py check
```

### View Recent Payments
```bash
python manage.py shell
>>> from machines.models import Rental
>>> Rental.objects.filter(payment_date__isnull=False).order_by('-payment_date')[:5]
```

### Check Webhook Status
```bash
# Check Stripe webhook logs
# Go to: https://dashboard.stripe.com/test/webhooks
```

---

**Last Updated**: March 2026
**Version**: 1.0
**Status**: Production Ready ✅
