"""
Test script for online payment workflow in rental approval page
Tests the complete flow: Approve → User Pays → Admin Verifies → Complete
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental, Machine
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_online_payment_workflow():
    """Test the complete online payment workflow"""
    print_section("ONLINE PAYMENT WORKFLOW TEST")
    
    # Get or create test users
    try:
        admin = User.objects.filter(is_staff=True, is_superuser=True).first()
        if not admin:
            print("❌ No admin user found. Please create an admin user first.")
            return
        
        member = User.objects.filter(is_staff=False, is_superuser=False).first()
        if not member:
            print("❌ No member user found. Please create a member user first.")
            return
        
        # Get a test machine
        machine = Machine.objects.filter(status='available').first()
        if not machine:
            print("❌ No available machine found.")
            return
        
        print(f"✅ Admin: {admin.get_full_name()} (@{admin.username})")
        print(f"✅ Member: {member.get_full_name()} (@{member.username})")
        print(f"✅ Machine: {machine.name}")
        
    except Exception as e:
        print(f"❌ Error setting up test: {e}")
        return
    
    # Step 1: Create a rental with online payment
    print_section("STEP 1: Create Rental with Online Payment")
    try:
        rental = Rental.objects.create(
            user=member,
            machine=machine,
            start_date=timezone.now().date() + timedelta(days=1),
            end_date=timezone.now().date() + timedelta(days=3),
            purpose="Test online payment workflow",
            payment_method='online',
            payment_type='cash',
            payment_amount=1500.00,
            status='pending',
            workflow_state='requested'
        )
        print(f"✅ Created rental #{rental.id}")
        print(f"   Payment Method: {rental.get_payment_method_display()}")
        print(f"   Payment Amount: PHP {rental.payment_amount}")
        print(f"   Status: {rental.status}")
        print(f"   Workflow State: {rental.workflow_state}")
    except Exception as e:
        print(f"❌ Error creating rental: {e}")
        return
    
    # Step 2: Admin approves the rental
    print_section("STEP 2: Admin Approves Rental")
    try:
        rental.status = 'approved'
        rental.workflow_state = 'approved'
        rental.verified_by = admin
        rental.save()
        print(f"✅ Rental approved by {admin.get_full_name()}")
        print(f"   Status: {rental.status}")
        print(f"   Workflow State: {rental.workflow_state}")
        print(f"   Payment Verified: {rental.payment_verified}")
        print(f"   → Member should now receive payment link")
    except Exception as e:
        print(f"❌ Error approving rental: {e}")
        return
    
    # Step 3: Simulate user completing online payment
    print_section("STEP 3: Member Completes Online Payment")
    try:
        rental.payment_date = timezone.now()
        rental.stripe_session_id = f"cs_test_{rental.id}_simulation"
        rental.payment_status = 'pending'
        rental.save()
        print(f"✅ Payment received")
        print(f"   Payment Date: {rental.payment_date}")
        print(f"   Stripe Session: {rental.stripe_session_id}")
        print(f"   Payment Status: {rental.payment_status}")
        print(f"   Payment Verified: {rental.payment_verified}")
        print(f"   → Admin should now verify payment in Stripe Dashboard")
    except Exception as e:
        print(f"❌ Error simulating payment: {e}")
        return
    
    # Step 4: Check rental approval page URL
    print_section("STEP 4: Rental Approval Page")
    print(f"📋 Admin should visit:")
    print(f"   http://127.0.0.1:8000/machines/admin/rental/{rental.id}/approve/")
    print(f"\n📝 Admin should see:")
    print(f"   ✓ Payment Details Card with:")
    print(f"     - Transaction ID: {rental.get_transaction_id or 'Pending'}")
    print(f"     - Payment Date: {rental.payment_date}")
    print(f"     - Amount: PHP {rental.payment_amount}")
    print(f"     - Stripe Session ID")
    print(f"   ✓ 'View in Stripe Dashboard' button")
    print(f"   ✓ 'Verify Payment & Complete Rental' button")
    
    # Step 5: Simulate admin verifying payment
    print_section("STEP 5: Admin Verifies Payment")
    print(f"⚠️  In production, admin would:")
    print(f"   1. Click 'View in Stripe Dashboard'")
    print(f"   2. Verify payment succeeded")
    print(f"   3. Click 'Verify Payment & Complete Rental'")
    print(f"\n🔧 Simulating verification...")
    
    try:
        # This simulates what the verify_online_payment view does
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType
        
        # Create payment record (this is what _ensure_rental_payment_record does)
        content_type = ContentType.objects.get_for_model(Rental)
        payment, created = Payment.objects.get_or_create(
            content_type=content_type,
            object_id=rental.id,
            defaults={
                'user': rental.user,
                'payment_type': 'rental',
                'amount': rental.payment_amount,
                'currency': 'PHP',
                'status': 'completed',
                'paid_at': rental.payment_date,
            }
        )
        if not created:
            payment.status = 'completed'
            payment.paid_at = rental.payment_date
            payment.save()
        
        rental.payment_verified = True
        rental.payment_status = 'paid'
        rental.status = 'completed'
        rental.workflow_state = 'completed'
        rental.verification_date = timezone.now()
        rental.verified_by = admin
        rental.actual_completion_time = timezone.now()
        rental.save()
        
        print(f"✅ Payment verified and rental completed")
        print(f"   Payment Verified: {rental.payment_verified}")
        print(f"   Payment Status: {rental.payment_status}")
        print(f"   Status: {rental.status}")
        print(f"   Workflow State: {rental.workflow_state}")
        print(f"   Verification Date: {rental.verification_date}")
        print(f"   Verified By: {rental.verified_by.get_full_name()}")
        print(f"   Transaction ID: {payment.internal_transaction_id}")
        
    except Exception as e:
        print(f"❌ Error verifying payment: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print_section("WORKFLOW SUMMARY")
    print(f"✅ Rental #{rental.id} - Complete Online Payment Workflow")
    print(f"\n📊 Final State:")
    print(f"   Machine: {rental.machine.name}")
    print(f"   Renter: {rental.user.get_full_name()}")
    print(f"   Payment Method: {rental.get_payment_method_display()}")
    print(f"   Payment Amount: PHP {rental.payment_amount}")
    print(f"   Payment Status: {rental.payment_status}")
    print(f"   Payment Verified: {'✅ Yes' if rental.payment_verified else '❌ No'}")
    print(f"   Rental Status: {rental.status}")
    print(f"   Transaction ID: {rental.get_transaction_id}")
    print(f"   Verified By: {rental.verified_by.get_full_name()}")
    print(f"   Verification Date: {rental.verification_date}")
    
    print(f"\n🎯 Test Rental URL:")
    print(f"   http://127.0.0.1:8000/machines/admin/rental/{rental.id}/approve/")
    
    print("\n" + "=" * 70)
    print("✅ ONLINE PAYMENT WORKFLOW TEST COMPLETED")
    print("=" * 70)

if __name__ == '__main__':
    test_online_payment_workflow()
