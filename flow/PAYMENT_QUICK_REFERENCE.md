# Payment Quick Reference

## Test Card (Use This!)
```
Card Number: 4242 4242 4242 4242
Expiry: 12/25
CVC: 123
ZIP: 12345
```

## Payment Flow
1. User submits request → Redirects to Stripe
2. User pays → Redirects back to site
3. Request auto-approved → User notified

## URLs
- Rental: `/payment/rental/<id>/`
- Appointment: `/payment/appointment/<id>/`
- Irrigation: `/payment/irrigation/<id>/`

## Payment Amounts
- **Rentals**: Machine price × Days
- **Appointments**: Rice quantity (kg) × $0.15
- **Irrigation**: Area (ha) × Hours × $10

## Stripe Keys (Test Mode)
```python
# In bufia/settings.py
STRIPE_PUBLIC_KEY = 'pk_test_51SXhx2Aque0gnK4A...'
STRIPE_SECRET_KEY = 'sk_test_51SXhx2Aque0gnK4A...'
```

## Quick Test
1. Create rental/appointment/irrigation
2. Use test card above
3. Complete payment
4. Check: Status = Approved ✅
5. Check: Notification received ✅

## Files Modified
- `bufia/settings.py` - Added Stripe keys
- `bufia/urls.py` - Added payment routes
- `bufia/views/payment_views.py` - Payment logic (NEW)
- `machines/views.py` - Redirect to payment
- `irrigation/views.py` - Redirect to payment

## Troubleshooting
- **Error creating session**: Check Stripe keys
- **Not approved after payment**: Check Django logs
- **Redirect loop**: Clear browser cache

## View Payments
Stripe Dashboard: https://dashboard.stripe.com/test/payments

## Documentation
- `STRIPE_PAYMENT_GUIDE.md` - Full guide
- `PAYMENT_TESTING_GUIDE.md` - Testing steps
- `PAYMENT_IMPLEMENTATION_SUMMARY.md` - Technical details
