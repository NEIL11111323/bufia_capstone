"""
Test script to verify IN-KIND rice confirmation workflow
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia_project.settings')
django.setup()

from machines.models import Rental
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("IN-KIND RICE CONFIRMATION WORKFLOW TEST")
print("=" * 70)

# Find IN-KIND rentals waiting for delivery
in_kind_rentals = Rental.objects.filter(
    payment_type='in_kind',
    settlement_status='waiting_for_delivery'
).select_related('machine', 'user', 'assigned_operator')

print(f"\n✅ Found {in_kind_rentals.count()} IN-KIND rental(s) waiting for rice delivery\n")

for rental in in_kind_rentals:
    print(f"Rental ID: {rental.id}")
    print(f"  Machine: {rental.machine.name}")
    print(f"  Renter: {rental.user.get_full_name()}")
    print(f"  Status: {rental.get_status_display()}")
    print(f"  Settlement Status: {rental.get_settlement_status_display()}")
    print(f"  Total Harvest: {rental.total_harvest_sacks or 'Not reported'} sacks")
    print(f"  BUFIA Share Required: {rental.organization_share_required or 'Not calculated'} sacks")
    print(f"  Rice Delivered: {rental.organization_share_received or 0} sacks")
    if rental.assigned_operator:
        print(f"  Operator: {rental.assigned_operator.get_full_name()}")
    print(f"  Admin Approval URL: /machines/admin/rental/{rental.id}/approve/")
    print()

if in_kind_rentals.count() == 0:
    print("ℹ️  No IN-KIND rentals currently waiting for rice delivery")
    print("\nChecking all IN-KIND rentals:")
    all_in_kind = Rental.objects.filter(payment_type='in_kind').select_related('machine', 'user')
    for rental in all_in_kind[:5]:
        print(f"\n  Rental #{rental.id} - {rental.machine.name}")
        print(f"    Status: {rental.get_status_display()}")
        print(f"    Settlement: {rental.get_settlement_status_display()}")
        print(f"    BUFIA Share Required: {rental.organization_share_required or 'N/A'}")

print("\n" + "=" * 70)
print("WORKFLOW STEPS FOR ADMIN:")
print("=" * 70)
print("""
1. Operator submits harvest report with total sacks
2. System calculates BUFIA share based on rice-share ratio
3. Settlement status changes to 'WAITING FOR DELIVERY'
4. Admin sees rice confirmation form in approval page
5. Admin confirms physical rice delivery
6. System marks settlement as PAID and completes rental
""")
print("=" * 70)
