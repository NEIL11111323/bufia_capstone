from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def verification_status_badge(user):
    """
    Generate a badge showing the user's verification status.
    
    Args:
        user: The user object to check verification status for
        
    Returns:
        HTML badge element showing verification status
    """
    if not user.is_authenticated:
        return ""
        
    if user.is_superuser:
        return mark_safe('<span class="badge bg-primary">Admin</span>')
        
    if user.is_verified:
        return mark_safe('<span class="badge bg-success">Verified Member</span>')
    
    if hasattr(user, 'membership_application') and user.membership_form_submitted:
        return mark_safe('<span class="badge bg-warning text-dark">Pending Verification</span>')
        
    return mark_safe('<span class="badge bg-danger">Unverified</span>')
    
@register.filter
def is_verified_or_exempt(user):
    """
    Check if user is verified or exempt from verification (admin).
    
    Args:
        user: The user object to check
        
    Returns:
        Boolean indicating if user can access verified-only features
    """
    if not user.is_authenticated:
        return False
        
    return user.is_verified or user.is_superuser
    
@register.simple_tag
def verification_alert(user):
    """
    Generate an alert message for unverified users.
    
    Args:
        user: The user object to check verification status for
        
    Returns:
        HTML alert element with verification instructions
    """
    if not user.is_authenticated or user.is_verified or user.is_superuser:
        return ""
        
    return mark_safe('''
    <div class="alert alert-warning verification-alert mb-4" role="alert">
        <div class="d-flex align-items-center">
            <div class="flex-shrink-0 alert-icon">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="flex-grow-1 ms-3">
                <h5 class="alert-heading">Membership Verification Required</h5>
                <p class="mb-0">Your account needs to be verified before you can access all features. Please complete your profile and submit the membership verification form.</p>
            </div>
            <div class="flex-shrink-0">
                <a href="/profile/membership/submit/" class="btn btn-sm btn-warning">Verify Now</a>
            </div>
        </div>
    </div>
    ''')

@register.simple_tag
def get_membership_application(user):
    """
    Get a user's membership application if it exists.
    
    Args:
        user: The user object to get membership application for
        
    Returns:
        The membership application object or None
    """
    if hasattr(user, 'membership_application'):
        return user.membership_application
    return None 