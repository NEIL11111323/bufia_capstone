# Stripe Payment Integration Guide

## Overview
The BUFIA system now includes Stripe payment integration for:
- Machine Rentals
- Rice Mill Appointments
- Irrigation Requests

## How It Works

### User Flow

1. **User submits a request** (rental/appointment/irrigation)
2. **System redirects to Stripe Checkout** (Stripe's built-in payment form)
3. **User completes payment** using credit/debit card
4. **Stripe redirects back** to success page
5. **System auto-approves** the request
6. **User receives notification** about approval

### Payment Amounts

The system calculates payment amounts automatically:

#### Machine Rentals
- **Formula**: `Machine Price × Number of Days`
- Example: $100/day × 3 days = $300

#### Rice Mill Appointments
- **Formula**: `Rice Quantity (kg) × $0.15 per kg`
- Example: 1000 kg × $0.15 = $150

#### Irrigation Requests
- **Formula**: `Area (hectares) × Duration (hours) × $10`
- Example: 5 hectares × 8 hours × $10 = $400

*Note: These rates can be adjusted in the payment views.*

## Configuration

### Stripe API Keys (Already Configured)

In `bufia/settings.py`:
```python
STRIPE_PUBLIC_KEY = 'pk_test_51SXhx2Aque0gnK4A...'
STRIPE_SECRET_KEY = 'sk_test_51SXhx2Aque0gnK4A...'
```

### Payment URLs

- **Rental Payment**: `/payment/rental/<rental_id>/`
- **Appointment Payment**: `/payment/appointment/<appointment_id>/`
- **Irrigation Payment**: `/payment/irrigation/<irrigation_id>/`
- **Success Page**: `/payment/success/`
- **Cancelled Page**: `/payment/cancelled/`
- **Webhook**: `/payment/webhook/` (for Stripe events)

## Testing the Payment Flow

### Test with Stripe Test Cards

Stripe provides test card numbers for testing:

**Successful Payment:**
- Card Number: `4242 4242 4242 4242`
- Expiry: Any future date (e.g., 12/25)
- CVC: Any 3 digits (e.g., 123)
- ZIP: Any 5 digits (e.g., 12345)

**Payment Declined:**
- Card Number: `4000 0000 0000 0002`

**Requires Authentication:**
- Card Number: `4000 0025 0000 3155`

### Testing Steps

1. **Create a Rental Request**
   - Log in as a user
   - Go to Machines → Select a machine → Rent
   - Fill in the form and submit
   - You'll be redirected to Stripe Checkout

2. **Complete Payment**
   - Use test card: `4242 4242 4242 4242`
   - Enter any future expiry date
   - Enter any CVC and ZIP
   - Click "Pay"

3. **Verify Success**
   - You'll be redirected back to the success page
   - The rental status will be "Approved"
   - You'll receive a notification

4. **Test Cancellation**
   - During payment, click the back arrow or close the window
   - You'll be redirected to the cancelled page
   - The rental remains "Pending"
   - You can try payment again later

## Payment Status Flow

```
User Submits Request
        ↓
Status: Pending
        ↓
Redirect to Stripe Checkout
        ↓
    ┌───┴───┐
    ↓       ↓
Payment   Payment
Success   Cancelled
    ↓       ↓
Status:   Status:
Approved  Pending
    ↓       ↓
User      User can
Notified  retry
```

## Features

### Auto-Approval After Payment
- Once payment is successful, the request is automatically approved
- No admin intervention needed for paid requests
- User receives approval notification immediately

### Payment Cancellation
- Users can cancel payment and return to the site
- Request remains in "Pending" status
- Users can retry payment later

### Secure Payment Processing
- All payment processing handled by Stripe
- No credit card data stored on your server
- PCI compliance handled by Stripe

## Webhook Configuration (Optional)

For production, set up webhooks to handle payment events:

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/payment/webhook/`
3. Select events: `checkout.session.completed`
4. Copy the webhook secret
5. Add to `settings.py`:
   ```python
   STRIPE_WEBHOOK_SECRET = 'whsec_...'
   ```

## Customizing Payment Amounts

To change payment calculations, edit `bufia/views/payment_views.py`:

### For Rentals:
```python
# Current: Machine price × days
amount = int(rental.machine.current_price * duration_days * 100)

# Custom: Fixed rate
amount = 5000  # $50.00
```

### For Appointments:
```python
# Current: $0.15 per kg
amount = int(float(appointment.rice_quantity) * 0.15 * 100)

# Custom: Fixed rate per appointment
amount = 10000  # $100.00
```

### For Irrigation:
```python
# Current: Area × Duration × $10
amount = int(irrigation_request.area_size * irrigation_request.duration_hours * 10 * 100)

# Custom: Per hectare rate
amount = int(irrigation_request.area_size * 50 * 100)  # $50 per hectare
```

## Admin Features

### Viewing Payments
- Admins can still manually approve requests without payment
- Payment status is tracked separately
- Future: Add payment history view in admin panel

### Manual Approval
- Admins can approve requests directly from Django admin
- This bypasses the payment requirement
- Useful for special cases or exemptions

## Troubleshooting

### "Payment session error"
- Check Stripe API keys in settings.py
- Verify keys are for the correct Stripe account
- Check Django logs for detailed error

### "Payment successful but status not updated"
- Check if signals are working (see NOTIFICATIONS_GUIDE.md)
- Verify the payment success view is being called
- Check Django logs for errors

### "Redirect loop"
- Clear browser cache and cookies
- Check if success_url and cancel_url are correct
- Verify URL patterns in urls.py

## Security Notes

### Test vs Production Keys
- **Test keys** (current): Start with `pk_test_` and `sk_test_`
- **Production keys**: Start with `pk_live_` and `sk_live_`
- Never commit production keys to version control

### Best Practices
1. Move API keys to environment variables in production
2. Use `.env` file with `python-decouple` or similar
3. Enable webhook signature verification
4. Set up proper error logging
5. Monitor failed payments in Stripe Dashboard

## Going Live

Before going to production:

1. **Get Production Keys**
   - Log in to Stripe Dashboard
   - Switch to "Live mode"
   - Copy production keys

2. **Update Settings**
   ```python
   STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
   STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
   ```

3. **Set Up Webhooks**
   - Configure webhook endpoint in Stripe
   - Add webhook secret to settings

4. **Test Thoroughly**
   - Test all payment flows
   - Verify notifications work
   - Check error handling

5. **Monitor**
   - Watch Stripe Dashboard for issues
   - Monitor Django logs
   - Set up alerts for failed payments

## Support

For Stripe-specific issues:
- Stripe Documentation: https://stripe.com/docs
- Stripe Support: https://support.stripe.com

For integration issues:
- Check Django logs
- Review payment_views.py
- Test with Stripe test cards
