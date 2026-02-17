# Stripe Troubleshooting Guide

## Error: 'NoneType' object has no attribute 'Session'

### Problem
This error occurs when the Stripe module is not properly imported or configured.

### Solution ✅ (Already Fixed)
The issue was caused by an outdated Stripe version (7.8.0). We upgraded to Stripe 14.0.1.

**What was done:**
```bash
pip install --upgrade stripe
```

**Updated files:**
- `requirements.txt` - Updated stripe version to 14.0.1
- `bufia/views/payment_views.py` - Added error handling for missing Stripe module

### Verification
Run the test script to verify Stripe is working:
```bash
Get-Content test_stripe_integration.py | python manage.py shell
```

Expected output:
```
✓ Stripe module imported successfully
✓ Has checkout: True
✓ Has Session.create: True
✓ API key configured
✓ Checkout session created successfully!
```

## Common Stripe Errors

### 1. "No module named 'stripe'"

**Cause:** Stripe not installed

**Solution:**
```bash
pip install stripe==14.0.1
```

### 2. "Invalid API Key"

**Cause:** Wrong or missing API key

**Solution:**
Check `bufia/settings.py`:
```python
STRIPE_SECRET_KEY = 'sk_test_51SXhx2Aque0gnK4A...'
```

Make sure:
- Key starts with `sk_test_` (for test mode)
- Key is complete (no truncation)
- No extra spaces or quotes

### 3. "Payment system is not configured"

**Cause:** Stripe module failed to import

**Solution:**
1. Check if Stripe is installed: `pip show stripe`
2. Restart Django server
3. Check Django console for import errors

### 4. "Invalid request error"

**Cause:** Missing or invalid parameters in checkout session

**Solution:**
Check payment views for:
- Valid amount (must be positive integer in cents)
- Valid currency code ('usd', 'php', etc.)
- Valid success_url and cancel_url

### 5. "Checkout session expired"

**Cause:** User took too long to complete payment

**Solution:**
- User should create a new request
- Checkout sessions expire after 24 hours

## Testing Checklist

### Before Testing
- [ ] Stripe installed: `pip show stripe`
- [ ] Version 14.0.1 or higher
- [ ] API keys configured in settings.py
- [ ] Django server restarted

### During Testing
- [ ] Create rental/appointment/irrigation request
- [ ] Redirected to Stripe Checkout
- [ ] Can see payment form
- [ ] Test card accepted: `4242 4242 4242 4242`
- [ ] Payment processes successfully

### After Payment
- [ ] Redirected back to success page
- [ ] Success message displayed
- [ ] Request status changed to "Approved"
- [ ] Notification received

## Debugging Steps

### Step 1: Check Stripe Installation
```bash
pip show stripe
```

Expected output:
```
Name: stripe
Version: 14.0.1
```

### Step 2: Test Stripe Import
```bash
python -c "import stripe; print('OK')"
```

Expected output:
```
OK
```

### Step 3: Check API Key
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.STRIPE_SECRET_KEY[:20])
sk_test_51SXhx2Aque0
```

### Step 4: Test Checkout Session Creation
```bash
Get-Content test_stripe_integration.py | python manage.py shell
```

Should show all green checkmarks (✓)

### Step 5: Check Django Logs
Start server and watch for errors:
```bash
python manage.py runserver
```

Look for:
- Import errors
- Configuration errors
- API errors

## Quick Fixes

### Fix 1: Reinstall Stripe
```bash
pip uninstall stripe
pip install stripe==14.0.1
```

### Fix 2: Restart Django Server
```bash
# Stop server (Ctrl+C)
python manage.py runserver
```

### Fix 3: Clear Python Cache
```bash
# Delete __pycache__ folders
# Restart Django server
```

### Fix 4: Check Virtual Environment
Make sure you're in the correct virtual environment:
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install Stripe
pip install stripe==14.0.1
```

## Stripe Dashboard

### View Test Payments
1. Go to: https://dashboard.stripe.com/test/payments
2. Log in with your Stripe account
3. See all test payments and their status

### View Logs
1. Go to: https://dashboard.stripe.com/test/logs
2. See all API requests
3. Check for errors

### View Events
1. Go to: https://dashboard.stripe.com/test/events
2. See webhook events
3. Check delivery status

## Environment-Specific Issues

### Windows
- Use PowerShell or CMD
- Activate virtual environment: `.venv\Scripts\activate`
- Use `Get-Content` instead of `<` for piping

### Linux/Mac
- Use bash or zsh
- Activate virtual environment: `source .venv/bin/activate`
- Can use `<` for piping: `python manage.py shell < test.py`

## Getting Help

### Check Logs
1. Django console output
2. Browser console (F12)
3. Stripe Dashboard logs

### Test with Curl
```bash
curl https://api.stripe.com/v1/charges \
  -u sk_test_51SXhx2Aque0gnK4A...: \
  -d amount=1000 \
  -d currency=usd \
  -d source=tok_visa
```

### Contact Support
- Stripe Support: https://support.stripe.com
- Stripe Documentation: https://stripe.com/docs
- Stripe Community: https://github.com/stripe/stripe-python/issues

## Prevention

### Best Practices
1. Always use latest Stripe version
2. Keep API keys in environment variables (production)
3. Test in test mode before going live
4. Monitor Stripe Dashboard regularly
5. Set up error logging
6. Handle all Stripe exceptions

### Regular Maintenance
1. Update Stripe monthly: `pip install --upgrade stripe`
2. Check for breaking changes in release notes
3. Test payment flow after updates
4. Monitor error rates in Stripe Dashboard

## Summary

✅ **Issue Fixed:** Upgraded Stripe from 7.8.0 to 14.0.1
✅ **Verification:** All tests passing
✅ **Ready to Use:** Payment system fully functional

Use test card `4242 4242 4242 4242` to test payments!
