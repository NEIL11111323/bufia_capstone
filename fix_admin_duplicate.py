#!/usr/bin/env python
"""Script to fix the duplicate admin accounts"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from users.models import CustomUser

# Get both admin users
admin_lower = CustomUser.objects.filter(username='admin').first()
admin_upper = CustomUser.objects.filter(username='Admin').first()

print("=" * 70)
print("DUPLICATE ADMIN ACCOUNTS:")
print("=" * 70)

if admin_lower:
    print(f"\n1. Username: 'admin' (lowercase)")
    print(f"   ID: {admin_lower.id}")
    print(f"   Email: {admin_lower.email}")
    print(f"   Date Joined: {admin_lower.date_joined}")
    print(f"   Last Login: {admin_lower.last_login}")
    print(f"   Is Superuser: {admin_lower.is_superuser}")
    print(f"   Is Staff: {admin_lower.is_staff}")
    print(f"   Role: {admin_lower.role}")

if admin_upper:
    print(f"\n2. Username: 'Admin' (capitalized)")
    print(f"   ID: {admin_upper.id}")
    print(f"   Email: {admin_upper.email}")
    print(f"   Date Joined: {admin_upper.date_joined}")
    print(f"   Last Login: {admin_upper.last_login}")
    print(f"   Is Superuser: {admin_upper.is_superuser}")
    print(f"   Is Staff: {admin_upper.is_staff}")
    print(f"   Role: {admin_upper.role}")

print("\n" + "=" * 70)
print("RECOMMENDATION:")
print("=" * 70)

# Determine which to keep based on last login and superuser status
if admin_lower and admin_upper:
    keep = None
    delete = None
    
    # Prefer the one with superuser status
    if admin_lower.is_superuser and not admin_upper.is_superuser:
        keep = admin_lower
        delete = admin_upper
    elif admin_upper.is_superuser and not admin_lower.is_superuser:
        keep = admin_upper
        delete = admin_lower
    # If both or neither are superuser, prefer the one with more recent login
    elif admin_lower.last_login and admin_upper.last_login:
        if admin_lower.last_login > admin_upper.last_login:
            keep = admin_lower
            delete = admin_upper
        else:
            keep = admin_upper
            delete = admin_lower
    elif admin_lower.last_login:
        keep = admin_lower
        delete = admin_upper
    elif admin_upper.last_login:
        keep = admin_upper
        delete = admin_lower
    else:
        # Default to keeping lowercase
        keep = admin_lower
        delete = admin_upper
    
    print(f"Keep: ID {keep.id} (Username: '{keep.username}')")
    print(f"Delete: ID {delete.id} (Username: '{delete.username}')")
    
    response = input("\nDo you want to delete the duplicate? (yes/no): ").strip().lower()
    
    if response == 'yes':
        delete.delete()
        print(f"\n✓ Successfully deleted user ID {delete.id} ('{delete.username}')")
        print("You can now log in without errors.")
    else:
        print("\nNo changes made. You can manually delete using:")
        print(f"  python manage.py shell")
        print(f"  >>> from users.models import CustomUser")
        print(f"  >>> CustomUser.objects.get(id={delete.id}).delete()")
