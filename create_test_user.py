"""
Script to create a test user account for BUFIA system
Run this with: python manage.py shell < create_test_user.py
"""

from django.contrib.auth import get_user_model
from users.models import Sector

User = get_user_model()

# User details
username = "testuser"
email = "testuser@bufia.com"
password = "testpass123"
first_name = "Test"
last_name = "User"
phone_number = "09123456789"

# Check if user already exists
if User.objects.filter(username=username).exists():
    print(f"User '{username}' already exists!")
    user = User.objects.get(username=username)
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Password: testpass123")
else:
    # Create the user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        is_active=True,
        is_verified=False,  # Not verified yet
        role='member'
    )
    
    print("=" * 50)
    print("✅ Test User Account Created Successfully!")
    print("=" * 50)
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"Name: {first_name} {last_name}")
    print(f"Phone: {phone_number}")
    print(f"Role: member")
    print(f"Verified: No (submit membership application to get verified)")
    print("=" * 50)
    print("\nYou can now login at: http://127.0.0.1:8000/accounts/login/")
    print("=" * 50)
