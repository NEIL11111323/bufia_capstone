"""
Test script to verify all report URLs are accessible
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

# Create test client
client = Client()

# Get or create admin user
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    print("❌ No admin user found. Please create one first.")
    exit(1)

print(f"✓ Testing with admin user: {admin_user.username}")

# Login
client.force_login(admin_user)

# Test all report URLs
report_urls = [
    ('reports:rental_report', 'Rental Transactions Report'),
    ('reports:harvest_report', 'Harvest & BUFIA Share Report'),
    ('reports:financial_summary', 'Financial Summary Report'),
    ('reports:membership_report', 'Membership Status Report'),
    ('reports:machine_usage_report', 'Machine Usage Report'),
]

print("\n" + "="*60)
print("TESTING REPORT URLS")
print("="*60 + "\n")

all_passed = True

for url_name, description in report_urls:
    try:
        url = reverse(url_name)
        response = client.get(url)
        
        if response.status_code == 200:
            print(f"✓ {description}")
            print(f"  URL: {url}")
            print(f"  Status: {response.status_code} OK\n")
        else:
            print(f"❌ {description}")
            print(f"  URL: {url}")
            print(f"  Status: {response.status_code}")
            print(f"  Error: Unexpected status code\n")
            all_passed = False
            
    except Exception as e:
        print(f"❌ {description}")
        print(f"  Error: {str(e)}\n")
        all_passed = False

print("="*60)
if all_passed:
    print("✓ ALL REPORTS PASSED")
else:
    print("❌ SOME REPORTS FAILED")
print("="*60)
