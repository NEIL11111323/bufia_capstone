from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from machines.models import Rental
from notifications.notification_helpers import create_notification

ACTIVE_OPERATOR_STATUSES = ['accepted', 'traveling', 'operating', 'harvest_ready']

def is_operator(user):
    return user.is_authenticated and user.role == 'operator'


User = get_user_model()


def _active_operator_jobs_queryset(operator):
    return Rental.objects.filter(
        assigned_operator=operator,
        operator_status__in=ACTIVE_OPERATOR_STATUSES,
    ).exclude(
        status__in=['completed', 'cancelled', 'rejected']
    )


def _operator_finished_jobs_queryset(operator):
    return Rental.objects.filter(
        assigned_operator=operator,
    ).filter(
        Q(status__in=['completed', 'finalized']) |
        Q(operator_status='completed')
    )

@login_required
@user_passes_test(is_operator)
def operator_simple_dashboard(request):
    """
    Redirect to the main dashboard for backward compatibility
    """
    return operator_main_dashboard(request)


@login_required
@user_passes_test(is_operator)
def operator_main_dashboard(request):
    """
    Comprehensive operator dashboard with all main functions:
    - Current ongoing job with live duration
    - All assigned jobs (approved rentals with assigned operator)
    - Recent completed jobs
    - Statistics and quick actions
    """
    operator = request.user
    
    # Get current ongoing job (max 1)
    ongoing_job = _active_operator_jobs_queryset(operator).select_related('machine', 'user').first()
    
    # Get assigned jobs (approved rentals with assigned operator OR status='assigned')
    assigned_jobs = Rental.objects.filter(
        assigned_operator=operator,
        status__in=['approved', 'assigned']  # Include both approved and assigned
    ).exclude(
        pk__in=_active_operator_jobs_queryset(operator).values('pk')
    ).select_related('machine', 'user').order_by('start_date')
    
    # Get completed jobs
    completed_jobs = _operator_finished_jobs_queryset(operator).select_related('machine', 'user').order_by('-actual_completion_time')[:10]  # Last 10 completed jobs
    
    # Get pending harvest count (in-kind jobs waiting for harvest report)
    pending_harvest_count = Rental.objects.filter(
        assigned_operator=operator,
        payment_type='in_kind',
        workflow_state='in_progress',
        operator_status__in=['operating', 'harvest_ready']
    ).count()
    
    context = {
        'ongoing_job': ongoing_job,
        'assigned_jobs': assigned_jobs,
        'completed_jobs': completed_jobs,
        'pending_harvest_count': pending_harvest_count,
    }
    
    return render(request, 'machines/operator/operator_main_dashboard.html', context)


@login_required
@user_passes_test(is_operator)
def operator_all_jobs(request):
    """Show all jobs assigned to this operator"""
    operator = request.user
    
    # Get all jobs assigned to this operator
    all_jobs = Rental.objects.filter(
        assigned_operator=operator
    ).order_by('-created_at')
    
    context = {
        'all_jobs': all_jobs,
        'page_title': 'All Jobs',
    }
    
    return render(request, 'machines/operator/jobs.html', context)


@login_required
@user_passes_test(is_operator)
def operator_ongoing_jobs(request):
    """Show only ongoing jobs with comprehensive status tracking"""
    operator = request.user
    
    # Get ongoing jobs - include both status='ongoing' and any with operator_status indicating work in progress
    ongoing_jobs = _active_operator_jobs_queryset(operator).select_related('machine', 'user').order_by('-actual_handover_date')
    
    # Also include jobs that are actively being worked on
    in_progress_jobs = Rental.objects.filter(
        assigned_operator=operator,
        status__in=['approved', 'assigned'],
        operator_status__in=['traveling', 'operating', 'harvest_ready']
    ).select_related('machine', 'user')
    
    # Combine and remove duplicates
    all_ongoing = (ongoing_jobs | in_progress_jobs).distinct().order_by('-actual_handover_date', '-updated_at')
    
    context = {
        'ongoing_jobs': all_ongoing,
        'page_title': 'Ongoing Jobs',
    }
    
    return render(request, 'machines/operator/work.html', context)


@login_required
@user_passes_test(is_operator)
def operator_completed_jobs(request):
    """Show completed jobs"""
    operator = request.user
    
    # Get completed jobs
    completed_jobs = _operator_finished_jobs_queryset(operator).order_by('-actual_completion_time')
    
    context = {
        'completed_jobs': completed_jobs,
        'page_title': 'Completed Jobs',
    }
    
    return render(request, 'machines/operator/jobs.html', context)


