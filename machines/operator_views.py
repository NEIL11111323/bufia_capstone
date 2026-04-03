from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from notifications.models import UserNotification
from notifications.operator_notifications import (
    notify_operator_job_assigned,
    notify_operator_job_updated,
    notify_operator_harvest_approved,
    notify_operator_job_completed,
    get_operator_notification_count,
)

from .models import HarvestReport, Machine, Rental


User = get_user_model()


def _is_operator_user(user):
    """Check if user has operator role"""
    return user.is_authenticated and user.role == User.OPERATOR


def _notify_admins(message, rental_id, *, exclude_user_id=None):
    admins = User.objects.filter(is_active=True, is_staff=True).exclude(role='operator')
    if exclude_user_id:
        admins = admins.exclude(pk=exclude_user_id)
    notifications = [
        UserNotification(
            user=admin,
            notification_type='rental_update',
            message=message,
            related_object_id=rental_id,
        )
        for admin in admins
    ]
    if notifications:
        UserNotification.objects.bulk_create(notifications)


@login_required
def operator_dashboard(request):
    """Professional operator dashboard - operators see their own, admins can view any"""
    
    # Check if admin is viewing another operator's dashboard
    operator_id = request.GET.get('operator_id')
    
    if operator_id and request.user.is_superuser:
        # Admin viewing specific operator's dashboard
        try:
            operator_user = User.objects.get(id=operator_id, role=User.OPERATOR)
            viewing_as_admin = True
        except User.DoesNotExist:
            messages.error(request, "Operator not found.")
            return redirect('machines:operator_overview')
    elif _is_operator_user(request.user):
        # Operator viewing their own dashboard
        operator_user = request.user
        viewing_as_admin = False
    else:
        # Not authorized
        messages.error(request, "You don't have permission to access the operator dashboard.")
        return redirect('dashboard')

    all_jobs = Rental.objects.select_related('machine', 'user').filter(
        assigned_operator=operator_user
    )

    stats = {
        'active': all_jobs.exclude(status__in=['completed', 'cancelled', 'rejected']).count(),
        'in_progress': all_jobs.filter(operator_status__in=['traveling', 'operating']).count(),
        'completed': all_jobs.filter(status='completed').count(),
    }

    recent_jobs = all_jobs.exclude(
        status__in=['completed', 'cancelled', 'rejected']
    ).order_by('-created_at')[:5]

    context = {
        'stats': stats,
        'recent_jobs': recent_jobs,
        'viewing_as_admin': viewing_as_admin,
        'operator_user': operator_user,
    }
    return render(request, 'machines/operator/index.html', context)


@login_required
def operator_all_jobs(request):
    """All assigned jobs with filtering - professional view"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access operator jobs.")
        return redirect('dashboard')

    # Get filter parameter
    filter_type = request.GET.get('filter', 'all')

    # Base queryset
    base_jobs = Rental.objects.select_related('machine', 'user').filter(
        assigned_operator=request.user
    )

    # Apply filters
    if filter_type == 'active':
        jobs = base_jobs.exclude(
            status__in=['completed', 'cancelled', 'rejected']
        ).order_by('start_date', '-created_at')
    elif filter_type == 'harvest':
        jobs = base_jobs.filter(
            payment_type='in_kind',
            operator_status__in=['operating', 'harvest_ready']
        ).exclude(
            status__in=['completed', 'cancelled', 'rejected']
        ).exclude(
            operator_status='harvest_reported'
        ).order_by('start_date', '-created_at')
    elif filter_type == 'completed':
        jobs = base_jobs.filter(
            status='completed'
        ).order_by('-updated_at')
    else:  # 'all'
        jobs = base_jobs.order_by('-created_at')

    # Calculate statistics
    active_count = base_jobs.exclude(
        status__in=['completed', 'cancelled', 'rejected']
    ).count()
    
    completed_count = base_jobs.filter(status='completed').count()
    
    harvest_pending_count = base_jobs.filter(
        payment_type='in_kind',
        operator_status__in=['operating', 'harvest_ready']
    ).exclude(
        status__in=['completed', 'cancelled', 'rejected']
    ).exclude(
        operator_status='harvest_reported'
    ).count()

    context = {
        'jobs': jobs,
        'filter': filter_type,
        'active_count': active_count,
        'completed_count': completed_count,
        'harvest_pending_count': harvest_pending_count,
    }
    return render(request, 'machines/operator/jobs.html', context)


@login_required
def operator_job_detail(request, rental_id):
    """View single job with actions"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access operator jobs.")
        return redirect('dashboard')

    rental = get_object_or_404(
        Rental.objects.select_related('machine', 'user'),
        pk=rental_id,
        assigned_operator=request.user,
    )

    context = {
        'rental': rental,
    }
    return render(request, 'machines/operator/job_detail.html', context)


