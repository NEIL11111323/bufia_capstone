from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from bufia.models import Payment
from machines.models import Machine, Rental

def is_superuser(user):
    return user.is_superuser


User = get_user_model()

@login_required
@user_passes_test(is_superuser)
def dashboard(request):
    """General reports dashboard for admins"""
    context = {
        'page_title': 'General Reports',
        'overview_stats': {
            'total_rentals': Rental.objects.count(),
            'in_kind_rentals': Rental.objects.filter(payment_type='in_kind').count(),
            'completed_payments': Payment.objects.filter(status='completed').count(),
            'verified_members': User.objects.filter(role=User.REGULAR_USER, is_verified=True).count(),
            'active_machines': Machine.objects.filter(status='available').count(),
        },
        'quick_links': {
            'sector_reports': Rental.objects.filter(
                user__membership_application__assigned_sector__isnull=False
            ).values('user__membership_application__assigned_sector').distinct().count(),
            'cash_rentals': Rental.objects.exclude(payment_type='in_kind').count(),
        }
    }
    return render(request, 'general_reports/dashboard.html', context)
