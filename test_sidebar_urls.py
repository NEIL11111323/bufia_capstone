#!/usr/bin/env python
"""
Test script to verify all sidebar navigation URLs are valid
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model

User = get_user_model()

# List of all URLs used in the sidebar navigation
urls_to_test = [
    # Top Navigation
    ('home', [], {}),
    ('profile', [], {}),
    ('account_email', [], {}),
    ('account_logout', [], {}),
    ('account_login', [], {}),
    
    # Sidebar - Main
    ('dashboard', [], {}),
    
    # Sidebar - Equipment & Scheduling
    ('machines:machine_list', [], {}),
    ('machines:ricemill_appointment_list', [], {}),
    ('machines:maintenance_list', [], {}),
    ('machines:rental_list', [], {}),
    
    # Sidebar - Services
    ('irrigation:irrigation_request_list', [], {}),
    
    # Sidebar - Reports
    ('reports:user_activity_report', [], {}),
    ('reports:machine_usage_report', [], {}),
    ('reports:rice_mill_scheduling_report', [], {}),
    ('general_reports:dashboard', [], {}),
    
    # Sidebar - Administration
    ('user_list', [], {}),
    ('notifications:send_notification', [], {}),
    ('activity_logs:logs', [], {}),
    ('admin:index', [], {}),
    
    # Notifications (requires ID)
    ('notifications:user_notifications', [], {}),
]

print("=" * 70)
print("SIDEBAR URL VALIDATION TEST")
print("=" * 70)
print()

errors = []
success = []

for url_name, args, kwargs in urls_to_test:
    try:
        url = reverse(url_name, args=args, kwargs=kwargs)
        success.append((url_name, url))
        print(f"✅ {url_name:50} -> {url}")
    except NoReverseMatch as e:
        errors.append((url_name, str(e)))
        print(f"❌ {url_name:50} -> ERROR: {e}")
    except Exception as e:
        errors.append((url_name, str(e)))
        print(f"❌ {url_name:50} -> ERROR: {e}")

print()
print("=" * 70)
print(f"RESULTS: {len(success)} passed, {len(errors)} failed")
print("=" * 70)

if errors:
    print()
    print("ERRORS FOUND:")
    for url_name, error in errors:
        print(f"  - {url_name}: {error}")
    exit(1)
else:
    print()
    print("✅ All sidebar URLs are valid!")
    exit(0)
