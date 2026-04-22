from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def verified_member_required(view_func):
    """
    Decorator to restrict transaction access to verified members only.

    This decorator checks if the user is verified before allowing transactions.
    Non-verified users can view features but cannot rent or make transactions.
    Superusers bypass this verification check.

    Args:
        view_func: The view function to be decorated

    Returns:
        Wrapped view function that includes verification check
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if not request.user.is_verified:
                from notifications.models import UserNotification

                UserNotification.objects.create(
                    user=request.user,
                    notification_type='membership_required',
                    message='Please pay the P500 membership fee to be verified and access rental services. You can pay by Gcash or over the counter at the BUFIA office.',
                )

                messages.warning(
                    request,
                    'Membership verification required. Please pay the P500 membership fee to rent machines and make transactions. '
                    'You can pay by Gcash or visit the BUFIA office for over-the-counter payment.',
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
            if request.user.is_water_tender() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                "You don't have permission to access this page. This feature is restricted to water tenders and administrators.",
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
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if request.user.is_water_tender():
                sector_id = kwargs.get('sector_id')
                if sector_id and request.user.managed_sectors.filter(id=sector_id).exists():
                    return view_func(request, *args, **kwargs)

            messages.error(
                request,
                "You don't have permission to access this sector. This sector is not assigned to you.",
            )
            return redirect('home')

        return redirect('account_login')

    return _wrapped_view
