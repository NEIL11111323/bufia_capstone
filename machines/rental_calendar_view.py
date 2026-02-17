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
    """
    Create rental with calendar view showing real-time availability
    """
    if request.method == 'POST':
        form = RentalForm(request.POST)
        
        if form.is_valid():
            try:
                # Lock the machine row to prevent race conditions
                machine = Machine.objects.select_for_update().get(
                    pk=form.cleaned_data['machine'].pk
                )
                
                # Double-check availability within transaction
                is_available, conflicts = Rental.check_availability(
                    machine=machine,
                    start_date=form.cleaned_data['start_date'],
                    end_date=form.cleaned_data['end_date']
                )
                
                if not is_available:
                    conflict = conflicts.first()
                    messages.error(
                        request,
                        f'Sorry, this machine was just booked from '
                        f'{conflict.start_date} to {conflict.end_date}. '
                        f'Please select different dates.'
                    )
                else:
                    # Create rental
                    rental = form.save(commit=False)
                    rental.user = request.user
                    rental.save()
                    
                    # Create notification
                    UserNotification.objects.create(
                        user=request.user,
                        notification_type='rental_submitted',
                        message=f'Your rental request for {machine.name} has been submitted.',
                        related_object_id=rental.id
                    )
                    
                    messages.success(
                        request,
                        'Rental request submitted successfully! Please complete payment.'
                    )
                    
                    return redirect('create_rental_payment', rental_id=rental.pk)
                    
            except Machine.DoesNotExist:
                messages.error(request, 'Selected machine does not exist.')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    else:
        initial = {'machine': machine_pk} if machine_pk else {}
        form = RentalForm(initial=initial)
    
    # Get machine object if provided
    machine = None
    if machine_pk:
        try:
            machine = Machine.objects.get(pk=machine_pk)
        except Machine.DoesNotExist:
            pass
    
    # Get all machines for dropdown (show all, let calendar show availability)
    all_machines = Machine.objects.all().order_by('name')
    
    return render(request, 'machines/rental_form_with_calendar.html', {
        'form': form,
        'machine': machine,
        'all_machines': all_machines,
    })
