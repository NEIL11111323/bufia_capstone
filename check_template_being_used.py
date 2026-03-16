#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines import operator_views
import inspect

print("=" * 80)
print("CHECKING WHICH TEMPLATE IS BEING USED")
print("=" * 80)

# Check operator_all_jobs view
print("\n1. OPERATOR_ALL_JOBS VIEW:")
source = inspect.getsource(operator_views.operator_all_jobs)
print(source)

# Check if template file exists
template_path = "templates/machines/operator/operator_all_jobs.html"
print(f"\n2. TEMPLATE FILE: {template_path}")
if os.path.exists(template_path):
    print("   ✅ File exists")
    with open(template_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"   Total lines: {len(lines)}")
        print(f"   First line: {lines[0].strip()}")
        
        # Check for table
        has_table = any('<table' in line for line in lines)
        has_cards = any('job-card' in line for line in lines)
        
        if has_table:
            print("   ❌ WARNING: Template contains <table> elements")
        else:
            print("   ✅ No table elements found")
        
        if has_cards:
            print("   ✅ Template uses card-based design")
        else:
            print("   ❌ WARNING: No card design found")
else:
    print("   ❌ File NOT found")

print("\n" + "=" * 80)
print("If template is correct but browser shows table:")
print("  → This is 100% a browser cache issue")
print("  → Clear ALL browser data and test in incognito")
print("=" * 80)
