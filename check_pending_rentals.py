#!/usr/bin/env python
"""Check pending rentals that might need operator assignment"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Rental

print("=" * 80)
print("PENDING RENTALS NEEDING OPERATOR ASSIGNMENT")
print("=" * 80)

# Get pending rentals
pending = Rental.objects.filter(status='pending').select_related('machine', 'user').order_by('-created_at')
print(f"\nTotal PENDING rentals: {pending.count()}\n")

for rental in pending:
    print(f"Rental ID: {rental.id} | Machine: {rental.machine.name} | Customer: {rental.customer_display_name}")
    print(f"  Requires Operator: {rental.requires_operator_service}")
    print(f"  Payment Type: {rental.payment_type} | Method: {rental.payment_method}")
    print(f"  Payment Verified: {rental.payment_verified} | Status: {rental.payment_status}")
    print()

# Get approved rentals without operator
approved = Rental.objects.filter(
    status='approved',
    requires_operator_service=True,
    assigned_operator__isnull=True
).select_related('machine', 'user').order_by('-created_at')

print(f"\n{'=' * 80}")
print(f"APPROVED RENTALS NEEDING OPERATOR (requires_operator_service=True, no operator assigned)")
print("=" * 80)
print(f"\nTotal: {approved.count()}\n")

for rental in approved:
    payment_ready = (
        rental.payment_type == 'in_kind'
        or rental.payment_verified
        or rental.payment_status == 'paid'
    )
    print(f"Rental ID: {rental.id} | Machine: {rental.machine.name} | Customer: {rental.customer_display_name}")
    print(f"  Payment Type: {rental.payment_type} | Method: {rental.payment_method}")
    print(f"  Payment Verified: {rental.payment_verified} | Status: {rental.payment_status}")
    print(f"  Payment Ready for Assignment: {payment_ready}")
    print()

print("=" * 80)
