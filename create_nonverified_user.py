#!/usr/bin/env python
"""
Script to create a non-verified test user account
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import MembershipApplication
import datetime

User = get_user_model()

def create_nonverified_user():
    """Create a non-verified test user"""
    
    # User details
    username = 'testuser'
    email = 'testuser@bufia.com'
    password = 'testpass123'
    first_name = 'Test'
    last_name = 'User'
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"❌ User '{username}' already exists!")
        user = User.objects.get(username=username)
        print(f"   Email: {user.email}")
        print(f"   Verified: {user.is_verified}")
        print(f"   Form Submitted: {user.membership_form_submitted}")
        
        # Ask if want to update
        response = input("\nDo you want to make this user non-verified? (yes/no): ")
        if response.lower() == 'yes':
            user.is_verified = False
            user.membership_form_submitted = False
            user.save()
            print("✅ User updated to non-verified status!")
        return user
    
    # Create new user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number='09123456789',
        address='Test Address, Test City',
        role=User.REGULAR_USER,
        is_verified=False,  # NOT VERIFIED
        membership_form_submitted=False,  # NO FORM SUBMITTED YET
        is_active=True,
        is_staff=False,
        is_superuser=False
    )
    
    print("✅ Non-verified test user created successfully!")
    print("\n" + "="*60)
    print("📋 USER DETAILS:")
    print("="*60)
    print(f"Username:     {user.username}")
    print(f"Password:     {password}")
    print(f"Email:        {user.email}")
    print(f"Full Name:    {user.get_full_name()}")
    print(f"Phone:        {user.phone_number}")
    print(f"Role:         {user.get_role_display()}")
    print(f"Verified:     {user.is_verified} ❌")
    print(f"Form Submit:  {user.membership_form_submitted} ❌")
    print(f"Active:       {user.is_active} ✅")
    print("="*60)
    print("\n🔐 LOGIN CREDENTIALS:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print("\n⚠️  USER STATUS:")
    print("   - Can login to the system")
    print("   - Can view all machines and features")
    print("   - CANNOT rent machines (not verified)")
    print("   - CANNOT make transactions (not verified)")
    print("   - Will see notification when trying to rent")
    print("\n📝 NEXT STEPS:")
    print("   1. Login with the credentials above")
    print("   2. Try to rent a machine")
    print("   3. You should see: 'Membership verification required!'")
    print("   4. Submit membership form to test the workflow")
    print("="*60)
    
    return user

if __name__ == '__main__':
    try:
        user = create_nonverified_user()
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        sys.exit(1)
