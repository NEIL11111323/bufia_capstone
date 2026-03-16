#!/usr/bin/env python
"""
Script to assign active rentals to Juan (operator1) for testing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental
from django.utils import timezone

User = get_user_model()

print("\n" + "="*70)
print("ASSIGNING JOBS TO JUAN (operator1)")
print("="*70 + "\n")

# Get Juan
try:
    juan = User.objects.get(username='operator1')
    print(f"✅ Found operator: {juan.username} ({juan.get_full_name()})\n")
except User.DoesNotExist:
    print("❌ Operator 'operator1' not found!")
    exit(1)

# Get approved rentals that need operators
rentals_to_assign = Rental.objects.filter(
    status='approved',
    assigned_operator__isnull=True
).exclude(
    workflow_state__in=['completed', 'cancelled']
).order_by('-created_at')[:5]  # Assign the 5 most recent

print(f"Found {rentals_to_assign.count()} rentals to assign:\n")

assigned_count = 0

for rental in rentals_to_assign:
    rental.assigned_operator = juan
    rental.operator_status = 'assigned'
    rental.operator_last_update_at = timezone.now()
    rental.save(update_fields=[
        'assigned_operator',
        'operator_status',
        'operator_last_update_at',
        'updated_at'
    ])
    
    print(f"✅ Assigned Rental #{rental.id}")
    print(f"   Machine: {rental.machine.name}")
    print(f"   Member: {rental.user.get_full_name()}")
    print(f"   Dates: {rental.start_date} to {rental.end_date}")
    print(f"   Payment Type: {rental.payment_type}")
    print()
    
    assigned_count += 1

print("="*70)
print(f"✅ Successfully assigned {assigned_count} job(s) to Juan!")
print("="*70)
print("\nJuan can now login and see these jobs at:")
print("http://127.0.0.1:8000/machines/operator/dashboard/")
print("\nLogin credentials:")
print("  Username: operator1")
print("  Password: operator123")
print("="*70 + "\n")
