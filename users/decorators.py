from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.core.exceptions import PermissionDenied

def verified_member_required(view_func):
    """
    Decorator to restrict view access to verified members only.
    
    This decorator checks if the user is verified before allowing access to the view.
    Superusers bypass this verification check.
    
    Args:
        view_func: The view function to be decorated
        
    Returns:
        Wrapped view function that includes verification check
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Superusers bypass verification
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # Check if user is verified
            if not request.user.is_verified:
                messages.warning(
                    request, 
                    "Your membership requires verification before you can access this feature. "
                    "Please complete your profile and submit the membership form."
                )
                return redirect('profile')
                
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

def water_tender_required(view_func):
    """
    Decorator to restrict view access to water tenders or superusers.
    
    Args:
        view_func: The view function to be decorated
        
    Returns:
        Wrapped view function that includes water tender role check
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Check if user is a water tender or superuser
            if request.user.is_water_tender() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # User doesn't have permission
            messages.error(
                request, 
                "You don't have permission to access this page. This feature is restricted to water tenders and administrators."
            )
            return redirect('home')
                
        return redirect('account_login')
    
    return _wrapped_view

def water_tender_sector_required(view_func):
    """
    Decorator to restrict view access to water tenders managing a specific sector,
    or superusers.
    
    This decorator expects a 'sector_id' in the kwargs (URL parameters).
    
    Args:
        view_func: The view function to be decorated
        
    Returns:
        Wrapped view function that includes sector-specific permission check
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Superusers bypass sector check
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # Check if user is a water tender
            if request.user.is_water_tender():
                sector_id = kwargs.get('sector_id')
                if sector_id:
                    # Check if water tender manages this sector
                    if request.user.managed_sectors.filter(id=sector_id).exists():
                        return view_func(request, *args, **kwargs)
                
            # User doesn't have permission for this sector
            messages.error(
                request, 
                "You don't have permission to access this sector. This sector is not assigned to you."
            )
            return redirect('home')
                
        return redirect('account_login')
    
    return _wrapped_view 