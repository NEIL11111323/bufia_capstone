# Operator Accounts Information

## Current Operator Accounts

### 1. Operator: micho@gmail.com
- **Username**: `micho@gmail.com`
- **Full Name**: N/A
- **Email**: micho@gmail.com
- **Status**: Active ✅
- **Date Joined**: November 24, 2025
- **Last Login**: November 24, 2025
- **Password**: [HASHED - Cannot retrieve plain text]

### 2. Operator: operator1
- **Username**: `operator1`
- **Full Name**: Juan Operator
- **Email**: operator@bufia.com
- **Status**: Active ✅
- **Date Joined**: March 11, 2026
- **Last Login**: March 11, 2026 (4:22 PM)
- **Password**: [HASHED - Cannot retrieve plain text]

## Total Operators: 2

---

## ⚠️ IMPORTANT: About Passwords

### Why Can't I See the Passwords?

Django stores passwords using **one-way hashing** for security. This means:

1. ✅ Passwords are encrypted and cannot be decrypted
2. ✅ Even admins cannot see the original password
3. ✅ This is a security best practice
4. ✅ Protects user accounts from database breaches

### What You CAN Do:

#### Option 1: Reset Password for an Operator

```bash
python manage.py changepassword operator1
```

This will prompt you to enter a new password.

#### Option 2: Set a Known Password Using Script

Create a script to set passwords:

```python
# reset_operator_password.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Set password for operator1
operator = User.objects.get(username='operator1')
operator.set_password('your_new_password_here')
operator.save()

print(f"Password updated for {operator.username}")
```

#### Option 3: Create New Operator with Known Password

```python
# create_new_operator.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create new operator
operator = User.objects.create_user(
    username='operator2',
    email='operator2@bufia.com',
    password='operator123',  # Set your password here
    first_name='Maria',
    last_name='Operator',
    is_staff=True,
    is_superuser=False
)

print(f"Operator created: {operator.username}")
print(f"Password: operator123")
```

---

## Likely Default Passwords

Based on the system setup, the default passwords are likely:

### For operator1:
- **Username**: `operator1`
- **Likely Password**: `operator123` or `Operator123!`

### For micho@gmail.com:
- **Username**: `micho@gmail.com`
- **Likely Password**: `micho123` or `password123`

### To Test:
1. Go to: http://127.0.0.1:8000/accounts/login/
2. Try username: `operator1`
3. Try password: `operator123`

If it doesn't work, you'll need to reset the password.

---

## How to Reset Password (Step by Step)

### Method 1: Using Django Command (Recommended)

```bash
# For operator1
python manage.py changepassword operator1

# For micho@gmail.com
python manage.py changepassword micho@gmail.com
```

You'll be prompted:
```
Changing password for user 'operator1'
Password: [type new password]
Password (again): [type new password again]
Password changed successfully for user 'operator1'
```

### Method 2: Using Python Script

I can create a script for you to set specific passwords.

---

## Quick Password Reset Script

Save this as `reset_operator_passwords.py`:

```python
#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Reset passwords
operators = [
    {'username': 'operator1', 'password': 'operator123'},
    {'username': 'micho@gmail.com', 'password': 'micho123'},
]

for op_data in operators:
    try:
        operator = User.objects.get(username=op_data['username'])
        operator.set_password(op_data['password'])
        operator.save()
        print(f"✅ Password reset for: {op_data['username']}")
        print(f"   New password: {op_data['password']}")
    except User.DoesNotExist:
        print(f"❌ User not found: {op_data['username']}")

print("\n✅ Password reset complete!")
```

Run it:
```bash
python reset_operator_passwords.py
```

---

## Operator Login URLs

### Operator Dashboard:
```
http://127.0.0.1:8000/machines/operator/dashboard/
```

### Login Page:
```
http://127.0.0.1:8000/accounts/login/
```

---

## Summary

| Username | Email | Status | Likely Password |
|----------|-------|--------|-----------------|
| operator1 | operator@bufia.com | Active | operator123 |
| micho@gmail.com | micho@gmail.com | Active | micho123 |

**Note**: If these passwords don't work, use the reset methods above.

---

## Need Help?

If you need to:
1. **Reset a password** - Use `python manage.py changepassword <username>`
2. **Create new operator** - I can create a script for you
3. **Set specific passwords** - I can create a reset script

Let me know what you need!
