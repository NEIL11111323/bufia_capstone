# CSRF Error Fix Guide

## Error
```
Forbidden (403)
CSRF verification failed. Request aborted.
Reason given for failure: CSRF token from POST incorrect.
```

## Root Causes

1. **Browser cache** - Old CSRF tokens cached
2. **Session expired** - User logged in too long ago
3. **Missing CSRF_TRUSTED_ORIGINS** - Development URL not trusted
4. **Cookies blocked** - Browser blocking cookies

## Solutions

### Solution 1: Clear Browser Cache (Most Common)
1. Open browser DevTools (F12)
2. Go to Application/Storage tab
3. Clear all cookies for localhost/127.0.0.1
4. Clear all site data
5. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
6. Log out and log back in

### Solution 2: Add Development URL to Settings
Add your development URL to `CSRF_TRUSTED_ORIGINS` in `bufia/settings.py`:

```python
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://*.trycloudflare.com',
]
```

### Solution 3: Check Cookie Settings
Ensure cookies are enabled in your browser:
- Chrome: Settings → Privacy and security → Cookies
- Firefox: Settings → Privacy & Security → Cookies
- Edge: Settings → Cookies and site permissions

### Solution 4: Restart Django Server
Sometimes the session gets corrupted:
```bash
# Stop the server (Ctrl+C)
# Clear sessions
python manage.py clearsessions

# Restart server
python manage.py runserver
```

### Solution 5: Check Form Templates
Verify all forms have CSRF token (already verified ✅):
```html
<form method="post" action="...">
    {% csrf_token %}
    <!-- form fields -->
</form>
```

## Quick Fix Steps

1. **Clear browser cache and cookies**
2. **Log out completely**
3. **Close all browser tabs**
4. **Restart Django server**
5. **Log back in**
6. **Try the form again**

## For Development

Add this to your `.env` file:
```
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False
```

## Verification

All forms in the system have been verified to include `{% csrf_token %}`:

### Admin Forms ✅
- Assign Operator form
- Approval Decision form
- Start Equipment Operation form
- Record Harvest form
- Confirm Rice Delivery form
- Verify Online Payment form
- Record Face-to-Face Payment form

### Operator Forms ✅
- Update Job Status form (job_detail.html)
- Submit Harvest Report form (job_detail.html)
- Quick Status Update form (jobs.html)
- Submit Harvest Modal form (jobs.html)
- Update Job Status form (work.html)
- Submit Harvest form (harvest.html)

## Testing After Fix

1. Log in as admin
2. Go to rental approval page
3. Try to submit a form
4. Should work without CSRF error

5. Log in as operator
6. Go to job detail page
7. Try to update status
8. Should work without CSRF error

## Common Mistakes to Avoid

❌ Don't use GET requests for data modification
❌ Don't disable CSRF protection
❌ Don't forget {% csrf_token %} in forms
❌ Don't use AJAX without CSRF token

✅ Use POST for data modification
✅ Include {% csrf_token %} in all POST forms
✅ Clear cache when switching between users
✅ Use proper CSRF headers for AJAX

## AJAX CSRF Fix (if needed)

If you're using AJAX, add this to your JavaScript:

```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Add to fetch requests
fetch(url, {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
})
```

## Still Having Issues?

1. Check Django logs for detailed error
2. Verify middleware order in settings.py
3. Check if custom middleware is interfering
4. Try in incognito/private browsing mode
5. Test with a different browser

## Prevention

To prevent CSRF errors in the future:

1. Always include {% csrf_token %} in POST forms
2. Clear cache when switching users
3. Don't keep sessions open for too long
4. Use proper logout functionality
5. Test forms after deployment
