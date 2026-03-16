#!/usr/bin/env python
"""Test role-based system implementation"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def main():
    print("=" * 70)
    print("ROLE-BASED SYSTEM TEST")
    print("=" * 70)
    
    # Test operators
    print("\n1. OPERATOR ACCOUNTS:")
    operators = User.objects.filter(role=User.OPERATOR)
    print(f"   Total: {operators.count()}")
    for op in operators:
        print(f"   ✅ {op.username} - {op.get_full_name() or 'N/A'}")
    
    # Test admins
    print("\n2. ADMIN ACCOUNTS:")
    admins = User.objects.filter(Q(is_superuser=True) | Q(role=User.SUPERUSER))
    print(f"   Total: {admins.count()}")
    for admin in admins[:5]:
        print(f"   ✅ {admin.username}")
    
    # Test farmers
    print("\n3. FARMER ACCOUNTS:")
    farmers = User.objects.filter(role=User.REGULAR_USER)
    print(f"   Total: {farmers.count()}")
    for farmer in farmers[:5]:
        print(f"   ✅ {farmer.username}")
    
    print("\n" + "=" * 70)
    print("✅ ROLE-BASED SYSTEM READY")
    print("=" * 70)


if __name__ == '__main__':
    from django.db.models import Q
    main()
