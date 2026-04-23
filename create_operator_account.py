"""
Create operator account for testing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create operator account
username = 'operator1'
password = 'operator123'
email = 'operator1@bufia.com'

# Check if operator already exists
if User.objects.filter(username=username).exists():
    operator = User.objects.get(username=username)
    print(f"✓ Operator '{username}' already exists")
else:
    operator = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name='Test',
        last_name='Operator',
        role=User.OPERATOR,
        is_active=True,
        is_verified=True,
    )
    print(f"✓ Created operator account: {username}")

# Update operator role and password
operator.role = User.OPERATOR
operator.is_active = True
operator.is_verified = True
operator.set_password(password)
operator.save()

print(f"\n{'='*50}")
print(f"OPERATOR LOGIN CREDENTIALS")
print(f"{'='*50}")
print(f"Username: {username}")
print(f"Password: {password}")
print(f"Role: {operator.get_role_display()}")
print(f"Active: {operator.is_active}")
print(f"Verified: {operator.is_verified}")
print(f"{'='*50}")
