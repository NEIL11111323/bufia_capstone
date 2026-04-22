"""
Middleware for BUFIA project
"""
from django.utils.cache import add_never_cache_headers
from django.middleware.csrf import get_token


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


class NoCacheForAuthenticatedMiddleware:
    """
    Middleware to prevent caching of authenticated pages and auth forms.
    This avoids stale CSRF/login pages when users navigate with browser back/forward.
    """

    AUTH_FORM_PATH_PREFIXES = (
        '/accounts/login/',
        '/accounts/signup/',
        '/accounts/password/',
        '/setup/',
    )
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Ensure auth pages always have a fresh CSRF cookie.
        if request.method == 'GET' and any(
            request.path.startswith(prefix) for prefix in self.AUTH_FORM_PATH_PREFIXES
        ):
            get_token(request)

        response = self.get_response(request)
        
        # Add no-cache headers for authenticated pages and auth-related forms.
        should_no_cache = request.user.is_authenticated or any(
            request.path.startswith(prefix) for prefix in self.AUTH_FORM_PATH_PREFIXES
        )

        if should_no_cache and not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            add_never_cache_headers(response)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response


class LogoutCacheControlMiddleware:
    """
    Middleware to add cache control headers to logout responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add cache control headers to logout page
        if '/accounts/logout/' in request.path:
            add_never_cache_headers(response)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
