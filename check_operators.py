#!/usr/bin/env python
"""Check operators in the database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("OPERATOR ROLE CHECK")
print("=" * 60)
print(f"\nUser.OPERATOR constant value: '{User.OPERATOR}'")
print(f"\nAll role choices:")
for role_value, role_label in User.ROLE_CHOICES:
    print(f"  - {role_value}: {role_label}")

print(f"\n\nSearching for operators with role=User.OPERATOR ('{User.OPERATOR}')...")
operators = User.objects.filter(is_active=True, role=User.OPERATOR)
print(f"Total operators found: {operators.count()}")

if operators.exists():
    print("\nOperator details:")
    for op in operators:
        print(f"  - ID: {op.id}, Username: {op.username}, Name: {op.get_full_name()}, Role: '{op.role}'")
else:
    print("\n⚠️  NO OPERATORS FOUND!")
    print("\nChecking all users and their roles:")
    all_users = User.objects.all()[:20]
    print(f"Total users in database: {User.objects.count()}")
    print("\nFirst 20 users:")
    for user in all_users:
        print(f"  - ID: {user.id}, Username: {user.username}, Role: '{user.role}', Active: {user.is_active}")
    
    print("\n\nUsers with 'operator' in role (case-insensitive):")
    operator_like = User.objects.filter(role__icontains='operator')
    print(f"Found: {operator_like.count()}")
    for user in operator_like:
        print(f"  - ID: {user.id}, Username: {user.username}, Role: '{user.role}', Active: {user.is_active}")

print("\n" + "=" * 60)
