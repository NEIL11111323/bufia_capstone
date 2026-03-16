#!/usr/bin/env python
"""
Create a new operator account for testing
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from machines.models import Rental, Machine
from notifications.operator_notifications import notify_operator_job_assigned

User = get_user_model()

def create_operator():
    """Create a new operator account"""
    print("🔧 Creating New Operator Account")
    print("=" * 40)
    
    # Create operator user
    username = "operator2"
    email = "operator2@bufia.com"
    password = "operator456"
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"⚠️  User '{username}' already exists. Updating...")
        operator = User.objects.get(username=username)
    else:
        operator = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name="Maria",
            last_name="Santos",
            is_staff=True,  # Required for operator access
            is_superuser=False,  # Not a superuser
            is_active=True
        )
        print(f"✅ Created operator: {operator.get_full_name()}")
    
    # Update password to ensure it's correct
    operator.set_password(password)
    operator.save()
    
    print(f"📋 Operator Details:")
    print(f"   Username: {operator.username}")
    print(f"   Email: {operator.email}")
    print(f"   Name: {operator.get_full_name()}")
    print(f"   Is Staff: {operator.is_staff}")
    print(f"   Is Superuser: {operator.is_superuser}")
    print(f"   Password: {password}")
    
    # Assign some jobs to this operator
    print(f"\n🎯 Assigning Jobs to Operator")
    
    # Get some rentals that are not assigned to other operators
    available_rentals = Rental.objects.filter(
        status__in=['approved', 'in_progress'],
        assigned_operator__isnull=True
    ).select_related('machine', 'user')[:3]
    
    if available_rentals.exists():
        for i, rental in enumerate(available_rentals, 1):
            rental.assigned_operator = operator
            rental.operator_status = 'assigned'
            rental.operator_last_update_at = timezone.now()
            rental.save(update_fields=[
                'assigned_operator', 'operator_status', 'operator_last_update_at', 'updated_at'
            ])
            
            # Send notification
            notify_operator_job_assigned(operator, rental)
            
            print(f"   ✅ Job {i}: {rental.machine.name} for {rental.user.get_full_name()}")
    else:
        print("   ⚠️  No available rentals to assign")
    
    # Create some additional rentals if needed
    if not available_rentals.exists():
        print(f"\n🔨 Creating Test Rentals")
        
        # Get a machine and user for testing
        try:
            machine = Machine.objects.first()
            user = User.objects.filter(is_staff=False, is_superuser=False).first()
            
            if machine and user:
                for i in range(2):
                    rental = Rental.objects.create(
                        user=user,
                        machine=machine,
                        start_date=timezone.now() + timedelta(days=i+1),
                        end_date=timezone.now() + timedelta(days=i+2),
                        status='approved',
                        workflow_state='approved',
                        workflow_payment_type='online',
                        area=1.5 + i,
                        field_location=f"Test Field {i+1}",
                        assigned_operator=operator,
                        operator_status='assigned',
                        operator_last_update_at=timezone.now()
                    )
                    
                    # Send notification
                    notify_operator_job_assigned(operator, rental)
                    
                    print(f"   ✅ Created Job {i+1}: {machine.name} for {user.get_full_name()}")
        except Exception as e:
            print(f"   ❌ Error creating test rentals: {e}")
    
    print(f"\n🎉 Operator Account Ready!")
    print("=" * 40)
    print(f"Login Credentials:")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"URL: http://127.0.0.1:8000/machines/operator/dashboard/")
    print(f"\nThis operator should see the clean interface with assigned jobs.")

if __name__ == '__main__':
    create_operator()