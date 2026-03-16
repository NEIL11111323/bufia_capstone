#!/usr/bin/env python
"""
Script to check operator assignments and debug why jobs aren't showing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("\n" + "="*70)
print("OPERATOR ASSIGNMENT DIAGNOSTIC")
print("="*70 + "\n")

# Get operators
operators = User.objects.filter(is_staff=True, is_superuser=False)

print(f"Found {operators.count()} operator(s):\n")

for operator in operators:
    print(f"Operator: {operator.username} ({operator.get_full_name() or 'No name'})")
    print("-" * 70)
    
    # Get all rentals assigned to this operator
    all_assigned = Rental.objects.filter(assigned_operator=operator)
    print(f"  Total rentals assigned: {all_assigned.count()}")
    
    # Get active rentals (not completed/cancelled/rejected)
    active_assigned = all_assigned.exclude(
        status__in=['completed', 'cancelled', 'rejected']
    )
    print(f"  Active rentals: {active_assigned.count()}")
    
    if active_assigned.exists():
        print(f"\n  Active Rental Details:")
        for rental in active_assigned:
            print(f"    - Rental #{rental.id}: {rental.machine.name}")
            print(f"      User: {rental.user.get_full_name()}")
            print(f"      Status: {rental.status}")
            print(f"      Workflow State: {rental.workflow_state}")
            print(f"      Operator Status: {rental.operator_status}")
            print(f"      Dates: {rental.start_date} to {rental.end_date}")
            print(f"      Payment Type: {rental.payment_type}")
            print()
    else:
        print(f"  ⚠️  No active rentals assigned to this operator\n")
    
    print()

# Check all rentals that need operators
print("\n" + "="*70)
print("RENTALS THAT NEED OPERATORS")
print("="*70 + "\n")

# Get rentals that are approved but have no operator
needs_operator = Rental.objects.filter(
    status='approved',
    assigned_operator__isnull=True
).exclude(
    workflow_state__in=['completed', 'cancelled']
)

print(f"Found {needs_operator.count()} rental(s) needing operator assignment:\n")

for rental in needs_operator:
    print(f"Rental #{rental.id}: {rental.machine.name}")
    print(f"  User: {rental.user.get_full_name()}")
    print(f"  Status: {rental.status}")
    print(f"  Workflow State: {rental.workflow_state}")
    print(f"  Dates: {rental.start_date} to {rental.end_date}")
    print(f"  Payment Type: {rental.payment_type}")
    print(f"  Requires Operator: {rental.requires_operator_service}")
    print()

# Check all rentals with operators assigned
print("\n" + "="*70)
print("ALL RENTALS WITH OPERATORS ASSIGNED")
print("="*70 + "\n")

with_operators = Rental.objects.filter(
    assigned_operator__isnull=False
).select_related('assigned_operator', 'machine', 'user')

print(f"Found {with_operators.count()} rental(s) with operators assigned:\n")

for rental in with_operators:
    print(f"Rental #{rental.id}: {rental.machine.name}")
    print(f"  Operator: {rental.assigned_operator.username} ({rental.assigned_operator.get_full_name()})")
    print(f"  User: {rental.user.get_full_name()}")
    print(f"  Status: {rental.status}")
    print(f"  Workflow State: {rental.workflow_state}")
    print(f"  Operator Status: {rental.operator_status}")
    print(f"  Dates: {rental.start_date} to {rental.end_date}")
    print()

print("="*70 + "\n")