@login_required
def operator_ongoing_jobs(request):
    """Ongoing jobs - work interface with statistics"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access operator jobs.")
        return redirect('dashboard')

    jobs = Rental.objects.select_related('machine', 'user').filter(
        assigned_operator=request.user,
        operator_status__in=['assigned', 'traveling', 'operating']
    ).order_by('start_date', '-created_at')

    # Calculate statistics
    assigned_count = jobs.filter(operator_status='assigned').count()
    traveling_count = jobs.filter(operator_status='traveling').count()
    operating_count = jobs.filter(operator_status='operating').count()

    context = {
        'jobs': jobs,
        'assigned_count': assigned_count,
        'traveling_count': traveling_count,
        'operating_count': operating_count,
    }
    return render(request, 'machines/operator/work.html', context)


@login_required
def operator_awaiting_harvest(request):
    """Only harvester jobs awaiting harvest completion with statistics"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access operator jobs.")
        return redirect('dashboard')

    jobs = Rental.objects.select_related('machine', 'user').filter(
        assigned_operator=request.user,
        payment_type='in_kind',
        operator_status__in=['operating', 'harvest_ready', 'harvest_reported']
    ).exclude(
        status__in=['completed', 'cancelled', 'rejected']
    ).order_by('start_date', '-created_at')

    # Calculate statistics
    pending_count = jobs.exclude(operator_status='harvest_reported').count()
    reported_count = jobs.filter(operator_status='harvest_reported').count()

    context = {
        'jobs': jobs,
        'pending_count': pending_count,
        'reported_count': reported_count,
    }
    return render(request, 'machines/operator/harvest.html', context)


@login_required
def operator_completed_jobs(request):
    """History of finished work with statistics"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access operator jobs.")
        return redirect('dashboard')

    jobs = Rental.objects.select_related('machine', 'user').filter(
        assigned_operator=request.user,
        status='completed'
    ).order_by('-updated_at')

    # Calculate statistics
    cash_count = jobs.exclude(payment_type='in_kind').count()
    inkind_count = jobs.filter(payment_type='in_kind').count()
    
    # Calculate total harvest for in-kind jobs
    total_harvest = sum(
        job.total_harvest_sacks or 0 
        for job in jobs.filter(payment_type='in_kind')
    )

    context = {
        'jobs': jobs,
        'page_title': 'Completed Jobs',
        'show_results': True,
        'cash_count': cash_count,
        'inkind_count': inkind_count,
        'total_harvest': total_harvest,
    }
    return render(request, 'machines/operator/operator_job_list.html', context)


@login_required
def operator_in_kind_payments(request):
    """Separate page for harvest payments tracking"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access payment information.")
        return redirect('dashboard')

    payments = Rental.objects.select_related('machine', 'user').filter(
        assigned_operator=request.user,
        payment_type='in_kind',
        harvest_total__isnull=False
    ).order_by('-operator_reported_at')

    context = {
        'payments': payments,
        'page_title': 'In-Kind Payments',
    }
    return render(request, 'machines/operator/operator_in_kind_payments.html', context)


