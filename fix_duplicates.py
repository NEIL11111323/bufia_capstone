#!/usr/bin/env python
"""Script to identify and fix duplicate usernames in the database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from users.models import CustomUser
from django.db.models import Count

# Find duplicate usernames
duplicates = CustomUser.objects.values('username').annotate(
    count=Count('id')
).filter(count__gt=1)

print("=" * 50)
print("DUPLICATE USERNAMES FOUND:")
print("=" * 50)

for dup in duplicates:
    username = dup['username']
    count = dup['count']
    print(f"\nUsername: '{username}' appears {count} times")
    
    # Get all users with this username
    users = CustomUser.objects.filter(username=username).order_by('date_joined')
    
    for i, user in enumerate(users, 1):
        print(f"  {i}. ID: {user.id}, Email: {user.email}, Date Joined: {user.date_joined}, Last Login: {user.last_login}")

print("\n" + "=" * 50)
print("RECOMMENDED ACTION:")
print("=" * 50)
print("Review the users above and decide which ones to keep.")
print("You can delete duplicates using Django admin or shell.")
print("\nTo delete a user by ID, run:")
print("  python manage.py shell")
print("  >>> from users.models import CustomUser")
print("  >>> CustomUser.objects.get(id=<ID>).delete()")
