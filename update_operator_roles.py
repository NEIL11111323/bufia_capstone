#!/usr/bin/env python
"""
Update existing operator accounts to use the role field instead of is_staff
This script sets role='operator' for all operator accounts
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def main():
    print("=" * 70)
    print("UPDATING OPERATOR ACCOUNTS TO USE ROLE FIELD")
    print("=" * 70)
    
    # Find all users who are staff but not superuser (current operators)
    current_operators = User.objects.filter(is_staff=True, is_superuser=False)
    
    print(f"\nFound {current_operators.count()} staff users (potential operators):")
    print("-" * 70)
    
    updated_count = 0
    for user in current_operators:
        print(f"\n👤 {user.username}")
        print(f"   Name: {user.get_full_name() or 'N/A'}")
        print(f"   Email: {user.email or 'N/A'}")
        print(f"   Current role: {user.role}")
        print(f"   is_staff: {user.is_staff}")
        
        # Update to operator role
        if user.role != User.OPERATOR:
            user.role = User.OPERATOR
            user.save()
            print(f"   ✅ Updated role to: {User.OPERATOR}")
            updated_count += 1
        else:
            print(f"   ℹ️  Already set to operator role")
    
    # Also check for any users with operator role
    print("\n" + "=" * 70)
    print("ALL USERS WITH OPERATOR ROLE:")
    print("=" * 70)
    
    all_operators = User.objects.filter(role=User.OPERATOR)
    print(f"\nTotal operators: {all_operators.count()}")
    
    for user in all_operators:
        print(f"\n✅ {user.username}")
        print(f"   Name: {user.get_full_name() or 'N/A'}")
        print(f"   Email: {user.email or 'N/A'}")
        print(f"   Role: {user.role}")
        print(f"   is_staff: {user.is_staff}")
        print(f"   is_superuser: {user.is_superuser}")
    
    print("\n" + "=" * 70)
    print(f"✅ UPDATED {updated_count} ACCOUNTS")
    print("=" * 70)
    
    print("\nNEXT STEPS:")
    print("1. Update operator view functions to use role field")
    print("2. Test operator login and dashboard access")
    print("3. Verify all operator functionalities work")


if __name__ == '__main__':
    main()
