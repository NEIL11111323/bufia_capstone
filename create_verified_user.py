"""
Create a verified user for testing package rentals
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Sector
from django.utils import timezone

User = get_user_model()

def create_verified_user():
    """Create a verified user with all necessary fields"""
    
    print("=" * 80)
    print("CREATING VERIFIED USER")
    print("=" * 80)
    
    # User details
    username = "testuser"
    email = "testuser@bufia.com"
    password = "testpass123"
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"\n⚠️  User '{username}' already exists!")
        user = User.objects.get(username=username)
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Is Verified: {user.is_verified}")
        print(f"   Membership Status: {user.membership_status}")
        
        # Update to verified if not already
        if not user.is_verified:
            user.is_verified = True
            user.membership_status = 'active'
            user.membership_paid = True
            user.membership_payment_date = timezone.now()
            user.save()
            print("\n✅ User updated to verified status!")
        
        print(f"\n📝 Login credentials:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return user
    
    # Get or create a sector
    sector = Sector.objects.filter(is_active=True).first()
    
    if not sector:
        # Get the next sector number
        last_sector = Sector.objects.order_by('-sector_number').first()
        next_number = (last_sector.sector_number + 1) if last_sector else 1
        
        sector = Sector.objects.create(
            name="Test Sector",
            sector_number=next_number,
            description='Test sector for verified users',
            is_active=True
        )
        print(f"\n✅ Created sector: {sector.name} (#{sector.sector_number})")
    else:
        print(f"\n✓ Using existing sector: {sector.name} (#{sector.sector_number})")
    
    # Create the user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name="Test",
        last_name="User",
    )
    
    # Set user as verified member
    user.is_verified = True
    user.membership_status = 'active'
    user.membership_paid = True
    user.membership_payment_date = timezone.now()
    user.sector = sector
    
    # Additional fields
    user.phone_number = "09123456789"
    user.address = "Test Address, Test City"
    
    user.save()
    
    print(f"\n✅ Created verified user successfully!")
    print(f"\n📋 User Details:")
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Full Name: {user.get_full_name()}")
    print(f"   Phone: {user.phone_number}")
    print(f"   Sector: {user.sector.name if user.sector else 'None'}")
    print(f"   Is Verified: {user.is_verified}")
    print(f"   Membership Status: {user.membership_status}")
    print(f"   Membership Paid: {user.membership_paid}")
    print(f"   Is Staff: {user.is_staff}")
    print(f"   Is Superuser: {user.is_superuser}")
    
    print(f"\n📝 Login credentials:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    
    print(f"\n🔗 You can now:")
    print(f"   1. Login at: http://127.0.0.1:8000/accounts/login/")
    print(f"   2. Create package requests at: http://127.0.0.1:8000/machines/packages/create/")
    print(f"   3. View your packages at: http://127.0.0.1:8000/machines/packages/")
    
    print("\n" + "=" * 80)
    
    return user

if __name__ == '__main__':
    try:
        user = create_verified_user()
    except Exception as e:
        print(f"\n❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
