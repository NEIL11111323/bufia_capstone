#!/usr/bin/env python
"""
Diagnostic script to verify operator template configuration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 80)
print("OPERATOR TEMPLATE DIAGNOSTIC")
print("=" * 80)

# Check operator users
print("\n1. OPERATOR USERS:")
operators = User.objects.filter(role=User.OPERATOR, is_active=True)
for op in operators:
    print(f"   - {op.username} ({op.email}) - Role: {op.role}")
    print(f"     is_staff: {op.is_staff}, is_superuser: {op.is_superuser}")

# Check template files
print("\n2. OPERATOR TEMPLATE FILES:")
template_dir = "templates/machines/operator"
if os.path.exists(template_dir):
    files = os.listdir(template_dir)
    for f in sorted(files):
        if f.endswith('.html'):
            filepath = os.path.join(template_dir, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                first_line = file.readline().strip()
                print(f"   ✓ {f}")
                print(f"     Extends: {first_line}")
else:
    print(f"   ✗ Directory not found: {template_dir}")

# Check base.html operator section
print("\n3. BASE.HTML OPERATOR NAVIGATION:")
base_path = "templates/base.html"
if os.path.exists(base_path):
    with open(base_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "CLEAN OPERATOR NAVIGATION" in content:
            print("   ✓ Operator navigation section found")
        else:
            print("   ✗ Operator navigation section NOT found")
        
        if "operator_dashboard" in content:
            print("   ✓ operator_dashboard URL found")
        else:
            print("   ✗ operator_dashboard URL NOT found")
        
        if "operator_all_jobs" in content:
            print("   ✓ operator_all_jobs URL found")
        else:
            print("   ✗ operator_all_jobs URL NOT found")
else:
    print(f"   ✗ File not found: {base_path}")

# Check rentals assigned to operators
print("\n4. OPERATOR JOB ASSIGNMENTS:")
for op in operators:
    job_count = Rental.objects.filter(assigned_operator=op).count()
    active_count = Rental.objects.filter(
        assigned_operator=op
    ).exclude(status__in=['completed', 'cancelled', 'rejected']).count()
    print(f"   - {op.username}: {job_count} total jobs, {active_count} active")

# Check URL patterns
print("\n5. URL PATTERNS:")
from django.urls import reverse
try:
    dashboard_url = reverse('machines:operator_dashboard')
    print(f"   ✓ operator_dashboard: {dashboard_url}")
except:
    print("   ✗ operator_dashboard URL not found")

try:
    all_jobs_url = reverse('machines:operator_all_jobs')
    print(f"   ✓ operator_all_jobs: {all_jobs_url}")
except:
    print("   ✗ operator_all_jobs URL not found")

# Check views
print("\n6. OPERATOR VIEWS:")
from machines import operator_views
views_to_check = [
    'operator_dashboard',
    'operator_all_jobs',
    'operator_ongoing_jobs',
    'operator_awaiting_harvest',
    'operator_completed_jobs',
    'operator_in_kind_payments',
    'operator_view_machines',
]
for view_name in views_to_check:
    if hasattr(operator_views, view_name):
        print(f"   ✓ {view_name} exists")
    else:
        print(f"   ✗ {view_name} NOT found")

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
print("\nIf all checks pass, the issue is likely browser cache.")
print("User should:")
print("1. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)")
print("2. Clear all browser data for the site")
print("3. Try incognito/private mode")
print("4. Try a different browser")
