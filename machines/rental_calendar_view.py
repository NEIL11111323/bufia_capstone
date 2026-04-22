"""
Simplified rental view with calendar integration
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Machine, Rental
from .forms import RentalForm
from users.decorators import verified_member_required
from notifications.models import UserNotification


@login_required
@verified_member_required
@transaction.atomic
def rental_create_with_calendar(request, machine_pk=None):
    """Legacy route that now forwards to the unified enhanced rental form."""
    if machine_pk:
        return redirect('machines:rental_create_for_machine', machine_id=machine_pk)
    return redirect('machines:rental_create')
