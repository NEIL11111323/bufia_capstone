"""
Custom allauth adapters for BUFIA
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.password_validation import (
    UserAttributeSimilarityValidator,
    get_default_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.urls import reverse
from urllib.parse import urlparse


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to redirect users to the right post-login dashboard.
    """

    def _normalize_operator_permissions(self, user):
        """
        Operators use their own dashboard and should not keep staff/admin flags.
        """
        if (
            user.is_authenticated
            and user.role == user.OPERATOR
            and user.is_staff
            and not user.is_superuser
        ):
            user.is_staff = False
            user.save(update_fields=['is_staff'])

    def _default_redirect_for_user(self, user):
        if not user.is_authenticated:
            return reverse('dashboard')

        self._normalize_operator_permissions(user)

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

    def clean_password(self, password, user=None):
        """
        Keep Django password validation, but allow passwords that are merely
        similar to username/email. Only exact matches are rejected.
        """
        validators = [
            validator
            for validator in get_default_password_validators()
            if not isinstance(validator, UserAttributeSimilarityValidator)
        ]
        validate_password(password, user=user, password_validators=validators)

        exact_match_targets = []
        if user is not None:
            username = (getattr(user, 'username', '') or '').strip()
            email = (getattr(user, 'email', '') or '').strip()
            if username:
                exact_match_targets.append(('username', username))
            if email:
                exact_match_targets.append(('email address', email))

        normalized_password = (password or '').strip().casefold()
        for label, value in exact_match_targets:
            if normalized_password and normalized_password == value.casefold():
                raise ValidationError(
                    f"Your password must not be exactly the same as your {label}.",
                    code='password_too_similar',
                )

        return password
    
    def get_login_redirect_url(self, request):
        """
        Redirect users to the correct dashboard and prevent redirect loops
        caused by landing on pages they do not have permission to access.
        """
        user = request.user
        self._normalize_operator_permissions(user)

        requested_next = request.POST.get('next') or request.GET.get('next') or ''
        parsed_next = urlparse(requested_next).path if requested_next else ''

        if parsed_next and self._can_access_target(user, parsed_next):
            return requested_next

        return self._default_redirect_for_user(user)
