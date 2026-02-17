# Payment Testing Guide

## Quick Test (5 Minutes)

### Prerequisites
- Django server running
- User account created and logged in
- At least one machine available

### Test 1: Machine Rental Payment

1. **Create Rental Request**
   - Go to: http://localhost:8000/machines/
   - Click "Rent" on any available machine
   - Fill in:
     - Start Date: Tomorrow
     - End Date: 3 days from now
     - Purpose: "Test rental"
   - Click "Submit"

2. **Verify Redirect to Stripe**
   - You should be redirected to Stripe Checkout page
   - URL should contain: `checkout.stripe.com`
   - You should see:
     - Machine name
     - Rental dates
     - Total amount

3. **Complete Payment**
   - Use test card: `4242 4242 4242 4242`
   - Expiry: `12/25`
   - CVC: `123`
   - ZIP: `12345`
   - Click "Pay"

4. **Verify Success**
   - You should be redirected back to your site
   - Success message should appear
   - Rental status should be "Approved"
   - Check notifications (bell icon) - should see approval notification

### Test 2: Rice Mill Appointment Payment

1. **Create Appointment**
   - Go to: http://localhost:8000/machines/
   - Find a Rice Mill machine
   - Click "Schedule Appointment"
   - Fill in:
     - Date: Next week
     - Time Slot: Morning
     - Rice Quantity: 1000 kg
   - Click "Submit"

2. **Complete Payment**
   - Redirected to Stripe Checkout
   - Use same test card: `4242 4242 4242 4242`
   - Complete payment

3. **Verify Success**
   - Redirected back with success message
   - Appointment status: "Approved"
   - Notification received

### Test 3: Irrigation Request Payment

1. **Create Irrigation Request**
   - Go to: http://localhost:8000/irrigation/
   - Click "Create New Request"
   - Fill in all required fields:
     - Date: Next week
     - Duration: 8 hours
     - Area: 5 hectares
     - Crop Type: Rice
   - Click "Submit"

2. **Complete Payment**
   - Redirected to Stripe Checkout
   - Use test card
   - Complete payment

3. **Verify Success**
   - Success message appears
   - Request status: "Approved"
   - Notification received

### Test 4: Payment Cancellation

1. **Start Payment Process**
   - Create any request (rental/appointment/irrigation)
   - Get redirected to Stripe Checkout

2. **Cancel Payment**
   - Click the back arrow (←) in Stripe Checkout
   - OR close the browser tab

3. **Verify Cancellation**
   - You should be redirected back to your site
   - Warning message: "Payment was cancelled"
   - Request status remains: "Pending"
   - You can retry payment later

## Stripe Test Cards

### Successful Payments
```
Card: 4242 4242 4242 4242
Exp: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits
```

### Declined Payment
```
Card: 4000 0000 0000 0002
Exp: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits
```

### Requires Authentication (3D Secure)
```
Card: 4000 0025 0000 3155
Exp: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits
```

### Insufficient Funds
```
Card: 4000 0000 0000 9995
Exp: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits
```

## Expected Behavior Checklist

### Before Payment
- [ ] Request is created with status "Pending"
- [ ] User is redirected to Stripe Checkout
- [ ] Stripe page shows correct amount and description
- [ ] User can see payment details

### During Payment
- [ ] Test card is accepted
- [ ] Payment processes without errors
- [ ] Loading indicator appears

### After Successful Payment
- [ ] User is redirected back to success page
- [ ] Success message is displayed
- [ ] Request status changes to "Approved"
- [ ] User receives approval notification
- [ ] Notification bell shows red dot

### After Cancelled Payment
- [ ] User is redirected back to cancelled page
- [ ] Warning message is displayed
- [ ] Request status remains "Pending"
- [ ] User can access the request again
- [ ] User can retry payment

## Troubleshooting

### Issue: "Error creating payment session"

**Possible Causes:**
1. Stripe API keys not configured
2. Invalid API keys
3. Network connection issue

**Solution:**
1. Check `bufia/settings.py` for Stripe keys
2. Verify keys are correct (start with `pk_test_` and `sk_test_`)
3. Check Django console for detailed error

### Issue: "Payment successful but status not updated"

**Possible Causes:**
1. Signal not triggered
2. Database error
3. View error

**Solution:**
1. Check Django console logs
2. Verify signals are registered (see NOTIFICATIONS_GUIDE.md)
3. Check if payment success view is being called

### Issue: "Redirect loop"

**Possible Causes:**
1. Browser cache issue
2. Session issue
3. URL configuration issue

**Solution:**
1. Clear browser cache and cookies
2. Try in incognito/private mode
3. Check URL patterns in `bufia/urls.py`

### Issue: "Stripe page not loading"

**Possible Causes:**
1. Network issue
2. Stripe service down
3. Invalid session

**Solution:**
1. Check internet connection
2. Check Stripe status: https://status.stripe.com
3. Try creating a new request

## Viewing Payment Details in Stripe Dashboard

1. Go to: https://dashboard.stripe.com/test/payments
2. Log in with your Stripe account
3. You'll see all test payments
4. Click on a payment to see details:
   - Amount
   - Customer info
   - Metadata (rental_id, user_id, etc.)
   - Timeline of events

## Advanced Testing

### Test Different Amounts

1. **Small Amount**: Create 1-day rental
2. **Large Amount**: Create 30-day rental
3. **Decimal Amount**: Create rental with odd number of days

### Test Error Scenarios

1. **Declined Card**: Use `4000 0000 0000 0002`
2. **Expired Card**: Use past expiry date
3. **Invalid CVC**: Use `99`

### Test Multiple Payments

1. Create multiple rentals
2. Pay for each one
3. Verify all are approved
4. Check notifications for all

## Production Testing Checklist

Before going live:

- [ ] Test with production Stripe keys
- [ ] Test with real (small) amounts
- [ ] Verify webhook is working
- [ ] Test refund process
- [ ] Test payment failure handling
- [ ] Verify email notifications work
- [ ] Test on mobile devices
- [ ] Test with different browsers
- [ ] Verify SSL certificate is valid
- [ ] Test payment cancellation
- [ ] Verify admin can see payment history
- [ ] Test with different user roles

## Support

If you encounter issues:

1. Check Django console logs
2. Check Stripe Dashboard logs
3. Review `STRIPE_PAYMENT_GUIDE.md`
4. Check Stripe documentation: https://stripe.com/docs
