#!/usr/bin/env python
"""Check if old operator_management_views is still imported"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

# Now check the imports
from machines import urls

print("=" * 60)
print("URL IMPORT CHECK")
print("=" * 60)

# Check if operator_management_views is in the module
has_old_import = hasattr(urls, 'operator_management_views')

print(f"\n❌ OLD Import Active: {has_old_import}")

if has_old_import:
    print("\n⚠️  WARNING: operator_management_views is still imported!")
    print("   This means Django server has cached the old import.")
    print("   You MUST restart the Django server.")
else:
    print("\n✅ GOOD: operator_management_views is NOT imported")
    print("   The old system is properly disabled.")

# Check what operator-related modules ARE imported
operator_modules = [x for x in dir(urls) if 'operator' in x.lower()]
print(f"\n📋 Operator-related imports found:")
for mod in operator_modules:
    print(f"   - {mod}")

# Check URL patterns
print(f"\n📋 Total URL patterns: {len(urls.urlpatterns)}")

# Try to find any patterns that might match /machines/operators/
operator_patterns = []
for pattern in urls.urlpatterns:
    pattern_str = str(pattern.pattern)
    if 'operator' in pattern_str:
        operator_patterns.append(pattern_str)

print(f"\n📋 Operator-related URL patterns:")
for p in operator_patterns:
    print(f"   - {p}")

print("\n" + "=" * 60)
print("RECOMMENDATION")
print("=" * 60)

if has_old_import:
    print("\n🚨 ACTION REQUIRED:")
    print("   1. Stop Django server (Ctrl+C)")
    print("   2. Clear cache: Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force")
    print("   3. Restart: python manage.py runserver")
else:
    print("\n✅ System is ready!")
    print("   Use URL: http://127.0.0.1:8000/machines/operators/overview/")
    print("   (Make sure to include /overview/ at the end)")

print("\n")
