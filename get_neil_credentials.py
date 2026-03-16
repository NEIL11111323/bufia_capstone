#!/usr/bin/env python
"""Get Neil's login credentials"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("NEIL'S LOGIN CREDENTIALS")
print("=" * 70)

try:
    neil = User.objects.get(username='Neil')
    
    print(f"\n✅ Account Found:")
    print(f"\n   Username: {neil.username}")
    print(f"   Full Name: {neil.get_full_name()}")
    print(f"   Email: {neil.email or 'Not set'}")
    print(f"   Role: {neil.role}")
    print(f"   Is Active: {neil.is_active}")
    print(f"   Is Staff: {neil.is_staff}")
    
    print(f"\n" + "=" * 70)
    print("LOGIN INFORMATION")
    print("=" * 70)
    print(f"\n   Username: Neil")
    print(f"   Password: [Cannot retrieve - passwords are hashed]")
    
    print(f"\n" + "=" * 70)
    print("IMPORTANT NOTE")
    print("=" * 70)
    print("""
Django stores passwords as secure hashes, not plain text.
This is a security feature - passwords cannot be retrieved.

If you don't know Neil's password, you have 2 options:

Option 1: Reset Neil's password
---------------------------------
Run this command in Django shell:

    python manage.py shell

Then run:

    from django.contrib.auth import get_user_model
    User = get_user_model()
    neil = User.objects.get(username='Neil')
    neil.set_password('newpassword123')
    neil.save()
    print("Password updated!")

Option 2: Create a new password reset script
---------------------------------------------
I can create a script to reset Neil's password to a known value.
""")
    
except User.DoesNotExist:
    print("\n❌ User 'Neil' not found")

print("=" * 70)
