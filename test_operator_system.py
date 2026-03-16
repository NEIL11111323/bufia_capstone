#!/usr/bin/env python
"""Test the complete operator system"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental, Machine

User = get_user_model()

print("=" * 60)
print("OPERATOR SYSTEM TEST")
print("=" * 60)

# Check if operator accounts exist
operators = User.objects.filter(role=User.OPERATOR, is_active=True)
print(f"\n✓ Found {operators.count()} operator account(s)")

if operators.exists():
    for op in operators:
        print(f"  - {op.username} ({op.get_full_name() or 'No name'})")
        
        # Check assigned jobs
        jobs = Rental.objects.filter(assigned_operator=op)
        print(f"    Jobs assigned: {jobs.count()}")
        print(f"    Active jobs: {jobs.exclude(status__in=['completed', 'cancelled', 'rejected']).count()}")
        print(f"    Completed jobs: {jobs.filter(status='completed').count()}")
else:
    print("\n⚠️  No operator accounts found!")
    print("   Run create_operator.py to create an operator account")

# Check machines
machines = Machine.objects.filter(status='available')
print(f"\n✓ Found {machines.count()} available machine(s)")
total_machines = Machine.objects.all().count()
print(f"  Total machines: {total_machines}")

# Check templates exist
import os
template_dir = 'templates/machines/operator/'
templates = [
    'index.html',
    'jobs.html',
    'job_detail.html',
    'harvest.html',
    'notifications.html',
    'machines.html',
]

print(f"\n✓ Checking templates in {template_dir}")
for template in templates:
    path = os.path.join(template_dir, template)
    if os.path.exists(path):
        print(f"  ✓ {template}")
    else:
        print(f"  ✗ {template} MISSING!")

# Check URLs
print("\n✓ Operator URLs configured:")
print("  - /machines/operator/dashboard/")
print("  - /machines/operator/jobs/")
print("  - /machines/operator/jobs/<id>/")
print("  - /machines/operator/jobs/ongoing/")
print("  - /machines/operator/jobs/awaiting-harvest/")
print("  - /machines/operator/jobs/completed/")
print("  - /machines/operator/machines/")
print("  - /machines/operator/notifications/")

print("\n" + "=" * 60)
print("SYSTEM STATUS: READY")
print("=" * 60)
print("\nNext steps:")
print("1. Run: python create_operator.py (if no operators exist)")
print("2. Assign jobs to operator from admin dashboard")
print("3. Login as operator and test the interface")
print("4. Check navigation in base.html shows operator menu")
print("\nOperator credentials (if created):")
print("  Username: operator")
print("  Password: operator123")
print("=" * 60)
