#!/usr/bin/env python
"""Create operator account"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create operator account
username = input("Enter username (default: operator): ") or "operator"
email = input("Enter email (default: operator@bufia.com): ") or "operator@bufia.com"
password = input("Enter password (default: operator123): ") or "operator123"
first_name = input("Enter first name (default: Operator): ") or "Operator"
last_name = input("Enter last name (default: User): ") or "User"

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'role': User.OPERATOR,
        'is_staff': True,
        'is_active': True,
    }
)

if created:
    user.set_password(password)
    user.save()
    print(f"\n✅ Operator account created successfully!")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Role: operator")
else:
    print(f"\n⚠️  User '{username}' already exists. Updating role...")
    user.role = User.OPERATOR
    user.is_staff = True
    user.set_password(password)
    user.save()
    print(f"✅ Updated to operator role")