@login_required
@user_passes_test(is_operator)
def operator_job_detail(request, rental_id):
    """Show detailed view of a specific job"""
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    context = {
        'rental': rental,
        'can_start': rental.status in ['approved', 'assigned'] and rental.payment_status == 'paid',
        'can_complete': rental.workflow_state == 'in_progress' and rental.operator_status not in ['unassigned', 'assigned', 'completed', 'harvest_reported'],
    }
    
    return render(request, 'machines/operator/job_detail.html', context)


@login_required
@user_passes_test(is_operator)
def operator_start_job(request, rental_id):
    """
    Start an assigned job.
    CORE LOGIC: 
    - Only ASSIGNED jobs can be started
    - Operator can only have ONE ongoing job at a time
    - Status: ASSIGNED → ONGOING
    """
    if request.method != 'POST':
        return redirect('machines:operator_simple_dashboard')
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    # RULE 1: Only approved/assigned jobs can be started
    if rental.status not in ['approved', 'assigned']:
        messages.error(request, f'Cannot start job. Status is "{rental.status}" but must be "approved" or "assigned".')
        return redirect('machines:operator_simple_dashboard')
    
    # RULE 2: Check if operator already has an ongoing job
    has_ongoing = _active_operator_jobs_queryset(operator).exclude(id=rental.id).exists()
    
    if has_ongoing:
        messages.error(request, 'You already have an ongoing job. Complete it first before starting a new one.')
        return redirect('machines:operator_simple_dashboard')
    
    # RULE 3: Payment must be confirmed before starting
    if rental.payment_status != 'paid':
        messages.error(request, 'Cannot start job. Payment not confirmed yet.')
        return redirect('machines:operator_simple_dashboard')
    
    # ✅ START THE JOB - Status transition: ASSIGNED → ONGOING
    rental.status = 'approved'
    rental.workflow_state = 'in_progress'
    rental.operator_status = 'traveling'  # Initial operator status
    rental.actual_handover_date = timezone.now()  # Record when operator took over
    rental.save(update_fields=['status', 'workflow_state', 'operator_status', 'actual_handover_date', 'updated_at'])
    
    rental.machine.sync_status()
    
    # Notify admin
    create_notification(
        user=rental.user,  # Farmer/Admin who created the rental
        notification_type='rental_job_started',
        message=f'Operator {operator.get_full_name()} has started working on {rental.machine.name}',
        title='Job Started',
        category='rental',
        priority='medium',
        related_object_id=rental.id
    )
    
    messages.success(request, f'Job started: {rental.machine.name}. Status set to "Traveling to location".')
    return redirect('machines:operator_ongoing_jobs')  # Redirect to ongoing jobs to show the started job


@login_required
@user_passes_test(is_operator)
def operator_complete_job(request, rental_id):
    """
    Complete the ongoing job.
    CORE LOGIC:
    - Only ONGOING jobs can be completed
    - Status: ONGOING → COMPLETED
    """
    if request.method != 'POST':
        return redirect('machines:operator_simple_dashboard')
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    # RULE: Only ongoing jobs can be completed
    if rental.workflow_state != 'in_progress' and rental.operator_status not in ['traveling', 'operating', 'harvest_ready']:
        messages.error(request, f'Cannot complete job. Current workflow is "{rental.workflow_state}" and the task is not active.')
        return redirect('machines:operator_simple_dashboard')
    
    # Operator finishes the field work, but admin still validates the final completion.
    rental.status = 'approved'
    rental.workflow_state = 'in_progress'
    rental.operator_status = 'completed'
    rental.actual_completion_time = timezone.now()  # Record when job was completed
    rental.save(update_fields=['status', 'workflow_state', 'operator_status', 'actual_completion_time', 'updated_at'])

    rental.sync_machine_status()
    
    # Notify admin
    create_notification(
        user=rental.user,  # Farmer/Admin who created the rental
        notification_type='rental_job_completed',
        message=f'Operator {operator.get_full_name()} has completed work on {rental.machine.name}. BUFIA admin will validate the completion next.',
        title='Operator Finished The Job',
        category='rental',
        priority='high',
        related_object_id=rental.id
    )

    admins = User.objects.filter(is_active=True, is_staff=True).exclude(role='operator')
    for admin_user in admins:
        create_notification(
            user=admin_user,
            notification_type='rental_status_update',
            message=(
                f'Operator {operator.get_full_name() or operator.username} marked '
                f'{rental.machine.name} as completed for {rental.customer_display_name}. '
                f'Admin validation is still required.'
            ),
            title='Operator Completion Waiting For Validation',
            category='rental',
            priority='important',
            related_object_id=rental.id,
            action_url=f'/machines/admin/rental/{rental.id}/approve/',
        )
    
    messages.success(request, f'Job completed: {rental.machine.name}. It is now waiting for admin validation.')
    return redirect('machines:operator_simple_dashboard')
