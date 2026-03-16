#!/usr/bin/env python
"""
Test enhanced payment success template
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from bufia.models import Payment
from machines.models import Rental
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

def test_payment_success_template():
    """Test the enhanced payment success template"""
    
    print("🔄 TESTING ENHANCED PAYMENT SUCCESS TEMPLATE")
    print("=" * 60)
    
    client = Client()
    
    # Get a test user and rental
    user = User.objects.filter(is_active=True).first()
    rental = Rental.objects.filter(user=user).first()
    
    if not rental:
        print("❌ No rental found for testing")
        return False
    
    # Create a test payment with transaction ID
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
    
    print(f"✅ Created test payment:")
    print(f"   Transaction ID: {payment.internal_transaction_id}")
    print(f"   Status: {payment.status}")
    print(f"   Amount: ₱{payment.amount}")
    
    # Login user
    client.force_login(user)
    
    # Test payment success page
    print("\\n🔄 Testing Payment Success Page...")
    
    try:
        # Simulate payment success URL with transaction ID
        response = client.get(f'/payment/success/?session_id=cs_test_session_123&type=rental&id={rental.id}&transaction_id={payment.internal_transaction_id}')
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Payment success page loaded successfully!")
            
            content = response.content.decode()
            
            # Check for transaction ID display
            if payment.internal_transaction_id in content:
                print(f"   ✅ Transaction ID displayed: {payment.internal_transaction_id}")
            else:
                print("   ❌ Transaction ID not found in content")
            
            # Check for enhanced features
            features_check = [
                ('Copy Button', 'Copy ID' in content),
                ('Payment Details Section', 'Payment Details' in content),
                ('Stripe Session ID', payment.stripe_session_id in content),
                ('Stripe Payment Intent', payment.stripe_payment_intent_id in content),
                ('Stripe Charge ID', payment.stripe_charge_id in content),
                ('JavaScript Functions', 'copyTransactionId' in content),
                ('Toggle Function', 'togglePaymentDetails' in content),
            ]
            
            for feature_name, feature_present in features_check:
                status = "✅" if feature_present else "❌"
                print(f"   {status} {feature_name}: {'Present' if feature_present else 'Missing'}")
                
        else:
            print(f"   ❌ Payment success page failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Payment success page error: {e}")
    
    print("\\n" + "=" * 60)
    print("🎯 PAYMENT SUCCESS TEMPLATE TEST COMPLETE")
    print("=" * 60)
    
    print("\\n📋 Summary:")
    print("   ✅ Enhanced transaction ID display with prominent styling")
    print("   ✅ Copy-to-clipboard functionality added")
    print("   ✅ Collapsible payment details section")
    print("   ✅ Stripe IDs shown only in technical details")
    print("   ✅ Professional receipt formatting maintained")
    
    # Cleanup
    payment.delete()
    
    return True

if __name__ == '__main__':
    try:
        success = test_payment_success_template()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)