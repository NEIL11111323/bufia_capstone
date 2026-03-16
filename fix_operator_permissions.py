"""
Fix operator permissions
Run with: python fix_operator_permissions.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def fix_operator():
    """Fix operator permissions"""
    
    username = 'operator1'
    
    try:
        operator = User.objects.get(username=username)
        
        print("\n" + "=" * 60)
        print(f"📝 CURRENT STATUS FOR '{username}':")
        print("=" * 60)
        print(f"Email:       {operator.email}")
        print(f"Full Name:   {operator.get_full_name() or 'Not set'}")
        print(f"Staff:       {operator.is_staff}")
        print(f"Superuser:   {operator.is_superuser}")
        print(f"Active:      {operator.is_active}")
        
        # Update permissions
        operator.is_staff = True
        operator.is_active = True
        operator.first_name = 'Juan'
        operator.last_name = 'Operator'
        operator.email = 'operator@bufia.com'
        
        # Reset password to known value
        operator.set_password('operator123')
        
        operator.save()
        
        print("\n" + "=" * 60)
        print("✅ OPERATOR PERMISSIONS UPDATED!")
        print("=" * 60)
        print(f"Username:    {operator.username}")
        print(f"Email:       {operator.email}")
        print(f"Password:    operator123")
        print(f"Full Name:   {operator.get_full_name()}")
        print(f"Staff:       {operator.is_staff}")
        print(f"Active:      {operator.is_active}")
        print("=" * 60)
        print("\n📋 OPERATOR DASHBOARD ACCESS:")
        print(f"   URL: http://localhost:8000/machines/operator/dashboard/")
        print("\n🔑 LOGIN CREDENTIALS:")
        print(f"   Username: operator1")
        print(f"   Password: operator123")
        print("\n✅ You can now login with these credentials!")
        print("=" * 60 + "\n")
        
    except User.DoesNotExist:
        print(f"\n❌ User '{username}' not found!")
        print("💡 Creating new operator account...\n")
        
        operator = User.objects.create_user(
            username='operator1',
            email='operator@bufia.com',
            password='operator123',
            first_name='Juan',
            last_name='Operator',
            is_staff=True,
            is_superuser=False,
            is_active=True
        )
        
        print("=" * 60)
        print("✅ NEW OPERATOR ACCOUNT CREATED!")
        print("=" * 60)
        print(f"Username: operator1")
        print(f"Password: operator123")
        print("=" * 60 + "\n")

if __name__ == '__main__':
    fix_operator()
