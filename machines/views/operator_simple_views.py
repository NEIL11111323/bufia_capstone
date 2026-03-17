from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from machines.models import Rental
from notifications.notification_helpers import create_notification

def is_operator(user):
    return user.is_authenticated and user.role == 'operator'

@login_required
@user_passes_test(is_operator)
def operator_simple_dashboard(request):
    """
    Simplified operator dashboard with only essential functions:
    - Current ongoing job
    - Assigned jobs list
    - Completed jobs history
    """
    operator = request.user
    
    # Get current ongoing job (max 1)
    ongoing_job = Rental.objects.filter(
        operator=operator,
        status='ongoing'
    ).first()
    
    # Get assigned jobs (not started yet)
    assigned_jobs = Rental.objects.filter(
        operator=operator,
        status='assigned'
    ).order_by('start_date')
    
    # Get completed jobs
    completed_jobs = Rental.objects.filter(
        operator=operator,
        status__in=['completed', 'finalized']
    ).order_by('-end_time')[:10]  # Last 10 completed jobs
    
    context = {
        'ongoing_job': ongoing_job,
        'assigned_jobs': assigned_jobs,
        'completed_jobs': completed_jobs,
    }
    
    return render(request, 'machines/operator/simple_dashboard.html', context)


@login_required
@user_passes_test(is_operator)
def operator_start_job(request, rental_id):
    """
    Start an assigned job.
    Rule: Operator can only have ONE ongoing job at a time.
    """
    if request.method != 'POST':
        return redirect('machines:operator_simple_dashboard')
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, operator=operator, status='assigned')
    
    # Check if operator already has an ongoing job
    has_ongoing = Rental.objects.filter(
        operator=operator,
        status='ongoing'
    ).exists()
    
    if has_ongoing:
        messages.error(request, '❌ You already have an ongoing job. Complete it first before starting a new one.')
        return redirect('machines:operator_simple_dashboard')
    
    # Start the job
    rental.status = 'ongoing'
    rental.start_time = timezone.now()
    rental.save()
    
    # Notify admin
    create_notification(
        user=rental.user,  # Farmer/Admin who created the rental
        title='Job Started',
        message=f'Operator {operator.get_full_name()} has started working on {rental.machine.name}',
        category='rental',
        priority='medium',
        related_rental=rental
    )
    
    messages.success(request, f'✅ Job started: {rental.machine.name}')
    return redirect('machines:operator_simple_dashboard')


@login_required
@user_passes_test(is_operator)
def operator_complete_job(request, rental_id):
    """
    Complete the ongoing job.
    """
    if request.method != 'POST':
        return redirect('machines:operator_simple_dashboard')
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, operator=operator, status='ongoing')
    
    # Complete the job
    rental.status = 'completed'
    rental.end_time = timezone.now()
    rental.save()
    
    # Notify admin
    create_notification(
        user=rental.user,  # Farmer/Admin who created the rental
        title='Job Completed',
        message=f'Operator {operator.get_full_name()} has completed work on {rental.machine.name}',
        category='rental',
        priority='high',
        related_rental=rental
    )
    
    messages.success(request, f'✅ Job completed: {rental.machine.name}. Sent to admin for verification.')
    return redirect('machines:operator_simple_dashboard')
