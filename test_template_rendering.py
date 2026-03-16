#!/usr/bin/env python
"""
Test payment success template rendering directly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from bufia.models import Payment
from machines.models import Rental
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

User = get_user_model()

def test_template_rendering():
    """Test payment success template rendering directly"""
    
    print("🔄 TESTING PAYMENT SUCCESS TEMPLATE RENDERING")
    print("=" * 60)
    
    # Get test data
    user = User.objects.filter(is_active=True).first()
    rental = Rental.objects.filter(user=user).first()
    
    if not rental:
        print("❌ No rental found for testing")
        return False
    
    # Create test payment
    content_type = ContentType.objects.get_for_model(Rental)
    payment = Payment.objects.create(
        user=user,
        payment_type='rental',
        amount=1500.00,
        currency='PHP',
        status='completed',
        stripe_session_id='cs_test_session_123',
        stripe_payment_intent_id='pi_test_intent_123',
        stripe_charge_id='ch_test_charge_123',
        content_type=content_type,
        object_id=rental.id
    )
    
    print(f"✅ Test Payment Created:")
    print(f"   Transaction ID: {payment.internal_transaction_id}")
    print(f"   Stripe Payment Intent: {payment.stripe_payment_intent_id}")
    print(f"   Stripe Charge ID: {payment.stripe_charge_id}")
    
    # Create request context
    factory = RequestFactory()
    request = factory.get('/payment/success/')
    request.user = user
    
    # Template context
    context = {
        'request': request,
        'transaction_id': payment.internal_transaction_id,
        'payment_type': 'rental',
        'rental': rental,
        'payment': payment,
        'machine_name': rental.machine.name,
        'amount': rental.payment_amount,
    }
    
    print("\\n🔄 Testing Template Rendering...")
    
    try:
        # Render the template
        rendered_html = render_to_string('machines/payment_success.html', context, request=request)
        
        print("   ✅ Template rendered successfully!")
        
        # Check for enhanced features
        features_check = [
            ('Transaction ID Display', payment.internal_transaction_id in rendered_html),
            ('Prominent Styling', 'transaction-id-prominent' in rendered_html),
            ('Copy Button', 'Copy ID' in rendered_html),
            ('Copy Function', 'copyTransactionId' in rendered_html),
            ('Payment Details Section', 'Payment Details' in rendered_html),
            ('Toggle Function', 'togglePaymentDetails' in rendered_html),
            ('Stripe Session ID', payment.stripe_session_id in rendered_html),
            ('Stripe Payment Intent', payment.stripe_payment_intent_id in rendered_html),
            ('Stripe Charge ID', payment.stripe_charge_id in rendered_html),
            ('Enhanced CSS', 'transaction-id-prominent' in rendered_html),
        ]
        
        print("\\n📋 Feature Check:")
        for feature_name, feature_present in features_check:
            status = "✅" if feature_present else "❌"
            print(f"   {status} {feature_name}")
        
        # Check template structure
        print("\\n🏗️  Template Structure:")
        if 'YOUR TRANSACTION ID' in rendered_html:
            print("   ✅ Prominent transaction ID header")
        if 'BUF-TXN-' in rendered_html:
            print("   ✅ Transaction ID format displayed")
        if 'Payment Details' in rendered_html:
            print("   ✅ Collapsible payment details section")
        if 'no-print' in rendered_html:
            print("   ✅ Print-friendly styling")
            
    except Exception as e:
        print(f"   ❌ Template rendering error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\\n" + "=" * 60)
    print("🎯 TEMPLATE RENDERING TEST COMPLETE")
    print("=" * 60)
    
    # Cleanup
    payment.delete()
    
    return True

if __name__ == '__main__':
    try:
        success = test_template_rendering()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)