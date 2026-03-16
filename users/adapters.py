"""
Custom allauth adapters for BUFIA
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to redirect operators to their dashboard after login
    """
    
    def get_login_redirect_url(self, request):
        """
        Redirect operators to operator dashboard, others to regular dashboard
        """
        user = request.user
        
        # Redirect operators (staff but not superuser) to operator dashboard
        if user.is_authenticated and user.is_staff and not user.is_superuser:
            return reverse('machines:operator_dashboard')
        
        # Default redirect for regular users and admins
        return super().get_login_redirect_url(request)
