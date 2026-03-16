#!/usr/bin/env python
"""
Force Django to reload all operator templates
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')

import django
django.setup()

from django.core.management import call_command
from django.template.loader import get_template
from django.conf import settings

print("=" * 70)
print("FORCING TEMPLATE RELOAD")
print("=" * 70)

# Clear template cache
if hasattr(settings, 'TEMPLATES'):
    for template_config in settings.TEMPLATES:
        if 'OPTIONS' in template_config:
            if 'loaders' in template_config['OPTIONS']:
                print("\n✅ Template caching detected")

# Test load all operator templates
templates = [
    'machines/operator/operator_dashboard_clean.html',
    'machines/operator/operator_all_jobs.html',
    'machines/operator/operator_job_list.html',
    'machines/operator/operator_in_kind_payments.html',
    'machines/operator/operator_view_machines.html',
    'machines/operator/operator_notifications.html',
    'machines/operator/operator_decision_form.html',
]

print("\n" + "=" * 70)
print("VERIFYING TEMPLATES")
print("=" * 70)

for template_name in templates:
    try:
        template = get_template(template_name)
        # Check if it extends base.html
        template_path = f'templates/{template_name}'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if 'base.html' in first_line:
                    print(f"\n✅ {template_name}")
                    print(f"   Extends: base.html")
                else:
                    print(f"\n❌ {template_name}")
                    print(f"   First line: {first_line.strip()}")
    except Exception as e:
        print(f"\n❌ {template_name}")
        print(f"   Error: {e}")

print("\n" + "=" * 70)
print("RESTART DJANGO SERVER")
print("=" * 70)
print("\nTo see changes:")
print("1. Stop the Django server (Ctrl+C)")
print("2. Restart: python manage.py runserver")
print("3. Clear browser cache: Ctrl + Shift + R")
print("4. Log in again as operator")
print("=" * 70)
