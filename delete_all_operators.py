#!/usr/bin/env python
"""
Delete all operator accounts and their data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 80)
print("DELETING ALL OPERATOR ACCOUNTS")
print("=" * 80)

# Find all operator users
operators = User.objects.filter(role=User.OPERATOR)
print(f"\nFound {operators.count()} operator accounts:")
for op in operators:
    print(f"  - {op.username} ({op.email})")

# Unassign all rentals from operators
rentals_with_operators = Rental.objects.filter(assigned_operator__isnull=False)
rental_count = rentals_with_operators.count()
print(f"\nFound {rental_count} rentals assigned to operators")

if rental_count > 0:
    rentals_with_operators.update(
        assigned_operator=None,
        operator_status='unassigned',
        operator_notes='',
        operator_last_update_at=None,
        operator_reported_at=None
    )
    print(f"✅ Unassigned all {rental_count} rentals from operators")

# Delete operator accounts
if operators.exists():
    operator_count = operators.count()
    operators.delete()
    print(f"✅ Deleted {operator_count} operator accounts")
else:
    print("No operator accounts to delete")

print("\n" + "=" * 80)
print("CLEANUP COMPLETE")
print("=" * 80)
print("\nAll operator accounts and assignments have been removed.")
print("The operator dashboard is now disabled.")
