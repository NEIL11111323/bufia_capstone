"""
Operator decision-making views for autonomous field operations
"""
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from django.contrib.auth import get_user_model

from notifications.operator_notifications import (
    notify_operator_job_updated,
    notify_operator_urgent_job,
)
from notifications.models import UserNotification

from .models import Rental, Machine


User = get_user_model()


def _is_operator_user(user):
    """Check if user has operator role"""
    return user.is_authenticated and user.role == User.OPERATOR


def _notify_admins(message, rental_id, *, exclude_user_id=None):
    """Notify admins about operator decisions"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    admins = User.objects.filter(is_active=True, is_staff=True, is_superuser=True).exclude(role='operator')
    if exclude_user_id:
        admins = admins.exclude(pk=exclude_user_id)
    
    notifications = [
        UserNotification(
            user=admin,
            notification_type='operator_decision',
            message=message,
            related_object_id=rental_id,
        )
        for admin in admins
    ]
    if notifications:
        UserNotification.objects.bulk_create(notifications)


@login_required
@transaction.atomic
def operator_make_decision(request, rental_id):
    """Allow operator to make field decisions and update rental"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to make operator decisions.")
        return redirect('dashboard')

    rental = get_object_or_404(
        Rental.objects.select_for_update().select_related('machine', 'user'),
        pk=rental_id,
        assigned_operator=request.user,
    )

    if request.method != 'POST':
        return redirect('machines:operator_ongoing_jobs')

    decision_type = request.POST.get('decision_type')
    reason = request.POST.get('reason', '').strip()
    
    if not decision_type or not reason:
        messages.error(request, 'Decision type and reason are required.')
        return redirect('machines:operator_ongoing_jobs')

    # Process different decision types
    if decision_type == 'delay_job':
        return _handle_delay_decision(request, rental, reason)
    elif decision_type == 'cancel_job':
        return _handle_cancel_decision(request, rental, reason)
    elif decision_type == 'modify_schedule':
        return _handle_schedule_modification(request, rental, reason)
    elif decision_type == 'request_support':
        return _handle_support_request(request, rental, reason)
    elif decision_type == 'report_issue':
        return _handle_issue_report(request, rental, reason)
    else:
        messages.error(request, 'Invalid decision type.')
        return redirect('machines:operator_ongoing_jobs')


def _handle_delay_decision(request, rental, reason):
    """Handle operator decision to delay job"""
    delay_hours = request.POST.get('delay_hours', '').strip()
    
    try:
        delay_hours = int(delay_hours)
        if delay_hours < 1 or delay_hours > 72:
            messages.error(request, 'Delay must be between 1 and 72 hours.')
            return redirect('machines:operator_ongoing_jobs')
    except (ValueError, TypeError):
        messages.error(request, 'Invalid delay hours.')
        return redirect('machines:operator_ongoing_jobs')
    
    # Update rental with delay
    old_start_date = rental.start_date
    rental.start_date = rental.start_date + timezone.timedelta(hours=delay_hours)
    rental.operator_status = 'assigned'  # Reset to assigned
    rental.operator_notes = f"DELAYED: {reason}. Original start: {old_start_date.strftime('%Y-%m-%d %H:%M')}"
    rental.operator_last_update_at = timezone.now()
    rental.save(update_fields=[
        'start_date', 'operator_status', 'operator_notes', 
        'operator_last_update_at', 'updated_at'
    ])
    
    # Notify admin
    _notify_admins(
        f'Operator delayed job: {rental.machine.name} by {delay_hours} hours. '
        f'Reason: {reason}. Member: {rental.customer_display_name}.',
        rental.id,
        exclude_user_id=request.user.id
    )
    
    messages.success(request, f'Job delayed by {delay_hours} hours. Admin has been notified.')
    return redirect('machines:operator_ongoing_jobs')


def _handle_cancel_decision(request, rental, reason):
    """Handle operator decision to cancel job"""
    # Only allow cancellation in certain conditions
    if rental.operator_status in ['operating', 'completed', 'harvest_reported']:
        messages.error(request, 'Cannot cancel job that is already in progress or completed.')
        return redirect('machines:operator_ongoing_jobs')
    
    # Update rental status
    rental.status = 'cancelled'
    rental.workflow_state = 'cancelled'
    rental.operator_status = 'unassigned'
    rental.operator_notes = f"CANCELLED BY OPERATOR: {reason}"
    rental.operator_last_update_at = timezone.now()
    rental.assigned_operator = None
    rental.save(update_fields=[
        'status', 'workflow_state', 'operator_status', 'operator_notes',
        'operator_last_update_at', 'assigned_operator', 'updated_at'
    ])
    
    # Free up machine
    rental.sync_machine_status()
    
    # Notify admin and user
    _notify_admins(
        f'Operator cancelled job: {rental.machine.name}. '
        f'Reason: {reason}. Member: {rental.customer_display_name}.',
        rental.id,
        exclude_user_id=request.user.id
    )
    
    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_cancelled',
        message=f'Your rental for {rental.machine.name} has been cancelled by the operator. '
                f'Reason: {reason}. Please contact admin for rescheduling.',
        related_object_id=rental.id
    )
    
    messages.success(request, 'Job cancelled. Admin and member have been notified.')
    return redirect('machines:operator_ongoing_jobs')


