#!/usr/bin/env python
"""Check Neil operator's assignments"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 60)
print("NEIL OPERATOR ASSIGNMENT CHECK")
print("=" * 60)

# Find neil operator
try:
    neil = User.objects.get(username='neil')
    print(f"\n✅ Found operator: {neil.username}")
    print(f"   Name: {neil.get_full_name()}")
    print(f"   Role: {neil.role}")
    print(f"   Is Staff: {neil.is_staff}")
    print(f"   Is Active: {neil.is_active}")
except User.DoesNotExist:
    print("\n❌ Operator 'neil' not found")
    print("\nAvailable operators:")
    operators = User.objects.filter(role=User.OPERATOR)
    for op in operators:
        print(f"   - {op.username} ({op.get_full_name()})")
    sys.exit(1)

# Check assignments
print(f"\n📋 Checking assignments for {neil.username}...")

all_rentals = Rental.objects.filter(assigned_operator=neil)
print(f"\nTotal rentals assigned: {all_rentals.count()}")

if all_rentals.exists():
    print("\nRental Details:")
    for rental in all_rentals:
        print(f"\n  Rental ID: {rental.id}")
        print(f"  Machine: {rental.machine.name}")
        print(f"  Member: {rental.user.get_full_name()}")
        print(f"  Status: {rental.status}")
        print(f"  Operator Status: {rental.operator_status}")
        print(f"  Start Date: {rental.start_date}")
        print(f"  Created: {rental.created_at}")
else:
    print("\n⚠️  No rentals assigned to this operator")
    
    # Check if there are any rentals with assigned_operator set
    print("\n📋 Checking all rentals with operators assigned...")
    rentals_with_operators = Rental.objects.exclude(assigned_operator__isnull=True)
    print(f"Total rentals with operators: {rentals_with_operators.count()}")
    
    if rentals_with_operators.exists():
        print("\nOther operator assignments:")
        for rental in rentals_with_operators[:5]:
            print(f"  - Rental #{rental.id}: {rental.machine.name} → {rental.assigned_operator.username}")

print("\n" + "=" * 60)
