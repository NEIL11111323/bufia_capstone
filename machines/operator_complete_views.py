"""
Complete Operator Views - All functions and actions needed by operators
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
import json
from datetime import datetime, timedelta

from machines.models import Rental, Machine, HarvestReport
from notifications.notification_helpers import create_notification
from users.models import CustomUser


def is_operator(user):
    """Check if user is an operator"""
    return user.is_authenticated and user.role == 'operator'


def is_operator_or_admin(user):
    """Allow operator access and admin viewer access to the dashboard."""
    return user.is_authenticated and (user.role == 'operator' or user.is_superuser)


def _payment_ready_for_operator(rental):
    """Operators can only take tasks that are already payment-ready."""
    return (
        rental.payment_type == 'in_kind'
        or rental.payment_verified
        or rental.payment_status == 'paid'
    )


def _append_operator_note(rental, note):
    """Append a timestamped operator note without losing existing notes."""
    timestamp = timezone.now().strftime('%b %d, %Y %I:%M %p')
    entry = f'[{timestamp}] {note}'
    if rental.operator_notes:
        rental.operator_notes = f'{rental.operator_notes}\n{entry}'
    else:
        rental.operator_notes = entry


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
@user_passes_test(is_operator_or_admin)
def operator_main_dashboard(request):
    """
    Main operator dashboard with comprehensive overview
    """
    viewing_as_admin = False
    operator = request.user

    if request.user.is_superuser and request.GET.get('operator_id'):
        operator = get_object_or_404(
            CustomUser,
            id=request.GET.get('operator_id'),
            role=CustomUser.OPERATOR,
            is_active=True,
        )
        viewing_as_admin = True
    
    # Get current ongoing job (max 1)
    ongoing_job = Rental.objects.filter(
        assigned_operator=operator,
        status='ongoing'
    ).select_related('machine', 'user').first()
    
    # Get assigned jobs waiting for operator acceptance
    assigned_jobs = Rental.objects.filter(
        assigned_operator=operator,
        status__in=['approved', 'assigned']
    ).exclude(
        status='ongoing'
    ).select_related('machine', 'user').order_by('start_date')

    for job in assigned_jobs:
        job.payment_ready_for_operator = _payment_ready_for_operator(job)
    
    # Get completed jobs (recent)
    completed_jobs = Rental.objects.filter(
        assigned_operator=operator,
        status__in=['completed', 'finalized']
    ).select_related('machine', 'user').order_by('-actual_completion_time')[:5]
    
    # Get pending harvest jobs
    pending_harvest = Rental.objects.filter(
        assigned_operator=operator,
        payment_type='in_kind',
        status='ongoing',
        operator_status__in=['operating', 'harvest_ready']
    ).select_related('machine', 'user')
    
    # Calculate statistics
    stats = {
        'total_assigned': assigned_jobs.count(),
        'ongoing': 1 if ongoing_job else 0,
        'completed_today': Rental.objects.filter(
            assigned_operator=operator,
            status='completed',
            actual_completion_time__date=timezone.now().date()
        ).count(),
        'pending_harvest': pending_harvest.count(),
        'total_completed': Rental.objects.filter(
            assigned_operator=operator,
            status__in=['completed', 'finalized']
        ).count(),
    }
    
    # Get urgent jobs (overdue or due today)
    today = timezone.now().date()
    urgent_jobs = assigned_jobs.filter(
        Q(start_date__lt=today) | Q(start_date=today)
    )
    
    context = {
        'viewing_as_admin': viewing_as_admin,
        'operator_user': operator,
        'ongoing_job': ongoing_job,
        'assigned_jobs': assigned_jobs,
        'completed_jobs': completed_jobs,
        'pending_harvest': pending_harvest,
        'urgent_jobs': urgent_jobs,
        'stats': stats,
    }
    
    return render(request, 'machines/operator/operator_main_dashboard.html', context)


# ============================================================================
# JOB MANAGEMENT VIEWS
# ============================================================================

@login_required
@user_passes_test(is_operator)
def operator_all_jobs(request):
    """
    All jobs assigned to operator with filtering and pagination
    """
    operator = request.user
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    search = request.GET.get('search', '').strip()
    
    # Base queryset
    jobs = Rental.objects.filter(
        assigned_operator=operator
    ).select_related('machine', 'user')
    
    # Apply filters
    if status_filter == 'assigned':
        jobs = jobs.filter(status__in=['approved', 'assigned'])
    elif status_filter == 'ongoing':
        jobs = jobs.filter(status='ongoing')
    elif status_filter == 'completed':
        jobs = jobs.filter(status__in=['completed', 'finalized'])
    elif status_filter == 'pending_harvest':
        jobs = jobs.filter(
            payment_type='in_kind',
            status='ongoing',
            operator_status__in=['operating', 'harvest_ready']
        )
    
    if payment_filter == 'cash':
        jobs = jobs.filter(payment_type='cash')
    elif payment_filter == 'in_kind':
        jobs = jobs.filter(payment_type='in_kind')
    
    if search:
        jobs = jobs.filter(
            Q(machine__name__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(field_location__icontains=search)
        )
    
    # Order by priority: ongoing first, then by start date
    jobs = jobs.order_by(
        '-status',  # ongoing jobs first
        'start_date',
        '-created_at'
    )
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate filter counts
    all_jobs = Rental.objects.filter(assigned_operator=operator)
    current_ongoing_job = all_jobs.filter(status='ongoing').first()
    filter_counts = {
        'all': all_jobs.count(),
        'assigned': all_jobs.filter(status__in=['approved', 'assigned']).count(),
        'ongoing': all_jobs.filter(status='ongoing').count(),
        'completed': all_jobs.filter(status__in=['completed', 'finalized']).count(),
        'pending_harvest': all_jobs.filter(
            payment_type='in_kind',
            status='ongoing',
            operator_status__in=['operating', 'harvest_ready']
        ).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'jobs': page_obj.object_list,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'search': search,
        'filter_counts': filter_counts,
        'page_title': 'All Jobs',
        'today': timezone.now().date(),
        'current_ongoing_job_id': current_ongoing_job.id if current_ongoing_job else None,
    }
    
    return render(request, 'machines/operator/all_jobs.html', context)


@login_required
@user_passes_test(is_operator)
def operator_job_detail(request, rental_id):
    """
    Detailed view of a specific job with all actions
    """
    operator = request.user
    rental = get_object_or_404(
        Rental.objects.select_related('machine', 'user'),
        id=rental_id,
        assigned_operator=operator
    )
    
    has_ongoing = Rental.objects.filter(
        assigned_operator=operator,
        status='ongoing'
    ).exclude(id=rental.id).exists()

    # Determine available actions
    can_accept = (
        rental.status in ['approved', 'assigned']
        and _payment_ready_for_operator(rental)
        and not has_ongoing
    )
    can_start = False
    can_complete = rental.status == 'ongoing' and rental.payment_type != 'in_kind'
    can_report_harvest = (
        rental.payment_type == 'in_kind' and 
        rental.status == 'ongoing' and
        rental.operator_status in ['operating', 'harvest_ready']
    )
    
    # Get harvest reports if any
    harvest_reports = HarvestReport.objects.filter(rental=rental).order_by('-report_timestamp')
    
    context = {
        'rental': rental,
        'can_accept': can_accept,
        'can_start': can_start and not has_ongoing,
        'can_complete': can_complete,
        'can_report_harvest': can_report_harvest,
        'has_ongoing': has_ongoing,
        'harvest_reports': harvest_reports,
    }
    
    return render(request, 'machines/operator/job_detail.html', context)


# ============================================================================
# JOB ACTION VIEWS
# ============================================================================

@login_required
@user_passes_test(is_operator)
def operator_accept_job(request, rental_id):
    """Accept an assigned job and begin operator work."""
    if request.method != 'POST':
        return redirect('machines:operator_job_detail', rental_id=rental_id)

    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)

    if rental.status not in ['approved', 'assigned']:
        messages.error(request, 'Cannot accept this task because it is no longer awaiting operator action.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)

    if not _payment_ready_for_operator(rental):
        messages.error(request, 'Cannot accept this task until payment is confirmed by admin.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)

    has_ongoing = Rental.objects.filter(
        assigned_operator=operator,
        status='ongoing'
    ).exclude(id=rental.id).exists()
    if has_ongoing:
        messages.error(request, 'Complete your current ongoing job before accepting another one.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)

    rental.status = 'ongoing'
    rental.workflow_state = 'in_progress'
    rental.operator_status = 'operating'
    rental.actual_handover_date = timezone.now()
    rental.operator_last_update_at = timezone.now()
    _append_operator_note(
        rental,
        f'Accepted by {operator.get_full_name() or operator.username} and started field work.',
    )
    rental.save(update_fields=[
        'status',
        'workflow_state',
        'operator_status',
        'actual_handover_date',
        'operator_last_update_at',
        'operator_notes',
        'updated_at',
    ])

    rental.machine.status = 'rented'
    rental.machine.save(update_fields=['status', 'updated_at'])

    create_notification(
        user=rental.user,
        notification_type='rental_status_update',
        message=f'Operator {operator.get_full_name() or operator.username} accepted the assigned task and is now working on {rental.machine.name}.',
        title='Task Accepted And Started',
        category='rental',
        priority='medium',
        related_object_id=rental.id
    )

    messages.success(request, f'Task accepted for {rental.machine.name}. This job is now active.')
    return redirect('machines:operator_job_detail', rental_id=rental.id)


@login_required
@user_passes_test(is_operator)
def operator_start_job(request, rental_id):
    """
    Start an assigned job with comprehensive validation
    """
    if request.method != 'POST':
        return redirect('machines:operator_main_dashboard')
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    # Validation checks
    if rental.status not in ['approved', 'assigned']:
        messages.error(request, f'❌ Cannot start job. Status is "{rental.status}" but must be "assigned" or "approved".')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # Check if operator already has an ongoing job
    has_ongoing = Rental.objects.filter(
        assigned_operator=operator,
        status='ongoing'
    ).exists()
    
    if has_ongoing:
        messages.error(request, '❌ You already have an ongoing job. Complete it first before starting a new one.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # Check payment status
    if rental.payment_status != 'paid':
        messages.error(request, '❌ Cannot start job. Payment not confirmed yet.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # Start the job
    rental.status = 'ongoing'
    rental.operator_status = 'traveling'  # Initial operator status
    rental.actual_handover_date = timezone.now()
    rental.save()
    
    # Update machine status
    rental.machine.status = 'rented'
    rental.machine.save()
    
    # Create notification
    create_notification(
        user=rental.user,
        notification_type='rental_job_started',
        message=f'Operator {operator.get_full_name()} has started working on {rental.machine.name}',
        title='Job Started',
        category='rental',
        priority='medium',
        related_object_id=rental.id
    )
    
    messages.success(request, f'✅ Job started: {rental.machine.name}. Status set to "Traveling to location".')
    return redirect('machines:operator_job_detail', rental_id=rental.id)


@login_required
@user_passes_test(is_operator)
def operator_update_status(request, rental_id):
    """
    Update job status (traveling → operating → harvest_ready, etc.)
    """
    if request.method != 'POST':
        return redirect('machines:operator_job_detail', rental_id=rental_id)
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    if rental.status != 'ongoing':
        messages.error(request, '❌ Can only update status for ongoing jobs.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    new_status = request.POST.get('operator_status')
    notes = request.POST.get('notes', '').strip()
    
    # Valid status transitions
    valid_statuses = ['traveling', 'operating', 'harvest_ready', 'completed']
    
    if new_status not in valid_statuses:
        messages.error(request, '❌ Invalid status selected.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # Update status
    rental.operator_status = new_status
    if notes:
        rental.operator_notes = notes
    rental.operator_last_update_at = timezone.now()
    rental.save()
    
    # Create notification for status update
    status_display = dict(Rental.OPERATOR_STATUS_CHOICES).get(new_status, new_status)
    create_notification(
        user=rental.user,
        notification_type='rental_status_update',
        message=f'Job status updated to: {status_display}',
        title='Job Status Update',
        category='rental',
        priority='low',
        related_object_id=rental.id
    )
    
    messages.success(request, f'✅ Status updated to: {status_display}')
    return redirect('machines:operator_job_detail', rental_id=rental.id)


@login_required
@user_passes_test(is_operator)
def operator_complete_job(request, rental_id):
    """
    Complete an ongoing job
    """
    if request.method != 'POST':
        return redirect('machines:operator_job_detail', rental_id=rental_id)
    
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    if rental.status != 'ongoing':
        messages.error(request, f'❌ Cannot complete job. Status is "{rental.status}" but must be "ongoing".')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # For in-kind payments, check if harvest is reported
    if rental.payment_type == 'in_kind' and not rental.total_harvest_sacks:
        messages.error(request, '❌ Cannot complete in-kind job without harvest report.')
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # Complete the job
    rental.status = 'completed'
    rental.workflow_state = 'work_completed'
    rental.operator_status = 'completed'
    rental.actual_completion_time = timezone.now()
    _append_operator_note(
        rental,
        f'Work completed by {operator.get_full_name() or operator.username}.',
    )
    rental.save(update_fields=[
        'status',
        'workflow_state',
        'operator_status',
        'actual_completion_time',
        'operator_notes',
        'updated_at',
    ])
    
    # Update machine status back to available
    rental.machine.status = 'available'
    rental.machine.save()
    
    # Create notification
    create_notification(
        user=rental.user,
        notification_type='rental_job_completed',
        message=f'Operator {operator.get_full_name()} has completed work on {rental.machine.name}',
        title='Job Completed',
        category='rental',
        priority='high',
        related_object_id=rental.id
    )
    
    messages.success(request, f'✅ Job completed: {rental.machine.name}. Sent to admin for verification.')
    return redirect('machines:operator_main_dashboard')


# ============================================================================
# HARVEST MANAGEMENT VIEWS
# ============================================================================

@login_required
@user_passes_test(is_operator)
def operator_harvest_jobs(request):
    """
    View all in-kind jobs requiring harvest management
    """
    operator = request.user
    
    # Get in-kind jobs at different stages
    pending_harvest = Rental.objects.filter(
        assigned_operator=operator,
        payment_type='in_kind',
        status='ongoing',
        operator_status__in=['operating', 'harvest_ready']
    ).select_related('machine', 'user')
    
    completed_harvest = Rental.objects.filter(
        assigned_operator=operator,
        payment_type='in_kind',
        status__in=['completed', 'finalized'],
        total_harvest_sacks__isnull=False
    ).select_related('machine', 'user').order_by('-actual_completion_time')
    
    # Calculate harvest statistics
    total_harvest = completed_harvest.aggregate(
        total_sacks=Sum('total_harvest_sacks')
    )['total_sacks'] or 0
    
    total_bufia_share = completed_harvest.aggregate(
        total_share=Sum('organization_share_required')
    )['total_share'] or 0
    
    context = {
        'pending_harvest': pending_harvest,
        'completed_harvest': completed_harvest,
        'total_harvest': total_harvest,
        'total_bufia_share': total_bufia_share,
        'page_title': 'Harvest Management',
    }
    
    return render(request, 'machines/operator/harvest_jobs.html', context)


@login_required
@user_passes_test(is_operator)
def operator_report_harvest(request, rental_id):
    """
    Report harvest for in-kind payment jobs
    """
    operator = request.user
    rental = get_object_or_404(Rental, id=rental_id, assigned_operator=operator)
    
    if request.method == 'POST':
        try:
            total_harvest = Decimal(request.POST.get('total_harvest', '0'))
            notes = request.POST.get('notes', '').strip()
            
            if total_harvest <= 0:
                messages.error(request, '❌ Harvest amount must be greater than zero.')
                return redirect('machines:operator_job_detail', rental_id=rental.id)
            
            if rental.payment_type != 'in_kind':
                messages.error(request, 'Harvest reporting is only available for in-kind rentals.')
                return redirect('machines:operator_job_detail', rental_id=rental.id)

            if rental.status != 'ongoing':
                messages.error(request, 'Harvest can only be submitted for an active in-kind job.')
                return redirect('machines:operator_job_detail', rental_id=rental.id)

            bufia_share, member_share = rental.calculate_harvest_shares(total_harvest)
            if bufia_share <= 0 and member_share <= 0:
                messages.error(request, 'Unable to compute harvest shares for this machine. Check the in-kind share setup.')
                return redirect('machines:operator_job_detail', rental_id=rental.id)
            
            # Update rental with harvest data
            rental.total_harvest_sacks = total_harvest
            rental.total_rice_sacks_harvested = total_harvest
            rental.bufia_share = bufia_share
            rental.organization_share_required = bufia_share
            rental.member_share = member_share
            rental.status = 'completed'
            rental.workflow_state = 'harvest_report_submitted'
            rental.operator_status = 'harvest_reported'
            rental.operator_reported_at = timezone.now()
            rental.settlement_status = 'waiting_for_delivery'
            rental.settlement_type = 'after_harvest'
            rental.payment_status = 'pending'
            rental.actual_completion_time = timezone.now()

            if notes:
                _append_operator_note(rental, notes)
            else:
                _append_operator_note(
                    rental,
                    f'Harvest submitted: {total_harvest} sacks. BUFIA share computed at {bufia_share} sacks.',
                )

            rental.save(update_fields=[
                'total_harvest_sacks',
                'total_rice_sacks_harvested',
                'bufia_share',
                'organization_share_required',
                'member_share',
                'status',
                'workflow_state',
                'operator_status',
                'operator_reported_at',
                'settlement_status',
                'settlement_type',
                'payment_status',
                'actual_completion_time',
                'operator_notes',
                'updated_at',
            ])

            rental.machine.status = 'available'
            rental.machine.save(update_fields=['status', 'updated_at'])
            
            # Create harvest report
            HarvestReport.objects.create(
                rental=rental,
                total_rice_sacks_harvested=total_harvest,
                recorded_by_admin=None,
                verification_notes=f'Operator-submitted harvest: {total_harvest} sacks'
            )
            
            # Create notification
            create_notification(
                user=rental.user,
                notification_type='harvest_reported',
                message=f'Harvest reported: {total_harvest} sacks. BUFIA share: {bufia_share} sacks.',
                title='Harvest Report Submitted',
                category='rental',
                priority='high',
                related_object_id=rental.id
            )
            
            messages.success(
                request,
                f'✅ Harvest reported: {total_harvest} sacks. BUFIA share: {bufia_share} sacks. '
                f'Admin now only needs to confirm delivery to BUFIA.'
            )
            
        except (InvalidOperation, ValueError):
            messages.error(request, '❌ Invalid harvest amount. Please enter a valid number.')
        
        return redirect('machines:operator_job_detail', rental_id=rental.id)
    
    # GET request - show form
    context = {
        'rental': rental,
    }
    return render(request, 'machines/operator/report_harvest.html', context)


# ============================================================================
# UTILITY VIEWS
# ============================================================================

@login_required
@user_passes_test(is_operator)
def operator_machines(request):
    """
    View available machines (read-only for operators)
    """
    machines = Machine.objects.filter(
        status__in=['available', 'maintenance']
    ).order_by('name')
    
    context = {
        'machines': machines,
        'page_title': 'Available Machines',
    }
    
    return render(request, 'machines/operator/machines.html', context)


@login_required
@user_passes_test(is_operator)
def operator_profile(request):
    """
    Operator profile and statistics
    """
    operator = request.user
    
    # Calculate operator statistics
    all_jobs = Rental.objects.filter(assigned_operator=operator)
    
    stats = {
        'total_jobs': all_jobs.count(),
        'completed_jobs': all_jobs.filter(status__in=['completed', 'finalized']).count(),
        'ongoing_jobs': all_jobs.filter(status='ongoing').count(),
        'total_harvest': all_jobs.filter(
            payment_type='in_kind',
            total_harvest_sacks__isnull=False
        ).aggregate(total=Sum('total_harvest_sacks'))['total'] or 0,
        'jobs_this_month': all_jobs.filter(
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).count(),
    }
    
    # Recent activity
    recent_jobs = all_jobs.order_by('-updated_at')[:10]
    
    context = {
        'operator': operator,
        'stats': stats,
        'recent_jobs': recent_jobs,
    }
    
    return render(request, 'machines/operator/profile.html', context)


# ============================================================================
# AJAX/API VIEWS
# ============================================================================

@login_required
@user_passes_test(is_operator)
def operator_job_status_api(request, rental_id):
    """
    API endpoint to get current job status (for live updates)
    """
    operator = request.user
    
    try:
        rental = Rental.objects.get(id=rental_id, assigned_operator=operator)
        
        data = {
            'status': rental.status,
            'operator_status': rental.operator_status,
            'operator_status_display': rental.get_operator_status_display(),
            'last_update': rental.operator_last_update_at.isoformat() if rental.operator_last_update_at else None,
            'duration': None,
        }
        
        # Calculate duration if job is ongoing
        if rental.status == 'ongoing' and rental.actual_handover_date:
            duration = timezone.now() - rental.actual_handover_date
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            data['duration'] = f"{hours}h {minutes}m"
        
        return JsonResponse(data)
        
    except Rental.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)


@login_required
@user_passes_test(is_operator)
def operator_dashboard_stats_api(request):
    """
    API endpoint for dashboard statistics (for auto-refresh)
    """
    operator = request.user
    
    stats = {
        'assigned_jobs': Rental.objects.filter(
            assigned_operator=operator,
            status__in=['approved', 'assigned']
        ).exclude(status='ongoing').count(),
        
        'ongoing_jobs': Rental.objects.filter(
            assigned_operator=operator,
            status='ongoing'
        ).count(),
        
        'completed_today': Rental.objects.filter(
            assigned_operator=operator,
            status='completed',
            actual_completion_time__date=timezone.now().date()
        ).count(),
        
        'pending_harvest': Rental.objects.filter(
            assigned_operator=operator,
            payment_type='in_kind',
            status='ongoing',
            operator_status__in=['operating', 'harvest_ready']
        ).count(),
    }
    
    return JsonResponse(stats)
