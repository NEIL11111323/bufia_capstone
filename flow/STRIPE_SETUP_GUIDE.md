# Stripe Payment Integration Guide for BUFIA

This guide will walk you through setting up Stripe payments for your BUFIA system.

## Table of Contents
1. [Create Stripe Account](#1-create-stripe-account)
2. [Get API Keys](#2-get-api-keys)
3. [Configure Django Settings](#3-configure-django-settings)
4. [Create Payment Models](#4-create-payment-models)
5. [Create Payment Views](#5-create-payment-views)
6. [Add Payment Templates](#6-add-payment-templates)
7. [Set Up Webhooks](#7-set-up-webhooks)
8. [Testing](#8-testing)

---

## 1. Create Stripe Account

### Steps:
1. Go to https://stripe.com
2. Click "Sign up" (top right)
3. Fill in your details:
   - Email address
   - Full name
   - Country (Philippines)
   - Password
4. Verify your email
5. Complete business information (you can skip for testing)

**Note:** You can start testing immediately without completing business verification!

---

## 2. Get API Keys

### Steps:
1. Log in to Stripe Dashboard: https://dashboard.stripe.com
2. Click "Developers" in the left sidebar
3. Click "API keys"
4. You'll see two types of keys:

   **Test Keys** (for development):
   - Publishable key: `pk_test_...` (safe to use in frontend)
   - Secret key: `sk_test_...` (keep secret, use in backend only)

   **Live Keys** (for production):
   - Publishable key: `pk_live_...`
   - Secret key: `sk_live_...`

5. Copy both TEST keys for now

**Important:** 
- NEVER commit secret keys to Git!
- Use environment variables for production

---

## 3. Configure Django Settings

### Add to `bufia/settings.py`:

```python
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY = 'pk_test_YOUR_KEY_HERE'  # Replace with your test key
STRIPE_SECRET_KEY = 'sk_test_YOUR_KEY_HERE'       # Replace with your test key
STRIPE_WEBHOOK_SECRET = ''  # We'll add this later

# For production, use environment variables:
# import os
# STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
# STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
```

---

## 4. Create Payment Models

I've created a `Payment` model in `users/models.py` to track all payments:

```python
class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_TYPE = [
        ('membership', 'Membership Fee'),
        ('rental', 'Equipment Rental'),
        ('irrigation', 'Irrigation Service'),
        ('rice_mill', 'Rice Mill Service'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.payment_type} - ₱{self.amount}"
```

---

## 5. Create Payment Views

I've created payment views in `users/views.py`:

### Key Views:

1. **`create_membership_payment`** - Creates Stripe Checkout session
2. **`payment_success`** - Handles successful payments
3. **`payment_cancel`** - Handles cancelled payments
4. **`stripe_webhook`** - Receives Stripe events

### How it works:

```python
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_membership_payment(request):
    # Create Stripe Checkout Session
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'php',
                'product_data': {
                    'name': 'BUFIA Membership Fee',
                },
                'unit_amount': 50000,  # ₱500.00 in centavos
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payment/success/'),
        cancel_url=request.build_absolute_uri('/payment/cancel/'),
    )
    
    return redirect(session.url)
```

---

## 6. Add Payment Templates

### Payment Button Example:

```html
<!-- In profile.html or membership form -->
<form action="{% url 'create_membership_payment' %}" method="post">
    {% csrf_token %}
    <button type="submit" class="btn btn-primary btn-lg">
        <i class="fas fa-credit-card me-2"></i>
        Pay Membership Fee (₱500.00)
    </button>
</form>
```

### Success Page:

```html
<!-- payment_success.html -->
<div class="alert alert-success">
    <h4>Payment Successful!</h4>
    <p>Your membership fee has been paid. Your account will be verified shortly.</p>
</div>
```

---

## 7. Set Up Webhooks

Webhooks allow Stripe to notify your app about payment events.

### Steps:

1. **Install Stripe CLI** (for local testing):
   - Download from: https://stripe.com/docs/stripe-cli
   - Or use: `pip install stripe-cli`

2. **Login to Stripe CLI**:
   ```bash
   stripe login
   ```

3. **Forward webhooks to local server**:
   ```bash
   stripe listen --forward-to localhost:8000/payment/webhook/
   ```

4. **Copy the webhook signing secret** (starts with `whsec_...`)

5. **Add to settings.py**:
   ```python
   STRIPE_WEBHOOK_SECRET = 'whsec_YOUR_SECRET_HERE'
   ```

### For Production:

1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. Enter your URL: `https://yourdomain.com/payment/webhook/`
4. Select events to listen for:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Copy the signing secret

---

## 8. Testing

### Test Card Numbers:

Stripe provides test cards that simulate different scenarios:

**Successful Payment:**
- Card: `4242 4242 4242 4242`
- Expiry: Any future date (e.g., 12/34)
- CVC: Any 3 digits (e.g., 123)
- ZIP: Any 5 digits (e.g., 12345)

**Payment Declined:**
- Card: `4000 0000 0000 0002`

**Requires Authentication (3D Secure):**
- Card: `4000 0025 0000 3155`

**Insufficient Funds:**
- Card: `4000 0000 0000 9995`

### Testing Flow:

1. Start your Django server:
   ```bash
   python manage.py runserver
   ```

2. Start Stripe webhook listener (in another terminal):
   ```bash
   stripe listen --forward-to localhost:8000/payment/webhook/
   ```

3. Go to your site and click "Pay Membership Fee"
4. Use test card: `4242 4242 4242 4242`
5. Complete payment
6. Check webhook events in terminal
7. Verify payment in Stripe Dashboard

---

## Payment Flow Diagram

```
User clicks "Pay" 
    ↓
Django creates Checkout Session
    ↓
User redirected to Stripe Checkout
    ↓
User enters card details
    ↓
Stripe processes payment
    ↓
User redirected back to your site
    ↓
Webhook confirms payment
    ↓
Django updates user status
    ↓
User receives confirmation
```

---

## Security Best Practices

1. **Never expose secret keys**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Validate webhooks**
   - Always verify webhook signatures
   - Check event types

3. **Use HTTPS in production**
   - Stripe requires HTTPS for webhooks
   - Use SSL certificate

4. **Handle errors gracefully**
   - Show user-friendly error messages
   - Log errors for debugging

5. **Test thoroughly**
   - Test all payment scenarios
   - Test webhook handling
   - Test error cases

---

## Common Issues & Solutions

### Issue 1: "Invalid API Key"
**Solution:** Check that you copied the correct key and it starts with `sk_test_` or `pk_test_`

### Issue 2: Webhook not receiving events
**Solution:** 
- Make sure Stripe CLI is running
- Check webhook URL is correct
- Verify webhook secret is set

### Issue 3: Payment succeeds but user not updated
**Solution:** 
- Check webhook handler is working
- Look for errors in Django logs
- Verify webhook signature validation

### Issue 4: Currency error
**Solution:** Use lowercase currency code: `'php'` not `'PHP'`

---

## Next Steps

1. ✅ Install Stripe library
2. ✅ Get API keys from Stripe
3. ✅ Add keys to settings.py
4. ✅ Run migrations for Payment model
5. ✅ Test payment flow with test cards
6. ✅ Set up webhooks
7. ⏳ Go live (complete Stripe verification)

---

## Resources

- **Stripe Documentation:** https://stripe.com/docs
- **Stripe Dashboard:** https://dashboard.stripe.com
- **Test Cards:** https://stripe.com/docs/testing
- **Webhook Testing:** https://stripe.com/docs/webhooks/test
- **Python Library:** https://stripe.com/docs/api/python

---

## Support

If you need help:
1. Check Stripe documentation
2. Look at Stripe logs in Dashboard
3. Check Django error logs
4. Test with Stripe CLI
5. Contact Stripe support (they're very helpful!)

---

**Remember:** Start with test mode, and only switch to live mode when you're ready to accept real payments!