@login_required
def operator_view_machines(request):
    """Simple machine list for operators - read only"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to view machines.")
        return redirect('dashboard')

    machines = Machine.objects.filter(status='active').order_by('name')

    context = {
        'machines': machines,
    }
    return render(request, 'machines/operator/machines.html', context)


@login_required
@transaction.atomic
def assign_operator(request, rental_id):
    """Assign operator to rental - admin only"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to assign operators.")
        return redirect('dashboard')

    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id
    )

    if request.method != 'POST':
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    operator_id = request.POST.get('assigned_operator')
    operator = None
    if operator_id:
        operator = User.objects.filter(
            pk=operator_id, 
            is_active=True, 
            role=User.OPERATOR
        ).first()

    payment_ready_for_assignment = (
        rental.payment_type == 'in_kind'
        or rental.payment_verified
        or rental.payment_status == 'paid'
    )
    if operator and not payment_ready_for_assignment:
        messages.error(
            request,
            'Cannot assign operator yet. Payment must be confirmed first for cash or online rentals.'
        )
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    if operator and rental.status not in ['approved', 'assigned']:
        messages.error(
            request,
            f'Cannot assign operator while rental status is "{rental.status}".'
        )
        return redirect('machines:admin_approve_rental', rental_id=rental.id)

    rental.assigned_operator = operator
    if operator:
        # When assigning an operator, change status from 'approved' to 'assigned'
        if rental.status == 'approved':
            rental.status = 'assigned'
        rental.operator_status = 'assigned'
    else:
        # When removing operator assignment
        if rental.status == 'assigned':
            rental.status = 'approved'  # Revert back to approved
        rental.operator_status = 'unassigned'
    
    rental.operator_last_update_at = timezone.now() if operator else rental.operator_last_update_at
    rental.save(update_fields=[
        'assigned_operator',
        'status',
        'operator_status',
        'operator_last_update_at',
        'updated_at',
    ])

    if operator:
        # Notify the operator about the assignment
        notify_operator_job_assigned(operator, rental)
        
        messages.success(request, f'Assigned {operator.get_full_name() or operator.username} to this rental.')
    else:
        messages.info(request, 'Operator assignment cleared.')

    return redirect('machines:admin_approve_rental', rental_id=rental.id)


@login_required
@transaction.atomic
def update_operator_job(request, rental_id):
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to update operator jobs.")
        return redirect('dashboard')

    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'assigned_operator'),
        pk=rental_id,
        assigned_operator=request.user,
    )

    if request.method != 'POST':
        return redirect('machines:operator_dashboard')

    new_status = request.POST.get('operator_status', '').strip()
    notes = request.POST.get('operator_notes', '').strip()
    harvest_sacks = request.POST.get('harvest_sacks', '').strip()
    
    valid_statuses = {choice[0] for choice in Rental.OPERATOR_STATUS_CHOICES}
    if new_status not in valid_statuses:
        messages.error(request, 'Invalid operator status selected.')
        return redirect('machines:operator_dashboard')

    rental.operator_status = new_status
    if notes:
        rental.operator_notes = notes
    rental.operator_last_update_at = timezone.now()

    update_fields = ['operator_status', 'operator_notes', 'operator_last_update_at', 'updated_at']
    
    # Handle harvest_complete status (convert to harvest_ready for backend processing)
    if new_status == 'harvest_complete' and rental.payment_type == 'in_kind':
        # This status requires harvest data, so we expect harvest_sacks to be provided
        if not harvest_sacks:
            messages.error(request, 'Harvest amount is required for harvest completion.')
            return redirect('machines:operator_dashboard')
        new_status = 'harvest_ready'
    
    # Handle harvest_ready status with harvest data for in-kind payments
    if new_status == 'harvest_ready' and rental.payment_type == 'in_kind' and harvest_sacks:
        try:
            total_harvest = Decimal(harvest_sacks)
            if total_harvest > 0:
                # Calculate shares
                bufia_share, member_share = rental.calculate_harvest_shares(total_harvest)
                
                # Update rental with harvest data
                rental.total_harvest_sacks = total_harvest
                rental.total_rice_sacks_harvested = total_harvest
                rental.bufia_share = bufia_share
                rental.member_share = member_share
                rental.organization_share_required = bufia_share
                rental.payment_status = 'pending'
                rental.settlement_status = 'waiting_for_delivery'
                rental.workflow_state = 'harvest_report_submitted'
                rental.operator_status = 'harvest_reported'
                rental.operator_reported_at = timezone.now()
                
                update_fields.extend([
                    'total_harvest_sacks',
                    'total_rice_sacks_harvested',
                    'bufia_share',
                    'member_share',
                    'organization_share_required',
                    'payment_status',
                    'settlement_status',
                    'workflow_state',
                    'operator_reported_at',
                ])
                
                # Create harvest report
                HarvestReport.objects.create(
                    rental=rental,
                    total_rice_sacks_harvested=total_harvest,
                    recorded_by_admin=None,
                    verification_notes=f'Operator-submitted harvest: {total_harvest} sacks (via status update)',
                )
                
                # Notify admins about harvest submission
                _notify_admins(
                    f'🌾 Harvest reported for {rental.machine.name}: '
                    f'{total_harvest} sacks. BUFIA share: {bufia_share} sacks. '
                    f'Operator: {request.user.get_full_name() or request.user.username}',
                    rental.id,
                    exclude_user_id=request.user.id,
                )
                
                messages.success(
                    request,
                    f'Harvest reported: {total_harvest} sacks. BUFIA share: {bufia_share} sacks. '
                    f'Sent to admin for verification.'
                )
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Invalid harvest amount provided.')
            return redirect('machines:operator_dashboard')
    
    if new_status == 'operating':
        rental.workflow_state = 'in_progress'
        if rental.status != 'completed':
            rental.status = 'approved'
        if rental.actual_handover_date is None:
            rental.actual_handover_date = timezone.now()
            update_fields.append('actual_handover_date')
        update_fields.extend(['workflow_state', 'status'])
        rental.save(update_fields=list(dict.fromkeys(update_fields)))
        rental.sync_machine_status()
    else:
        rental.save(update_fields=list(dict.fromkeys(update_fields)))

    _notify_admins(
        f'Operator update for {rental.machine.name}: {rental.get_operator_status_display()}.',
        rental.id,
        exclude_user_id=request.user.id,
    )
    
    if new_status != 'harvest_reported':
        messages.success(request, 'Operator job updated.')
    
    # Redirect back to the referring page
    next_url = request.POST.get('next', 'machines:operator_dashboard')
    return redirect(next_url)


