"""
Custom allauth adapters for BUFIA
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from urllib.parse import urlparse


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to redirect users to the right post-login dashboard.
    """

    def _default_redirect_for_user(self, user):
        if not user.is_authenticated:
            return reverse('dashboard')

        if user.role == user.OPERATOR:
            return reverse('machines:operator_simple_dashboard')

        if user.is_staff or user.is_superuser or user.role == user.SUPERUSER:
            return reverse('dashboard')

        return reverse('dashboard')

    def _can_access_target(self, user, target_path):
        if not target_path:
            return False

        if target_path.startswith('/machines/admin/'):
            return user.is_staff or user.is_superuser or user.role == user.SUPERUSER

        if target_path.startswith('/machines/operator/'):
            return user.role == user.OPERATOR or user.is_superuser

        return True
    
    def get_login_redirect_url(self, request):
        """
        Redirect users to the correct dashboard and prevent redirect loops
        caused by landing on pages they do not have permission to access.
        """
        user = request.user

        requested_next = request.POST.get('next') or request.GET.get('next') or ''
        parsed_next = urlparse(requested_next).path if requested_next else ''

        if parsed_next and self._can_access_target(user, parsed_next):
            return requested_next

        return self._default_redirect_for_user(user)
