#!/usr/bin/env python
"""
Script to reset operator passwords to known values
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*70)
print("OPERATOR PASSWORD RESET SCRIPT")
print("="*70 + "\n")

# Define operators and their new passwords
operators_to_reset = [
    {
        'username': 'operator1',
        'new_password': 'operator123',
        'description': 'Juan Operator'
    },
    {
        'username': 'micho@gmail.com',
        'new_password': 'micho123',
        'description': 'Micho Operator'
    },
]

success_count = 0
failed_count = 0

for op_data in operators_to_reset:
    try:
        operator = User.objects.get(username=op_data['username'])
        operator.set_password(op_data['new_password'])
        operator.save()
        
        print(f"✅ SUCCESS: Password reset for {op_data['description']}")
        print(f"   Username: {op_data['username']}")
        print(f"   New Password: {op_data['new_password']}")
        print(f"   Status: Active - {operator.is_active}")
        print("-" * 70)
        success_count += 1
        
    except User.DoesNotExist:
        print(f"❌ FAILED: User not found")
        print(f"   Username: {op_data['username']}")
        print("-" * 70)
        failed_count += 1

print("\n" + "="*70)
print("RESET SUMMARY")
print("="*70)
print(f"✅ Successful: {success_count}")
print(f"❌ Failed: {failed_count}")
print(f"📊 Total: {success_count + failed_count}")
print("="*70)

if success_count > 0:
    print("\n📝 LOGIN CREDENTIALS:")
    print("-" * 70)
    for op_data in operators_to_reset:
        try:
            operator = User.objects.get(username=op_data['username'])
            print(f"\n{op_data['description']}:")
            print(f"  Username: {op_data['username']}")
            print(f"  Password: {op_data['new_password']}")
            print(f"  Login URL: http://127.0.0.1:8000/accounts/login/")
        except User.DoesNotExist:
            pass
    print("\n" + "="*70)

print("\n✅ Password reset complete!\n")
