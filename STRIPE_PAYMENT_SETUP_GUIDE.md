# Stripe Payment Link Setup Guide

## Overview
This guide explains how to configure Stripe payment links to redirect customers back to your BUFIA site after successful payment.

## Payment Success Page
**URL:** `http://127.0.0.1:8000/machines/rentals/payment-success/`
**Production URL:** `https://yourdomain.com/machines/rentals/payment-success/`

## How to Configure Stripe Payment Links

### Option 1: Update Existing Payment Link (Recommended)
1. Go to Stripe Dashboard: https://dashboard.stripe.com/test/payment-links
2. Find your TRACTOR payment link
3. Click "Edit" or create a new one
4. In the "After payment" section:
   - Select "Redirect to a page"
   - Enter: `http://127.0.0.1:8000/machines/rentals/payment-success/`
   - For production: `https://yourdomain.com/machines/rentals/payment-success/`
5. Save the payment link
6. Update the link in your database (see below)

### Option 2: Add Success URL Parameter
You can append the success URL directly to the payment link:
```
https://buy.stripe.com/test_aFa3cw7zJ8jN8dv1fyefC00?success_url=http://127.0.0.1:8000/machines/rentals/payment-success/
```

### Option 3: Use Stripe Checkout Sessions (Advanced)
For more control, implement Stripe Checkout Sessions with custom success/cancel URLs.

## Update TRACTOR Payment Link

### Via Django Admin
1. Go to: http://127.0.0.1:8000/admin/machines/machine/
2. Find "TRACTOR" machine
3. Update the "Stripe payment link" field with the new link
4. Save

### Via Django Shell
```python
python manage.py shell

from machines.models import Machine

tractor = Machine.objects.get(name__icontains='TRACTOR')
tractor.stripe_payment_link = "https://buy.stripe.com/test_aFa3cw7zJ8jN8dv1fyefC00?success_url=http://127.0.0.1:8000/machines/rentals/payment-success/"
tractor.save()
```

## Payment Success Page Features

The payment success page includes:
- ✅ Success confirmation message
- 📋 Rental details summary
- 📝 Next steps information
- 🔗 Quick action buttons:
  - View Rental Details
  - My Rentals
  - Browse Machines
  - Dashboard
- 📧 Support contact information

## User Flow

1. User selects machine and fills rental form
2. User chooses "Online Payment"
3. User submits rental request
4. User sees confirmation page with "Proceed to Payment" button
5. User clicks button → Redirected to Stripe payment page
6. User completes payment on Stripe
7. **Stripe redirects back to payment success page** ← NEW
8. User sees success message and can navigate to:
   - View their rental details
   - Check all rentals
   - Browse more machines
   - Return to dashboard

## Testing

### Test the Flow
1. Create a rental for TRACTOR
2. Select "Online Payment"
3. Click "Proceed to Payment"
4. Use Stripe test card: `4242 4242 4242 4242`
5. Complete payment
6. Verify redirect to success page

### Test Cards
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Requires authentication: `4000 0025 0000 3155`

## Production Deployment

Before going live:
1. Update all payment links with production domain
2. Replace test Stripe keys with live keys
3. Test the complete flow in production
4. Set up Stripe webhooks for payment verification (optional)

## Stripe Webhook Integration (Optional)

For automatic payment verification, set up webhooks:
1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/webhooks/stripe/`
3. Select events: `checkout.session.completed`, `payment_intent.succeeded`
4. Implement webhook handler to auto-verify payments

## Support

For issues:
- Check Stripe Dashboard logs
- Verify success_url is correctly configured
- Ensure user is logged in when returning
- Check browser console for errors

## Notes

- The payment success page works for logged-in users only
- It shows the most recent rental for the user
- Admin still needs to approve the rental after payment
- Payment verification can be automated with webhooks
