from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, reverse

class VerificationCheckMiddleware:
    """
    Middleware that performs global verification checks.
    
    This middleware checks if the user is verified before allowing access to certain paths.
    It specifically targets machine rental and rice mill features.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip verification check if:
        # 1. User is not authenticated
        # 2. User is superuser
        # 3. Request path is in exempt URLs
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        if request.user.is_superuser:
            return self.get_response(request)
            
        # Define exempt paths that don't require verification
        exempt_paths = [
            '/profile/',
            '/profile/edit/',
            '/profile/photo/update/',
            '/profile/password/change/',
            '/profile/membership/submit/',
            '/accounts/logout/',
            '/admin/',
            '/',
            '/dashboard/',
        ]
        
        # Allow access to static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # Check if current path is exempt
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)
            
        # Check verification status for restricted paths
        if (request.path.startswith('/machines/') or 
            request.path.startswith('/rice_mill/') or 
            'rent' in request.path or 
            'schedule' in request.path) and not request.user.is_verified:
            
            # Determine the current URL name to avoid redirects to restricted areas
            try:
                url_name = resolve(request.path_info).url_name
                # Skip middleware check for certain view names if needed
                exempt_views = ['home', 'dashboard', 'profile']
                if url_name in exempt_views:
                    return self.get_response(request)
            except:
                pass
            
            messages.warning(
                request,
                "Your membership requires verification before you can access this feature. "
                "Please complete your profile and submit the membership form."
            )
            return redirect('profile')
            
        return self.get_response(request) 