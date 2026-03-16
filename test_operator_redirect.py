#!/usr/bin/env python
"""Test that old operator URL redirects to new one"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("OPERATOR URL REDIRECT TEST")
print("=" * 60)

# Create test client
client = Client()

# Get or create superuser for testing
try:
    superuser = User.objects.filter(is_superuser=True).first()
    if not superuser:
        print("\n⚠️  No superuser found. Creating test superuser...")
        superuser = User.objects.create_superuser(
            username='testadmin',
            email='test@test.com',
            password='testpass123'
        )
        print("✅ Test superuser created")
    
    # Login
    client.force_login(superuser)
    print(f"\n✅ Logged in as: {superuser.username}")
    
    # Test old URL
    print("\n📋 Testing old URL: /machines/operators/")
    response = client.get('/machines/operators/', follow=False)
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 302:
        print(f"   ✅ REDIRECT detected")
        print(f"   Redirect Location: {response.url}")
        
        if 'operators/overview' in response.url:
            print("\n✅ SUCCESS! Old URL redirects to new operator overview")
        else:
            print(f"\n❌ ERROR: Redirects to wrong location: {response.url}")
    elif response.status_code == 200:
        print("\n❌ ERROR: No redirect - page loaded directly")
        print("   This means the redirect is not working")
    else:
        print(f"\n❌ ERROR: Unexpected status code: {response.status_code}")
    
    # Test new URL
    print("\n📋 Testing new URL: /machines/operators/overview/")
    response = client.get('/machines/operators/overview/')
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ New URL works correctly")
    else:
        print(f"   ❌ ERROR: Status code {response.status_code}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
