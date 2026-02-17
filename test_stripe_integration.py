"""
Test Stripe integration
Run with: python manage.py shell < test_stripe_integration.py
"""

import stripe
from django.conf import settings

print("=" * 60)
print("Testing Stripe Integration")
print("=" * 60)

# Test 1: Check Stripe module
print("\n1. Checking Stripe module...")
try:
    print(f"   ✓ Stripe module imported successfully")
    print(f"   ✓ Has checkout: {hasattr(stripe, 'checkout')}")
    print(f"   ✓ Has Session.create: {hasattr(stripe.checkout.Session, 'create')}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Check API key configuration
print("\n2. Checking API key configuration...")
try:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    print(f"   ✓ API key configured")
    print(f"   ✓ Key starts with: {settings.STRIPE_SECRET_KEY[:15]}...")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: Test creating a checkout session (will fail without valid data, but tests API)
print("\n3. Testing Stripe API connection...")
try:
    # This will fail but confirms API is reachable
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 1000,
                'product_data': {
                    'name': 'Test Product',
                },
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='http://localhost:8000/success',
        cancel_url='http://localhost:8000/cancel',
    )
    print(f"   ✓ Checkout session created successfully!")
    print(f"   ✓ Session ID: {session.id}")
    print(f"   ✓ Session URL: {session.url[:50]}...")
except stripe.error.InvalidRequestError as e:
    print(f"   ⚠ API reachable but request invalid (expected): {str(e)[:100]}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Check payment views exist
print("\n4. Checking payment views...")
try:
    from bufia.views import payment_views
    print(f"   ✓ payment_views module imported")
    print(f"   ✓ Has create_rental_payment: {hasattr(payment_views, 'create_rental_payment')}")
    print(f"   ✓ Has create_irrigation_payment: {hasattr(payment_views, 'create_irrigation_payment')}")
    print(f"   ✓ Has create_appointment_payment: {hasattr(payment_views, 'create_appointment_payment')}")
    print(f"   ✓ Has payment_success: {hasattr(payment_views, 'payment_success')}")
    print(f"   ✓ Has payment_cancelled: {hasattr(payment_views, 'payment_cancelled')}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
print("Stripe Integration Test Complete!")
print("=" * 60)
print("\nNext steps:")
print("1. Start Django server: python manage.py runserver")
print("2. Create a rental/appointment/irrigation request")
print("3. Use test card: 4242 4242 4242 4242")
print("4. Complete payment and verify approval")
print("=" * 60)
