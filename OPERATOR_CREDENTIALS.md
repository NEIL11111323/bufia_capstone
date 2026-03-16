# 🔐 Operator Account Credentials

## ✅ All Operator Accounts (Passwords Reset)

### Operator 1: Juan Operator
```
Username: operator1
Password: operator123
Email: operator@bufia.com
Status: Active ✅
Role: Operator (Staff, Not Superuser)
```

### Operator 2: Micho
```
Username: micho@gmail.com
Password: micho123
Email: micho@gmail.com
Status: Active ✅
Role: Operator (Staff, Not Superuser)
```

---

## 🌐 Login Information

### Login URL:
```
http://127.0.0.1:8000/accounts/login/
```

### Operator Dashboard URL:
```
http://127.0.0.1:8000/machines/operator/dashboard/
```

---

## 📋 Quick Login Guide

### For Operator 1 (Juan):
1. Go to: http://127.0.0.1:8000/accounts/login/
2. Enter username: `operator1`
3. Enter password: `operator123`
4. Click "Login"
5. You'll be redirected to operator dashboard

### For Operator 2 (Micho):
1. Go to: http://127.0.0.1:8000/accounts/login/
2. Enter username: `micho@gmail.com`
3. Enter password: `micho123`
4. Click "Login"
5. You'll be redirected to operator dashboard

---

## 🔧 What Operators Can Do

Operators have access to:
- ✅ View assigned rentals
- ✅ Update rental status
- ✅ Submit harvest reports (for IN-KIND rentals)
- ✅ View machine information
- ✅ Update operation progress
- ✅ Communicate with admin
- ❌ Cannot approve rentals (admin only)
- ❌ Cannot manage users (admin only)
- ❌ Cannot access admin panel (admin only)

---

## 📊 Account Summary

| # | Username | Password | Full Name | Email | Status |
|---|----------|----------|-----------|-------|--------|
| 1 | operator1 | operator123 | Juan Operator | operator@bufia.com | Active ✅ |
| 2 | micho@gmail.com | micho123 | N/A | micho@gmail.com | Active ✅ |

**Total Operators**: 2

---

## 🔄 To Change Passwords Later

### Method 1: Using Django Command
```bash
python manage.py changepassword operator1
```

### Method 2: Using Reset Script
```bash
python reset_operator_passwords.py
```

### Method 3: Create Custom Password
Edit `reset_operator_passwords.py` and change the password values, then run:
```bash
python reset_operator_passwords.py
```

---

## 🆕 To Create New Operator

Use this command:
```bash
python create_operator_account.py
```

Or manually:
```bash
python manage.py createsuperuser --username operator3 --email operator3@bufia.com
# Then set is_superuser=False in admin panel
```

---

## ⚠️ Security Notes

1. **Change default passwords** in production
2. **Use strong passwords** (mix of letters, numbers, symbols)
3. **Don't share passwords** via insecure channels
4. **Rotate passwords** regularly
5. **Monitor login activity** for suspicious access

---

## 📝 Password Requirements

For production, ensure passwords have:
- Minimum 8 characters
- Mix of uppercase and lowercase
- At least one number
- At least one special character
- Not common words or patterns

Example strong passwords:
- `Oper@tor2026!`
- `Bufia#Ops123`
- `M1ch0$ecure`

---

## 🔍 Troubleshooting

### Problem: Can't login with these credentials
**Solution**: Run the reset script again:
```bash
python reset_operator_passwords.py
```

### Problem: "User is not active"
**Solution**: Activate the user:
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> operator = User.objects.get(username='operator1')
>>> operator.is_active = True
>>> operator.save()
```

### Problem: Redirected to wrong page after login
**Solution**: Check user permissions:
- Operators should have: `is_staff=True`, `is_superuser=False`
- If `is_superuser=True`, they'll go to admin panel instead

---

## 📞 Support

If you need to:
- Reset passwords
- Create new operators
- Change operator permissions
- Troubleshoot login issues

Run the appropriate script or use Django management commands.

---

**Last Updated**: March 12, 2026
**Passwords Reset**: ✅ Complete
**Status**: Ready for Use
