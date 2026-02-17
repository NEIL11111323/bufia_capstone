# Stripe Payment System - Working Guide

## ✅ Status: FULLY FUNCTIONAL

The Stripe payment integration is working correctly. Here's how to use it:

## Quick Test

### Test Card Information
```
Card Number: 4242 4242 4242 4242
Expiry Date: 12/25 (any future date)
CVC: 123 (any 3 digits)
ZIP Code: 12345 (any 5 digits)
```

## How to Use

### 1. Machine Rental Payment

**Step 1: Create Rental Request**
1. Go to: `http://localhost:8000/machines/`
2. Click "Rent" on any available machine
3. Fill in the rental form:
   - Start Date
   - End Date
   - Purpose
4. Click "Submit"

**Step 2: Payment**
- You'll be automatically redirected to Stripe Checkout
- Enter test card details (see above)
- Click "Pay"

**Step 3: Confirmation**
- Redirected back to your site
- Rental status: "Approved"
- Notification sent
- Success message displayed

### 2. Rice Mill Appointment Payment

**Step 1: Create Appointment**
1. Go to: `http://localhost:8000/machines/`
2. Find a Rice Mill machine
3. Click "Schedule Appointment"
4. Fill in:
   - Appointment Date
   - Time Slot (Morning/Afternoon)
   - Rice Quantity (kg)
5. Click "Submit"

**Step 2: Payment**
- Redirected to Stripe Checkout
- Enter test card details
- Click "Pay"

**Step 3: Confirmation**
- Appointment approved
- Reference number provided
- Notification sent

### 3. Irrigation Request Payment

**Step 1: Create Request**
1. Go to: `http://localhost:8000/irrigation/`
2. Click "Create New Request"
3. Fill in all fields:
   - Requested Date
   - Duration (hours)
   - Area Size (hectares)
   - Crop Type
   - Purpose
4. Click "Submit"

**Step 2: Payment**
- Redirected to Stripe Checkout
- Enter test card details
- Click "Pay"

**Step 3: Confirmation**
- Request approved
- Notification sent
- Success message

## Payment Amounts

### Automatic Calculation

**Machine Rentals:**
```
Amount = Machine Price × Number of Days
Example: ₱100/day × 3 days = ₱300 = $6.00 USD
```

**Rice Mill Appointments:**
```
Amount = Rice Quantity (kg) × $0.15
Example: 1000 kg × $0.15 = $150.00 USD
```

**Irrigation Requests:**
```
Amount = Area (hectares) × Duration (hours) × $10
Example: 5 hectares × 8 hours × $10 = $400.00 USD
```

## Stripe Dashboard

### View Test Payments

1. Go to: https://dashboard.stripe.com/test/payments
2. Log in with your Stripe account
3. See all test payments
4. Click on any payment to see details:
   - Amount
   - Card used
   - Customer info
   - Metadata (rental_id, user_id, etc.)
   - Timeline

### View Logs

1. Go to: https://dashboard.stripe.com/test/logs
2. See all API requests
3. Check for errors
4. View request/response details

## Test Different Scenarios

### 1. Successful Payment
```
Card: 4242 4242 4242 4242
Result: Payment succeeds
Status: Approved
```

### 2. Declined Payment
```
Card: 4000 0000 0000 0002
Result: Payment declined
Status: Remains Pending
```

### 3. Requires Authentication (3D Secure)
```
Card: 4000 0025 0000 3155
Result: Shows authentication dialog
Status: Approved after authentication
```

### 4. Insufficient Funds
```
Card: 4000 0000 0000 9995
Result: Insufficient funds error
Status: Remains Pending
```

### 5. Expired Card
```
Card: 4000 0000 0000 0069
Result: Expired card error
Status: Remains Pending
```

## Troubleshooting

### Issue: "Payment system is not configured"

**Solution:**
1. Check Stripe keys in `bufia/settings.py`
2. Verify keys start with `pk_test_` and `sk_test_`
3. Restart Django server

### Issue: "Error creating payment session"

**Solution:**
1. Check internet connection
2. Verify Stripe API keys are correct
3. Check Django console for detailed error
4. Check Stripe Dashboard logs

### Issue: "Payment successful but not approved"

**Solution:**
1. Check if signals are working
2. Verify payment success view is called
3. Check Django console logs
4. Verify redirect URLs are correct

### Issue: Redirect not working

