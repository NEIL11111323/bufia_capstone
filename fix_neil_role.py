#!/usr/bin/env python
"""Fix Neil's role to be an operator"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("FIXING NEIL'S ROLE")
print("=" * 70)

# Try both lowercase and capitalized
for username in ['neil', 'Neil']:
    try:
        neil = User.objects.get(username=username)
        print(f"\n✅ Found user: {neil.username}")
        print(f"   Current role: {neil.role}")
        print(f"   Is staff: {neil.is_staff}")
        print(f"   Is active: {neil.is_active}")
        
        # Update to operator
        neil.role = User.OPERATOR
        neil.is_staff = True
        neil.is_active = True
        neil.save()
        
        print(f"\n✅ Updated {neil.username} to OPERATOR role")
        print(f"   New role: {neil.role}")
        print(f"   Is staff: {neil.is_staff}")
        print(f"   Is active: {neil.is_active}")
        
        print(f"\n✅ SUCCESS! {neil.username} is now an operator")
        print(f"\n📝 Next steps:")
        print(f"   1. Restart Django server")
        print(f"   2. Login as admin")
        print(f"   3. Go to rental approval page")
        print(f"   4. Assign {neil.username} to a rental")
        print(f"   5. Login as {neil.username} and check dashboard")
        
        break
        
    except User.DoesNotExist:
        continue
else:
    print(f"\n❌ Neither 'neil' nor 'Neil' found in database")
    print(f"\n   Available users:")
    for user in User.objects.all()[:15]:
        print(f"   - {user.username} (role: {user.role})")

print("\n" + "=" * 70)