@login_required
@transaction.atomic
def submit_operator_harvest(request, rental_id):
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to submit harvest reports.")
        return redirect('dashboard')

    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user', 'assigned_operator'),
        pk=rental_id,
        assigned_operator=request.user,
        payment_type='in_kind',
    )

    if request.method != 'POST':
        return redirect('machines:operator_dashboard')

    total_harvest_raw = request.POST.get('total_harvest_sacks', '').strip()
    notes = request.POST.get('operator_notes', '').strip()
    try:
        total_harvest = Decimal(total_harvest_raw)
    except (InvalidOperation, TypeError):
        messages.error(request, 'Enter a valid harvest total in sacks.')
        return redirect('machines:operator_dashboard')

    if total_harvest <= 0:
        messages.error(request, 'Harvest total must be greater than zero.')
        return redirect('machines:operator_dashboard')

    bufia_share, member_share = rental.calculate_harvest_shares(total_harvest)
    rental.total_harvest_sacks = total_harvest
    rental.total_rice_sacks_harvested = total_harvest
    rental.bufia_share = bufia_share
    rental.member_share = member_share
    rental.organization_share_required = bufia_share
    rental.payment_status = 'pending'
    rental.settlement_status = 'waiting_for_delivery'
    rental.workflow_state = 'harvest_report_submitted'
    rental.operator_status = 'harvest_reported'
    rental.operator_reported_at = timezone.now()
    rental.operator_last_update_at = timezone.now()
    if notes:
        rental.operator_notes = notes
    rental.save(update_fields=[
        'total_harvest_sacks',
        'total_rice_sacks_harvested',
        'bufia_share',
        'member_share',
        'organization_share_required',
        'payment_status',
        'settlement_status',
        'workflow_state',
        'operator_status',
        'operator_reported_at',
        'operator_last_update_at',
        'operator_notes',
        'updated_at',
    ])

    HarvestReport.objects.create(
        rental=rental,
        total_rice_sacks_harvested=total_harvest,
        recorded_by_admin=None,
        verification_notes=f'Operator-submitted harvest report by {request.user.get_full_name() or request.user.username}.',
    )

    _notify_admins(
        (
            f'Harvest reported for {rental.machine.name}: '
            f'{total_harvest} sacks, BUFIA share {bufia_share} sacks.'
        ),
        rental.id,
        exclude_user_id=request.user.id,
    )
    messages.success(request, 'Harvest report submitted for admin review.')
    
    # Redirect back to the referring page
    next_url = request.POST.get('next', 'machines:operator_dashboard')
    return redirect(next_url)
