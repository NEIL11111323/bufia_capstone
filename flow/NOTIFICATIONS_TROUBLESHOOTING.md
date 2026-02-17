# Notifications Not Showing - Troubleshooting Guide

## Issue
User reports: "I can't see the notifications"

## Possible Causes & Solutions

### 1. **No Notifications in Database**
**Check:** Run the check script
```bash
python manage.py shell < check_notifications.py
```

**Solution:** Create test notifications
```bash
python manage.py create_test_notifications
```

### 2. **Context Processor Not Working**
**Check:** Verify context processor is registered in `settings.py`
```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... other processors
                'notifications.context_processors.notifications_context',
            ],
        },
    },
]
```

**Solution:** If missing, add it to settings.py

### 3. **User Not Authenticated**
**Check:** Notifications only show for logged-in users
```python
if request.user.is_authenticated:
    # Notifications are loaded
```

**Solution:** Make sure you're logged in

### 4. **JavaScript Error**
**Check:** Open browser console (F12) and look for errors

**Solution:** Clear browser cache and reload page

### 5. **Template Not Loading Context**
**Check:** Verify `base.html` has the notification dropdown code

**Solution:** The dropdown should be in the navbar section

### 6. **Database Migration Issue**
**Check:** Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. **Cache Issue**
**Check:** Clear Django cache
```bash
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

**Solution:** Also clear browser cache (Ctrl+Shift+Delete)

## Quick Diagnostic Steps

### Step 1: Check if notifications exist
```bash
python manage.py shell
>>> from notifications.models import UserNotification
>>> UserNotification.objects.count()
```

If returns 0, create test notifications:
```bash
python manage.py create_test_notifications
```

### Step 2: Check context processor
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from notifications.context_processors import notifications_context
>>> from django.test import RequestFactory
>>> 
>>> User = get_user_model()
>>> user = User.objects.first()
>>> 
>>> factory = RequestFactory()
>>> request = factory.get('/')
>>> request.user = user
>>> 
>>> context = notifications_context(request)
>>> print(context)
```

Should return:
```python
{
    'unread_notifications_count': X,
    'recent_notifications': [...]
}
```

### Step 3: Check template rendering
Look at the page source (Ctrl+U) and search for "notification-dropdown"
- If found: Notifications are being rendered
- If not found: Template issue

### Step 4: Check browser console
Press F12 and look for:
- JavaScript errors
- Network errors
- Console warnings

## Common Issues & Fixes

### Issue: "No notifications" message shows
**Cause:** No notifications in database for current user
**Fix:** 
```bash
python manage.py create_test_notifications
```

### Issue: Dropdown doesn't open
**Cause:** Bootstrap JavaScript not loaded
**Fix:** Check that Bootstrap JS is included in base.html:
```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
```

### Issue: Notification count shows but dropdown is empty
**Cause:** Template loop issue
**Fix:** Check the `{% for notification in recent_notifications %}` loop in base.html

### Issue: Notifications show for admin but not regular users
**Cause:** Permissions or user-specific filtering
**Fix:** Check UserNotification.objects.filter(user=request.user)

## Testing Notifications

### Create a test notification manually:
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from notifications.models import UserNotification
>>> 
>>> User = get_user_model()
>>> user = User.objects.first()  # or get specific user
>>> 
>>> UserNotification.objects.create(
...     user=user,
...     notification_type='general',
...     message='This is a test notification',
...     is_read=False
... )
```

### Verify it appears:
1. Refresh the page
2. Check the notification bell icon
3. Click to open dropdown
4. Should see the test notification

## Files to Check

1. **notifications/context_processors.py** - Provides notifications to templates
2. **templates/base.html** - Displays notification dropdown
3. **notifications/models.py** - UserNotification model
4. **bufia/settings.py** - Context processor registration

## Debug Mode

Add debug output to context processor:
```python
def notifications_context(request):
    unread_notifications_count = 0
    recent_notifications = []
    
    if request.user.is_authenticated:
        try:
            unread_notifications_count = UserNotification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            
            recent_notifications = UserNotification.objects.filter(
                user=request.user
            ).order_by('-timestamp')[:5]
            
            # DEBUG
            print(f"User: {request.user.username}")
            print(f"Unread count: {unread_notifications_count}")
            print(f"Recent notifications: {recent_notifications.count()}")
            
        except Exception as e:
            print(f"Error in notifications_context: {e}")
            unread_notifications_count = 0
            recent_notifications = []
            
    return {
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }
```

## Quick Fix Commands

```bash
# 1. Create test notifications
python manage.py create_test_notifications

# 2. Check notifications exist
python manage.py shell < check_notifications.py

# 3. Clear cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()

# 4. Restart server
# Press Ctrl+C to stop
python manage.py runserver

# 5. Clear browser cache
# In browser: Ctrl+Shift+Delete
```

## Expected Behavior

When working correctly:
1. ✅ Notification bell icon shows in navbar
2. ✅ Red dot appears if unread notifications exist
3. ✅ Clicking bell opens dropdown
4. ✅ Recent 5 notifications are displayed
5. ✅ "No notifications" message if none exist
6. ✅ Clicking notification marks it as read

## Still Not Working?

If notifications still don't show after trying all steps:

1. Check server console for errors
2. Check browser console (F12) for JavaScript errors
3. Verify you're logged in as a user (not anonymous)
4. Try creating a notification manually via Django admin
5. Check if UserNotification model exists in database
6. Verify migrations are applied: `python manage.py showmigrations notifications`

## Contact Support

If issue persists, provide:
- Django version
- Browser and version
- Console errors (if any)
- Output of `python manage.py shell < check_notifications.py`
- Screenshot of the navbar area
