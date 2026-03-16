#!/usr/bin/env python
"""
Remove extra operator accounts, keeping only Juan Operator (operator1)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def remove_extra_operators():
    """Remove all operators except Juan Operator (operator1)"""
    
    # Get all operators (staff but not superuser)
    operators = User.objects.filter(is_staff=True, is_superuser=False)
    
    print("Current Operators:")
    for op in operators:
        print(f"  - ID: {op.id}, Username: {op.username}, Name: {op.get_full_name()}")
    
    # Keep only Juan Operator (operator1)
    keep_username = 'operator1'
    
    operators_to_remove = operators.exclude(username=keep_username)
    
    if not operators_to_remove.exists():
        print(f"\n✓ Only {keep_username} exists. No operators to remove.")
        return
    
    print(f"\nOperators to be removed:")
    for op in operators_to_remove:
        print(f"  - ID: {op.id}, Username: {op.username}, Name: {op.get_full_name()}")
    
    # Remove the operators
    count = operators_to_remove.count()
    operators_to_remove.delete()
    
    print(f"\n✓ Successfully removed {count} operator(s)")
    
    # Verify
    remaining = User.objects.filter(is_staff=True, is_superuser=False)
    print(f"\nRemaining Operators:")
    for op in remaining:
        print(f"  - ID: {op.id}, Username: {op.username}, Name: {op.get_full_name()}")

if __name__ == '__main__':
    remove_extra_operators()
