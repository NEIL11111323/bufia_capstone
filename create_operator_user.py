"""
Create an operator user account for BUFIA system
Operators have unique functions for managing machine operations and harvest reporting
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import CustomUser

User = get_user_model()

# Create operator account
username = 'operator'
email = 'operator@bufia.com'
password = 'operator123'
first_name = 'Machine'
last_name = 'Operator'

# Check if user already exists
if User.objects.filter(username=username).exists():
    print(f'❌ User "{username}" already exists.')
    operator = User.objects.get(username=username)
    print(f'   Updating existing user to operator role...')
    operator.role = CustomUser.OPERATOR
    operator.is_verified = True
    operator.is_staff = False
    operator.is_superuser = False
    operator.save()
    print(f'✅ Updated "{username}" to operator role')
else:
    # Create new operator user
    operator = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=CustomUser.OPERATOR,
        is_verified=True,
        is_staff=False,
        is_superuser=False
    )
    print(f'✅ Operator account created successfully!')

print('\n' + '='*60)
print('OPERATOR ACCOUNT DETAILS')
print('='*60)
print(f'Username: {username}')
print(f'Password: {password}')
print(f'Email: {email}')
print(f'Role: Operator')
print(f'Verified: Yes')
print('='*60)

print('\n' + '='*60)
print('OPERATOR UNIQUE FUNCTIONS')
print('='*60)
print("""
1. VIEW ASSIGNED JOBS
   - See all machine rentals assigned to them
   - View job details (machine, farmer, location, dates)
   
2. UPDATE JOB STATUS
   - Mark jobs as "In Progress" when starting work
   - Update field progress and notes
   
3. SUBMIT HARVEST REPORTS (IN-KIND Rentals)
   - Enter total sacks harvested
   - System auto-calculates BUFIA share (1/9)
   - Submit harvest completion reports
   
4. VIEW JOB HISTORY
   - See completed jobs
   - View harvest reports submitted
   
5. DASHBOARD ACCESS
   - Operator-specific dashboard at /operator/dashboard/
   - Statistics: Assigned jobs, Today's jobs, In Progress, etc.
   
6. NO ACCESS TO:
   - Admin functions (user management, approvals)
   - Financial reports
   - Membership management
   - Other operators' jobs
""")
print('='*60)

print('\n✅ Operator account is ready to use!')
print('   Login at: http://127.0.0.1:8000/login/')
