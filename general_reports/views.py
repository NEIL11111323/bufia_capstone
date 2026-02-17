from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def dashboard(request):
    """General reports dashboard for admins"""
    context = {
        'page_title': 'General Reports',
    }
    return render(request, 'general_reports/dashboard.html', context)
