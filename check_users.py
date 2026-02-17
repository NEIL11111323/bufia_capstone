#!/usr/bin/env python
"""Script to check all users and case-insensitive duplicates"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from users.models import CustomUser
from collections import defaultdict

# Get all users
users = CustomUser.objects.all().order_by('username')

print("=" * 70)
print("ALL USERS IN DATABASE:")
print("=" * 70)

for user in users:
    print(f"ID: {user.id:3d} | Username: {user.username:20s} | Email: {user.email:30s} | Active: {user.is_active}")

print(f"\nTotal users: {users.count()}")

# Check for case-insensitive duplicates
username_map = defaultdict(list)
for user in users:
    username_map[user.username.lower()].append(user)

print("\n" + "=" * 70)
print("CASE-INSENSITIVE DUPLICATE CHECK:")
print("=" * 70)

duplicates_found = False
for lower_username, user_list in username_map.items():
    if len(user_list) > 1:
        duplicates_found = True
        print(f"\nUsername '{lower_username}' has {len(user_list)} variations:")
        for user in user_list:
            print(f"  - ID: {user.id}, Username: '{user.username}', Email: {user.email}")

if not duplicates_found:
    print("No case-insensitive duplicates found.")
