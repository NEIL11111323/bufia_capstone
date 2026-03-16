#!/usr/bin/env python
"""Verify Neil operator setup and assignments"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 70)
print("NEIL OPERATOR VERIFICATION")
print("=" * 70)

# Find neil
try:
    neil = User.objects.get(username='neil')
    print(f"\n✅ Found Neil:")
    print(f"   Username: {neil.username}")
    print(f"   Name: {neil.get_full_name() or 'Not set'}")
    print(f"   Email: {neil.email or 'Not set'}")
    print(f"   Role: {neil.role}")
    print(f"   Is Staff: {neil.is_staff}")
    print(f"   Is Active: {neil.is_active}")
    print(f"   Is Superuser: {neil.is_superuser}")
    
    # Check if role is correct
    if neil.role == User.OPERATOR:
        print(f"\n✅ Neil has OPERATOR role")
    else:
        print(f"\n❌ Neil's role is '{neil.role}' but should be 'operator'")
        print(f"   Fix: Set neil.role = User.OPERATOR")
    
    # Check assignments
    print(f"\n📋 Checking Neil's Job Assignments:")
    assignments = Rental.objects.filter(assigned_operator=neil).select_related('machine', 'user')
    
    print(f"   Total assignments: {assignments.count()}")
    
    if assignments.exists():
        print(f"\n   Assigned Jobs:")
        for i, rental in enumerate(assignments, 1):
            print(f"\n   {i}. Rental #{rental.id}")
            print(f"      Machine: {rental.machine.name}")
            print(f"      Member: {rental.user.get_full_name()}")
            print(f"      Status: {rental.status}")
            print(f"      Operator Status: {rental.operator_status}")
            print(f"      Start Date: {rental.start_date}")
            print(f"      Created: {rental.created_at.strftime('%Y-%m-%d %H:%M')}")
    else:
        print(f"\n   ⚠️  No jobs assigned to Neil yet")
        
        # Show how to assign
        print(f"\n   📝 To assign a job to Neil:")
        print(f"      1. Login as admin")
        print(f"      2. Go to: /machines/admin/dashboard/")
        print(f"      3. Find a rental to approve")
        print(f"      4. In the approval page, select 'neil' from operator dropdown")
        print(f"      5. Click 'Assign Operator'")
        
        # Check if there are any unassigned rentals
        unassigned = Rental.objects.filter(
            assigned_operator__isnull=True,
            status='approved'
        ).count()
        
        if unassigned > 0:
            print(f"\n   💡 There are {unassigned} approved rental(s) without operators")
            print(f"      You can assign Neil to one of these")

except User.DoesNotExist:
    print(f"\n❌ User 'neil' not found in database")
    print(f"\n   Available users:")
    for user in User.objects.all()[:10]:
        print(f"   - {user.username} (role: {user.role})")
    print(f"\n   To create Neil as operator, run:")
    print(f"   python create_operator.py")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

# Show all operators
operators = User.objects.filter(role=User.OPERATOR, is_active=True)
print(f"\nActive Operators: {operators.count()}")
for op in operators:
    job_count = Rental.objects.filter(assigned_operator=op).count()
    print(f"   - {op.username}: {job_count} job(s)")

print("\n" + "=" * 70)
