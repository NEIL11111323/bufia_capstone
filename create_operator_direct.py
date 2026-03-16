"""
Direct script to create operator account
Run with: python create_operator_direct.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

@transaction.atomic
def create_operator():
    """Create operator account with staff permissions"""
    
    # Operator details
    username = 'operator1'
    email = 'operator@bufia.com'
    password = 'operator123'
    first_name = 'Juan'
    last_name = 'Operator'
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"\n❌ User '{username}' already exists!")
        existing_user = User.objects.get(username=username)
        print(f"   Email: {existing_user.email}")
        print(f"   Staff: {existing_user.is_staff}")
        print(f"   Superuser: {existing_user.is_superuser}")
        print(f"\n💡 Try logging in with:")
        print(f"   Username: {username}")
        print(f"   Password: operator123")
        return None
    
    # Create operator user
    operator = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=True,
        is_superuser=False,
        is_active=True
    )
    
    # Try to set is_verified if field exists
    try:
        operator.is_verified = True
        operator.save()
    except AttributeError:
        pass
    
    print("\n" + "=" * 60)
    print("✅ OPERATOR ACCOUNT CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Username:    {operator.username}")
    print(f"Email:       {operator.email}")
    print(f"Password:    {password}")
    print(f"Full Name:   {operator.get_full_name()}")
    print(f"Staff:       {operator.is_staff}")
    print(f"Superuser:   {operator.is_superuser}")
    print(f"Active:      {operator.is_active}")
    print("=" * 60)
    print("\n📋 OPERATOR DASHBOARD ACCESS:")
    print(f"   URL: http://localhost:8000/machines/operator/dashboard/")
    print("\n🔑 LOGIN CREDENTIALS:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print("\n⚠️  IMPORTANT: Change the password after first login!")
    print("=" * 60 + "\n")
    
    return operator

if __name__ == '__main__':
    create_operator()
