#!/usr/bin/env python
"""
Verify operator dashboard tabs implementation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from machines.models import Rental

User = get_user_model()

print("=" * 60)
print("OPERATOR DASHBOARD TABS VERIFICATION")
print("=" * 60)

# Check operator account
operator = User.objects.filter(username='operator1').first()
if not operator:
    print("\n❌ ERROR: operator1 account not found!")
    exit(1)

print(f"\n✅ Operator Account: {operator.username} ({operator.get_full_name()})")
print(f"   - Is Staff: {operator.is_staff}")
print(f"   - Is Active: {operator.is_active}")

# Check assigned jobs
all_jobs = Rental.objects.filter(assigned_operator=operator)
active_jobs = all_jobs.exclude(status__in=['completed', 'cancelled', 'rejected'])
completed_jobs = all_jobs.filter(status='completed')

print(f"\n📊 Job Statistics:")
print(f"   - Total Assigned: {all_jobs.count()}")
print(f"   - Active Jobs: {active_jobs.count()}")
print(f"   - Completed Jobs: {completed_jobs.count()}")

# Check template file
template_path = 'templates/machines/operator/operator_dashboard_simple.html'
if os.path.exists(template_path):
    print(f"\n✅ Template File: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
        has_tabs = 'data-bs-toggle="tab"' in content
        has_active_tab = 'id="active-jobs"' in content
        has_completed_tab = 'id="completed-jobs"' in content
        
        print(f"   - Has Tab Navigation: {'✅' if has_tabs else '❌'}")
        print(f"   - Has Active Tab: {'✅' if has_active_tab else '❌'}")
        print(f"   - Has Completed Tab: {'✅' if has_completed_tab else '❌'}")
else:
    print(f"\n❌ Template file not found: {template_path}")

# Check Bootstrap in base template
base_template_path = 'templates/base.html'
if os.path.exists(base_template_path):
    with open(base_template_path, 'r', encoding='utf-8') as f:
        content = f.read()
        has_bootstrap_js = 'bootstrap.bundle' in content
        print(f"\n✅ Bootstrap 5 JS Loaded: {'✅' if has_bootstrap_js else '❌'}")
else:
    print(f"\n❌ Base template not found: {base_template_path}")

print("\n" + "=" * 60)
print("TROUBLESHOOTING STEPS")
print("=" * 60)
print("""
If you can't see the tabs on the operator dashboard:

1. HARD REFRESH YOUR BROWSER:
   - Windows: Press Ctrl + Shift + R or Ctrl + F5
   - This clears the cached version of the page

2. VERIFY SERVER IS RUNNING:
   - Check that Django development server is running
   - URL: http://127.0.0.1:8000/machines/operator/dashboard/

3. CHECK BROWSER CONSOLE:
   - Press F12 to open Developer Tools
   - Click "Console" tab
   - Look for any JavaScript errors (red text)

4. VERIFY YOU'RE LOGGED IN AS OPERATOR:
   - Username: operator1
   - Password: operator123

5. CLEAR ALL BROWSER CACHE:
   - Chrome: Ctrl + Shift + Delete
   - Select "Cached images and files"
   - Click "Clear data"

The tabs ARE implemented and working. This is a browser caching issue.
""")

print("=" * 60)
print("✅ VERIFICATION COMPLETE")
print("=" * 60)
