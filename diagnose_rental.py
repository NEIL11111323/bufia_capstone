#!/usr/bin/env python
"""Diagnose rental operator assignment issue"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 80)
print("RENTAL OPERATOR ASSIGNMENT DIAGNOSTIC")
print("=" * 80)

# Get recent rentals
recent_rentals = Rental.objects.select_related('machine', 'user').order_by('-created_at')[:5]

print(f"\nTotal rentals in database: {Rental.objects.count()}")
print(f"\nShowing last 5 rentals:\n")

for rental in recent_rentals:
    print(f"\n{'=' * 80}")
    print(f"Rental ID: {rental.id}")
    print(f"Machine: {rental.machine.name}")
    print(f"Customer: {rental.customer_display_name}")
    print(f"Status: {rental.status}")
    print(f"Workflow State: {rental.workflow_state}")
    print(f"Payment Type: {rental.payment_type}")
    print(f"Payment Method: {rental.payment_method}")
    print(f"Payment Verified: {rental.payment_verified}")
    print(f"Payment Status: {rental.payment_status}")
    print(f"Requires Operator Service: {rental.requires_operator_service}")
    print(f"Assigned Operator: {rental.assigned_operator}")
    
    # Check conditions for operator assignment
    print(f"\n--- Operator Assignment Conditions ---")
    payment_ready = (
        rental.payment_type == 'in_kind'
        or rental.payment_verified
        or rental.payment_status == 'paid'
    )
    can_assign = (
        rental.requires_operator_service
        and rental.status in ('approved', 'assigned')
        and payment_ready
    )
    
    print(f"✓ Requires operator service: {rental.requires_operator_service}")
    print(f"✓ Status is 'approved' or 'assigned': {rental.status in ('approved', 'assigned')} (current: {rental.status})")
    print(f"✓ Payment ready: {payment_ready}")
    print(f"  - Is in_kind: {rental.payment_type == 'in_kind'}")
    print(f"  - Payment verified: {rental.payment_verified}")
    print(f"  - Payment status is 'paid': {rental.payment_status == 'paid'}")
    print(f"\n→ CAN ASSIGN OPERATOR: {can_assign}")

# Check operators
print(f"\n\n{'=' * 80}")
print("AVAILABLE OPERATORS")
print("=" * 80)
operators = User.objects.filter(is_active=True, role=User.OPERATOR)
print(f"\nTotal active operators: {operators.count()}")
for op in operators:
    print(f"  - ID: {op.id}, Username: {op.username}, Name: {op.get_full_name()}")

print("\n" + "=" * 80)
