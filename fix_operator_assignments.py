#!/usr/bin/env python
"""Fix and verify operator assignments"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 60)
print("OPERATOR ASSIGNMENT FIX & VERIFICATION")
print("=" * 60)

# List all operators
operators = User.objects.filter(role=User.OPERATOR, is_active=True)
print(f"\n📋 Active Operators: {operators.count()}")
for op in operators:
    print(f"   - {op.username} ({op.get_full_name()}) [ID: {op.id}]")

# Check neil specifically
try:
    neil = User.objects.get(username='neil')
    print(f"\n✅ Found Neil:")
    print(f"   ID: {neil.id}")
    print(f"   Name: {neil.get_full_name()}")
    print(f"   Role: {neil.role}")
    print(f"   Is Operator: {neil.role == User.OPERATOR}")
    
    # Check assignments
    assignments = Rental.objects.filter(assigned_operator=neil)
    print(f"\n📋 Neil's Assignments: {assignments.count()}")
    
    if assignments.exists():
        for rental in assignments:
            print(f"\n   Rental #{rental.id}:")
            print(f"   - Machine: {rental.machine.name}")
            print(f"   - Member: {rental.user.get_full_name()}")
            print(f"   - Status: {rental.status}")
            print(f"   - Operator Status: {rental.operator_status}")
            print(f"   - Start Date: {rental.start_date}")
    else:
        print("   ⚠️  No assignments found")
        
        # Check if there are pending rentals that could be assigned
        print("\n📋 Checking unassigned rentals...")
        unassigned = Rental.objects.filter(
            assigned_operator__isnull=True,
            status='approved'
        )
        print(f"   Unassigned approved rentals: {unassigned.count()}")
        
        if unassigned.exists():
            print("\n   Recent unassigned rentals:")
            for rental in unassigned[:5]:
                print(f"   - Rental #{rental.id}: {rental.machine.name} for {rental.user.get_full_name()}")
                
except User.DoesNotExist:
    print("\n❌ Operator 'neil' not found")
    print("   Available usernames:")
    for user in User.objects.all()[:10]:
        print(f"   - {user.username}")

# Summary of all assignments
print("\n" + "=" * 60)
print("ASSIGNMENT SUMMARY")
print("=" * 60)

all_assigned = Rental.objects.exclude(assigned_operator__isnull=True)
print(f"\nTotal rentals with operators assigned: {all_assigned.count()}")

if all_assigned.exists():
    print("\nAssignments by operator:")
    for op in operators:
        count = Rental.objects.filter(assigned_operator=op).count()
        if count > 0:
            print(f"   - {op.username}: {count} rental(s)")

print("\n" + "=" * 60)
