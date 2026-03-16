#!/usr/bin/env python
"""Check Neil's setup and available rentals"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 70)
print("NEIL OPERATOR STATUS & AVAILABLE RENTALS")
print("=" * 70)

# Check Neil
for username in ['neil', 'Neil']:
    try:
        neil = User.objects.get(username=username)
        print(f"\n✅ Neil's Account:")
        print(f"   Username: {neil.username}")
        print(f"   Name: {neil.get_full_name() or 'Not set'}")
        print(f"   Role: {neil.role}")
        print(f"   Is Staff: {neil.is_staff}")
        print(f"   Is Active: {neil.is_active}")
        
        # Check assignments
        assignments = Rental.objects.filter(assigned_operator=neil)
        print(f"\n📋 Neil's Current Assignments: {assignments.count()}")
        
        if assignments.exists():
            for rental in assignments:
                print(f"   - Rental #{rental.id}: {rental.machine.name} - {rental.status}")
        else:
            print(f"   No assignments yet")
        
        break
    except User.DoesNotExist:
        continue

print(f"\n" + "=" * 70)
print("AVAILABLE RENTALS TO ASSIGN")
print("=" * 70)

# Show approved rentals without operators
unassigned = Rental.objects.filter(
    assigned_operator__isnull=True,
    status='approved'
).select_related('machine', 'user')

print(f"\n✅ Approved rentals without operators: {unassigned.count()}")

if unassigned.exists():
    for rental in unassigned[:5]:
        print(f"\n   Rental #{rental.id}")
        print(f"   Machine: {rental.machine.name}")
        print(f"   Member: {rental.user.get_full_name()}")
        print(f"   Status: {rental.status}")
        print(f"   Start Date: {rental.start_date}")
        print(f"   URL: /machines/admin/rental/{rental.id}/approve/")
else:
    print(f"\n   No unassigned approved rentals")
    
    # Show pending rentals
    pending = Rental.objects.filter(status='pending').count()
    print(f"\n   💡 There are {pending} pending rental(s) that need approval first")

# Show all rentals summary
print(f"\n" + "=" * 70)
print("ALL RENTALS SUMMARY")
print("=" * 70)

from django.db.models import Count

status_counts = Rental.objects.values('status').annotate(count=Count('id'))
print(f"\nRentals by status:")
for item in status_counts:
    print(f"   {item['status']}: {item['count']}")

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
1. Restart Django server (if not already done)
2. Login as admin at: http://127.0.0.1:8000/admin/
3. Go to: http://127.0.0.1:8000/machines/admin/dashboard/
4. Find a rental to approve (or approve a pending one)
5. On the approval page, select 'Neil' from operator dropdown
6. Click 'Assign Operator' button
7. Login as Neil and check: http://127.0.0.1:8000/machines/operator/dashboard/
""")
print("=" * 70)
