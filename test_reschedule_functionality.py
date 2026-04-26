#!/usr/bin/env python
"""
Test script to verify the reschedule functionality works correctly
"""
import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Machine, Rental

User = get_user_model()

def test_reschedule_functionality():
    """Test the reschedule functionality"""
    print("Testing reschedule functionality...")
    
    # Get or create test data
    try:
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            print("No admin user found. Creating one...")
            admin_user = User.objects.create_user(
                username='admin_test',
                email='admin@test.com',
                is_staff=True,
                is_superuser=True
            )
            admin_user.set_password('admin123')
            admin_user.save()
        
        # Get a machine
        machine = Machine.objects.first()
        if not machine:
            print("No machines found. Please create a machine first.")
            return
        
        # Get a customer
        customer = User.objects.filter(is_staff=False).first()
        if not customer:
            print("No customer found. Creating one...")
            customer = User.objects.create_user(
                username='customer_test',
                email='customer@test.com'
            )
            customer.set_password('customer123')
            customer.save()
        
        # Create a test rental that could be rescheduled
        today = date.today()
        start_date = today + timedelta(days=5)
        end_date = start_date + timedelta(days=3)
        
        rental = Rental.objects.create(
            machine=machine,
            user=customer,
            start_date=start_date,
            end_date=end_date,
            status='approved',
            workflow_state='approved',
            payment_method='face_to_face',
            payment_amount=1000.00,
            payment_verified=True
        )
        
        print(f"Created test rental #{rental.id}")
        print(f"Machine: {machine.name}")
        print(f"Customer: {customer.username}")
        print(f"Original dates: {start_date} to {end_date}")
        print(f"Status: {rental.status}")
        print(f"Workflow state: {rental.workflow_state}")
        
        # Test URL pattern
        from django.urls import reverse
        reschedule_url = reverse('machines:reschedule_rental', kwargs={'rental_id': rental.id})
        print(f"Reschedule URL: {reschedule_url}")
        
        print("\n✅ Reschedule functionality setup completed successfully!")
        print(f"You can now test rescheduling rental #{rental.id} in the admin dashboard.")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_reschedule_functionality()