def _handle_schedule_modification(request, rental, reason):
    """Handle operator request for schedule modification"""
    new_date = request.POST.get('new_date', '').strip()
    new_time = request.POST.get('new_time', '').strip()
    
    if not new_date:
        messages.error(request, 'New date is required for schedule modification.')
        return redirect('machines:operator_ongoing_jobs')
    
    try:
        from datetime import datetime
        if new_time:
            new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
        else:
            new_datetime = datetime.strptime(new_date, "%Y-%m-%d")
        
        new_datetime = timezone.make_aware(new_datetime)
    except ValueError:
        messages.error(request, 'Invalid date/time format.')
        return redirect('machines:operator_ongoing_jobs')
    
    # Check if new time is reasonable (not too far in past/future)
    now = timezone.now()
    if new_datetime < now - timezone.timedelta(hours=1):
        messages.error(request, 'Cannot schedule in the past.')
        return redirect('machines:operator_ongoing_jobs')
    
    if new_datetime > now + timezone.timedelta(days=30):
        messages.error(request, 'Cannot schedule more than 30 days in advance.')
        return redirect('machines:operator_ongoing_jobs')
    
    # Update rental
    old_start_date = rental.start_date
    rental.start_date = new_datetime
    rental.operator_notes = f"SCHEDULE MODIFIED: {reason}. " \
                           f"Original: {old_start_date.strftime('%Y-%m-%d %H:%M')}, " \
                           f"New: {new_datetime.strftime('%Y-%m-%d %H:%M')}"
    rental.operator_last_update_at = timezone.now()
    rental.save(update_fields=[
        'start_date', 'operator_notes', 'operator_last_update_at', 'updated_at'
    ])
    
    # Notify admin and user
    _notify_admins(
        f'Operator modified schedule: {rental.machine.name}. '
        f'New date: {new_datetime.strftime("%Y-%m-%d %H:%M")}. '
        f'Reason: {reason}. Member: {rental.customer_display_name}.',
        rental.id,
        exclude_user_id=request.user.id
    )
    
    UserNotification.objects.create(
        user=rental.user,
        notification_type='rental_schedule_changed',
        message=f'Your rental schedule for {rental.machine.name} has been modified. '
                f'New date: {new_datetime.strftime("%b %d, %Y at %H:%M")}. '
                f'Reason: {reason}.',
        related_object_id=rental.id
    )
    
    messages.success(request, 'Schedule modified. Admin and member have been notified.')
    return redirect('machines:operator_ongoing_jobs')


def _handle_support_request(request, rental, reason):
    """Handle operator request for support"""
    support_type = request.POST.get('support_type', 'general')
    urgency = request.POST.get('urgency', 'normal')
    
    # Update rental notes
    rental.operator_notes = f"SUPPORT REQUESTED ({support_type.upper()}): {reason}"
    rental.operator_last_update_at = timezone.now()
    rental.save(update_fields=['operator_notes', 'operator_last_update_at', 'updated_at'])
    
    # Create urgent notification if needed
    if urgency == 'urgent':
        notify_operator_urgent_job(
            request.user, 
            rental, 
            f"Support requested: {reason}"
        )
    
    # Notify admin
    urgency_text = "🚨 URGENT" if urgency == 'urgent' else "📞"
    _notify_admins(
        f'{urgency_text} Support requested: {rental.machine.name}. '
        f'Type: {support_type}. Reason: {reason}. '
        f'Operator: {request.user.get_full_name()}. '
        f'Member: {rental.customer_display_name}.',
        rental.id,
        exclude_user_id=request.user.id
    )
    
    urgency_msg = "urgent " if urgency == 'urgent' else ""
    messages.success(request, f'Support request sent. Admin will respond to your {urgency_msg}request.')
    return redirect('machines:operator_ongoing_jobs')


def _handle_issue_report(request, rental, reason):
    """Handle operator issue report"""
    issue_type = request.POST.get('issue_type', 'other')
    severity = request.POST.get('severity', 'medium')
    
    # Update rental based on issue severity
    if severity == 'critical':
        # Critical issues may require stopping work
        rental.operator_status = 'assigned'  # Stop operating
        rental.operator_notes = f"🚨 CRITICAL ISSUE ({issue_type.upper()}): {reason}. Work stopped."
        
        # Notify as urgent
        notify_operator_urgent_job(
            request.user,
            rental,
            f"Critical issue reported: {reason}"
        )
        
        messages.warning(request, 'Critical issue reported. Work status reset to assigned.')
    else:
        rental.operator_notes = f"ISSUE REPORTED ({issue_type.upper()}, {severity.upper()}): {reason}"
        messages.success(request, 'Issue reported. You can continue working.')
    
    rental.operator_last_update_at = timezone.now()
    rental.save(update_fields=['operator_status', 'operator_notes', 'operator_last_update_at', 'updated_at'])
    
    # Notify admin
    severity_icon = "🚨" if severity == 'critical' else "⚠️" if severity == 'high' else "ℹ️"
    _notify_admins(
        f'{severity_icon} Issue reported: {rental.machine.name}. '
        f'Type: {issue_type}, Severity: {severity}. '
        f'Details: {reason}. '
        f'Operator: {request.user.get_full_name()}.',
        rental.id,
        exclude_user_id=request.user.id
    )
    
    return redirect('machines:operator_ongoing_jobs')


@login_required
def operator_decision_form(request, rental_id):
    """Show decision form for operator"""
    if not _is_operator_user(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')

    rental = get_object_or_404(
        Rental.objects.select_related('machine', 'user'),
        pk=rental_id,
        assigned_operator=request.user,
    )

    context = {
        'rental': rental,
        'can_cancel': rental.operator_status in ['assigned', 'traveling'],
        'can_delay': rental.operator_status in ['assigned', 'traveling'],
        'can_modify_schedule': rental.operator_status in ['assigned'],
    }

    return render(request, 'machines/operator/operator_decision_form.html', context)
