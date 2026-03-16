#!/usr/bin/env python
"""
Script to list all operator accounts in the system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Get all operators (staff but not superuser)
operators = User.objects.filter(is_staff=True, is_superuser=False)

print("\n" + "="*70)
print("OPERATOR ACCOUNTS IN BUFIA SYSTEM")
print("="*70)

if operators.exists():
    for idx, operator in enumerate(operators, 1):
        print(f"\n{idx}. OPERATOR DETAILS:")
        print("-" * 70)
        print(f"   Username:        {operator.username}")
        print(f"   Full Name:       {operator.get_full_name() or 'N/A'}")
        print(f"   First Name:      {operator.first_name or 'N/A'}")
        print(f"   Last Name:       {operator.last_name or 'N/A'}")
        print(f"   Email:           {operator.email or 'N/A'}")
        print(f"   Active:          {'Yes' if operator.is_active else 'No'}")
        print(f"   Staff:           {'Yes' if operator.is_staff else 'No'}")
        print(f"   Superuser:       {'Yes' if operator.is_superuser else 'No'}")
        print(f"   Date Joined:     {operator.date_joined.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Last Login:      {operator.last_login.strftime('%Y-%m-%d %H:%M:%S') if operator.last_login else 'Never'}")
        print(f"   Password:        [HASHED - Cannot retrieve plain text]")
        print(f"   Password Set:    {'Yes' if operator.has_usable_password() else 'No'}")
        
else:
    print("\n⚠️  NO OPERATOR ACCOUNTS FOUND")
    print("\nOperators are users with:")
    print("  - is_staff = True")
    print("  - is_superuser = False")

print("\n" + "="*70)
print(f"TOTAL OPERATORS: {operators.count()}")
print("="*70)

print("\n📝 IMPORTANT NOTES:")
print("-" * 70)
print("1. Passwords are stored as hashed values and CANNOT be retrieved")
print("2. To reset a password, use: python manage.py changepassword <username>")
print("3. Or create a new password reset script")
print("4. Default password for test accounts is usually: 'operator123'")
print("="*70 + "\n")
