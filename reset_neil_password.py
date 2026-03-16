#!/usr/bin/env python
"""Reset Neil's password to a known value"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("RESET NEIL'S PASSWORD")
print("=" * 70)

try:
    neil = User.objects.get(username='Neil')
    
    # Set new password
    new_password = 'neil123'
    neil.set_password(new_password)
    neil.save()
    
    print(f"\n✅ Password Reset Successful!")
    print(f"\n" + "=" * 70)
    print("NEW LOGIN CREDENTIALS")
    print("=" * 70)
    print(f"\n   Username: Neil")
    print(f"   Password: {new_password}")
    print(f"\n   Full Name: {neil.get_full_name()}")
    print(f"   Role: {neil.role}")
    print(f"\n" + "=" * 70)
    print("LOGIN URL")
    print("=" * 70)
    print(f"\n   http://127.0.0.1:8000/login/")
    print(f"\n" + "=" * 70)
    
except User.DoesNotExist:
    print("\n❌ User 'Neil' not found")

print("=" * 70)
