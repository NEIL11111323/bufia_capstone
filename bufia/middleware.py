"""
Middleware for BUFIA project
"""
from django.utils.cache import add_never_cache_headers
from django.contrib.auth.decorators import login_required


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
    Middleware to prevent caching of authenticated pages.
    This prevents users from accessing authenticated pages via browser back button after logout.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add no-cache headers for authenticated users on protected pages
        if request.user.is_authenticated:
            # Exclude static files and media
            if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
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
