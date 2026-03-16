#!/usr/bin/env python
"""
Verify the operator interface fix is complete
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "=" * 80)
print("OPERATOR INTERFACE FIX VERIFICATION")
print("=" * 80)

# Check micho@gmail.com user
print("\n1. CHECKING MICHO@GMAIL.COM USER:")
try:
    user = User.objects.get(email='micho@gmail.com')
    print(f"   ✓ User found: {user.username}")
    print(f"   ✓ Role: {user.role}")
    print(f"   ✓ is_staff: {user.is_staff}")
    print(f"   ✓ is_superuser: {user.is_superuser}")
    
    if user.role == 'operator':
        print("   ✅ CORRECT: User has operator role")
    else:
        print(f"   ❌ WRONG: User role is '{user.role}', should be 'operator'")
except User.DoesNotExist:
    print("   ❌ User not found!")

# Check base.html for correct role check
print("\n2. CHECKING BASE.HTML TEMPLATE:")
base_path = "templates/base.html"
with open(base_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
    if "{% if user.role == 'operator' %}" in content:
        print("   ✅ CORRECT: Using role-based check")
    elif "{% if user.is_staff and not user.is_superuser %}" in content:
        print("   ❌ WRONG: Still using is_staff check")
    else:
        print("   ⚠️  WARNING: Could not find operator check")
    
    if "CACHE BUSTER: v2.2" in content:
        print("   ✅ CORRECT: Cache buster updated to v2.2")
    else:
        print("   ⚠️  WARNING: Cache buster not updated")

# Check operator templates
print("\n3. CHECKING OPERATOR TEMPLATES:")
template_dir = "templates/machines/operator"
templates = [
    'operator_dashboard_clean.html',
    'operator_all_jobs.html',
    'operator_job_list.html',
    'operator_in_kind_payments.html',
    'operator_view_machines.html',
]

for template in templates:
    filepath = os.path.join(template_dir, template)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if "{% extends 'base.html' %}" in first_line:
                print(f"   ✅ {template}: Extends base.html")
            else:
                print(f"   ❌ {template}: Does NOT extend base.html")
    else:
        print(f"   ❌ {template}: File not found")

# Check for card-based design in templates
print("\n4. CHECKING FOR CARD-BASED DESIGN:")
dashboard_path = "templates/machines/operator/operator_dashboard_clean.html"
with open(dashboard_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
    if "stats-grid" in content:
        print("   ✅ Statistics grid found")
    else:
        print("   ❌ Statistics grid NOT found")
    
    if "job-card" in content:
        print("   ✅ Job cards found")
    else:
        print("   ❌ Job cards NOT found")
    
    if "stat-card" in content:
        print("   ✅ Stat cards found")
    else:
        print("   ❌ Stat cards NOT found")

all_jobs_path = "templates/machines/operator/operator_all_jobs.html"
with open(all_jobs_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
    if "job-card" in content:
        print("   ✅ All Jobs uses card design")
    else:
        print("   ❌ All Jobs does NOT use card design")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

print("\n📋 NEXT STEPS FOR USER:")
print("\n1. STOP Django server:")
print("   Press Ctrl+C in terminal")
print("\n2. START Django server:")
print("   python manage.py runserver")
print("\n3. CLEAR browser cache:")
print("   Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)")
print("\n4. TEST in incognito mode FIRST:")
print("   - Open incognito window (Ctrl+Shift+N)")
print("   - Go to http://127.0.0.1:8000/")
print("   - Log in as: micho@gmail.com / micho123")
print("   - Navigate to operator dashboard")
print("   - You should see CARD-BASED design with green header")
print("\n5. If working in incognito:")
print("   - Close incognito")
print("   - Clear ALL browser data in regular browser")
print("   - Restart browser")
print("   - Log in again")
print("\n" + "=" * 80)
