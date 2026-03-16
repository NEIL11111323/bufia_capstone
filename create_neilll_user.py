#!/usr/bin/env python
"""
Script to create user 'neilll' with password 'pass123'
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_neilll_user():
    """Create user neilll"""
    
    # User details
    username = 'neilll'
    email = 'neilll@bufia.com'
    password = 'pass123'
    first_name = 'Neil'
    last_name = 'Test'
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"❌ User '{username}' already exists!")
        user = User.objects.get(username=username)
        print(f"\n📋 EXISTING USER DETAILS:")
        print(f"   Username:     {user.username}")
        print(f"   Email:        {user.email}")
        print(f"   Full Name:    {user.get_full_name()}")
        print(f"   Verified:     {user.is_verified}")
        print(f"   Form Submit:  {user.membership_form_submitted}")
        
        # Update password
        response = input("\nDo you want to reset the password to 'pass123'? (yes/no): ")
        if response.lower() == 'yes':
            user.set_password(password)
            user.is_verified = False
            user.membership_form_submitted = False
            user.save()
            print("✅ Password reset and user set to non-verified!")
            print(f"\n🔐 LOGIN CREDENTIALS:")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
        return user
    
    # Create new user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number='09123456789',
        address='Test Address, Bulacan',
        role=User.REGULAR_USER,
        is_verified=False,  # NOT VERIFIED
        membership_form_submitted=False,  # NO FORM SUBMITTED
        is_active=True,
        is_staff=False,
        is_superuser=False
    )
    
    print("✅ User 'neilll' created successfully!")
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
    print("   ✅ Can login to the system")
    print("   ✅ Can view all machines and features")
    print("   ❌ CANNOT rent machines (not verified)")
    print("   ❌ CANNOT make transactions (not verified)")
    print("   📢 Will see notification when trying to rent")
    print("\n📝 TO TEST THE SYSTEM:")
    print("   1. Login with username: neilll, password: pass123")
    print("   2. Browse machines (you can see everything)")
    print("   3. Try to rent a machine")
    print("   4. You'll see: '⚠️ Membership verification required!'")
    print("   5. Submit membership form (₱500 fee)")
    print("   6. Admin must mark payment as paid")
    print("   7. Admin must approve membership")
    print("   8. Then you can rent machines")
    print("="*60)
    
    return user

if __name__ == '__main__':
    try:
        user = create_neilll_user()
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