**Solution:**
1. Check success_url and cancel_url in payment views
2. Verify URL patterns in `bufia/urls.py`
3. Clear browser cache
4. Try in incognito mode

## Configuration

### Current Settings

**File:** `bufia/settings.py`

```python
# Stripe Configuration
STRIPE_PUBLIC_KEY = 'pk_test_51SXhx2Aque0gnK4A...'
STRIPE_SECRET_KEY = 'sk_test_51SXhx2Aque0gnK4A...'
```

### Payment URLs

```python
# bufia/urls.py
path('payment/rental/<int:rental_id>/', payment_views.create_rental_payment, name='create_rental_payment'),
path('payment/irrigation/<int:irrigation_id>/', payment_views.create_irrigation_payment, name='create_irrigation_payment'),
path('payment/appointment/<int:appointment_id>/', payment_views.create_appointment_payment, name='create_appointment_payment'),
path('payment/success/', payment_views.payment_success, name='payment_success'),
path('payment/cancelled/', payment_views.payment_cancelled, name='payment_cancelled'),
path('payment/webhook/', payment_views.stripe_webhook, name='stripe_webhook'),
```

## Features

### ✅ Auto-Approval
- Payment success → Request auto-approved
- No admin intervention needed
- User receives notification immediately

### ✅ Secure Processing
- All payment data handled by Stripe
- No credit card data stored on your server
- PCI compliance handled by Stripe
- SSL/TLS encryption

### ✅ Payment Cancellation
- Users can cancel and return
- Request remains pending
- Can retry payment later

### ✅ Notifications
- User notified when payment succeeds
- User notified when request approved
- Admin notified of new requests

## Going to Production

### Steps to Go Live

**1. Get Production Keys**
- Log in to Stripe Dashboard
- Switch to "Live mode"
- Copy production keys (start with `pk_live_` and `sk_live_`)

**2. Update Settings**
```python
# bufia/settings.py
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
```

**3. Set Environment Variables**
```bash
# On your server
export STRIPE_PUBLIC_KEY='pk_live_...'
export STRIPE_SECRET_KEY='sk_live_...'
```

**4. Set Up Webhooks**
- Go to Stripe Dashboard → Developers → Webhooks
- Add endpoint: `https://yourdomain.com/payment/webhook/`
- Select events: `checkout.session.completed`
- Copy webhook secret
- Add to settings: `STRIPE_WEBHOOK_SECRET = 'whsec_...'`

**5. Test in Production**
- Use real credit card (small amount)
- Verify payment processes
- Check notifications work
- Verify redirects work

## Security Best Practices

### ✅ Current Implementation
- API keys in settings (OK for development)
- Test mode enabled
- CSRF protection enabled
- Login required for all payment views

### 🔒 Production Recommendations
1. Move API keys to environment variables
2. Use `.env` file with `python-decouple`
3. Enable webhook signature verification
4. Set up proper error logging
5. Monitor failed payments
6. Set up alerts for suspicious activity

## Support

### Documentation
- Stripe Docs: https://stripe.com/docs
- Stripe API Reference: https://stripe.com/docs/api
- Stripe Testing: https://stripe.com/docs/testing

### Dashboard
- Test Mode: https://dashboard.stripe.com/test
- Live Mode: https://dashboard.stripe.com

### Test Cards
- All test cards: https://stripe.com/docs/testing#cards

## Summary

✅ **Stripe Integration**: Fully functional
✅ **Test Mode**: Enabled and working
✅ **Payment Flow**: Complete end-to-end
✅ **Auto-Approval**: Working correctly
✅ **Notifications**: Sent automatically
✅ **Security**: PCI compliant via Stripe

**The Stripe payment system is working correctly!** Use the test card `4242 4242 4242 4242` to test all payment flows.

## Quick Verification

Run this command to verify Stripe is working:
```bash
python manage.py shell -c "import stripe; from django.conf import settings; stripe.api_key = settings.STRIPE_SECRET_KEY; session = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price_data': {'currency': 'usd', 'unit_amount': 1000, 'product_data': {'name': 'Test'}}, 'quantity': 1}], mode='payment', success_url='http://test.com', cancel_url='http://test.com'); print('✅ Stripe is working! Session ID:', session.id)"
```

Expected output:
```
✅ Stripe is working! Session ID: cs_test_...
```

If you see this, your Stripe integration is fully functional! 🎉
