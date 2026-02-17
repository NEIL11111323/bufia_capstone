# Middleware Fix - AccessControlMiddleware Missing

## Issue
Server failed to start with error:
```
AttributeError: module 'bufia.middleware' has no attribute 'AccessControlMiddleware'
```

## Root Cause
The `settings.py` referenced `bufia.middleware.AccessControlMiddleware` but the class didn't exist in the middleware file.

## Solution
Added a placeholder `AccessControlMiddleware` class to `bufia/middleware.py`:

```python
class AccessControlMiddleware:
    """
    Placeholder middleware for access control.
    Can be extended for custom access control logic.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
```

## Current Middleware Classes in bufia/middleware.py

1. **AccessControlMiddleware** - Placeholder for custom access control
2. **NoCacheForAuthenticatedMiddleware** - Prevents caching of authenticated pages
3. **LogoutCacheControlMiddleware** - Adds cache control to logout responses

## Status
✅ **FIXED** - Server should now start successfully.

## Next Steps
If you need custom access control logic, you can extend the `AccessControlMiddleware` class with your specific requirements.
