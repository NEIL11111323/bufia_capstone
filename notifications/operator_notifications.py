"""
Individual operator notification system
Ensures each operator gets personalized notifications for their job activities
"""
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import UserNotification

User = get_user_model()


def notify_operator_job_assigned(operator, rental):
    """Notify operator when a new job is assigned to them"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_job_assigned',
        message=f'New job assigned: {rental.machine.name} for {rental.user.get_full_name()}. '
                f'Date: {rental.start_date.strftime("%b %d, %Y")}. '
                f'Location: {rental.field_location or "Not specified"}.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/jobs/ongoing/'
    )


def notify_operator_job_updated(operator, rental, old_status, new_status):
    """Notify operator when job status is updated by admin"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_job_updated',
        message=f'Job status updated: {rental.machine.name} changed from '
                f'{old_status} to {new_status}. '
                f'Member: {rental.user.get_full_name()}.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/jobs/ongoing/'
    )


def notify_operator_harvest_approved(operator, rental):
    """Notify operator when their harvest report is approved"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_harvest_approved',
        message=f'Harvest report approved: {rental.machine.name} - '
                f'{rental.harvest_total} sacks. '
                f'BUFIA share: {rental.bufia_share} sacks.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/payments/in-kind/'
    )


def notify_operator_harvest_rejected(operator, rental, reason):
    """Notify operator when their harvest report is rejected"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_harvest_rejected',
        message=f'Harvest report needs revision: {rental.machine.name}. '
                f'Reason: {reason}. Please resubmit with correct information.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/jobs/awaiting-harvest/'
    )


def notify_operator_job_completed(operator, rental):
    """Notify operator when job is marked as completed"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_job_completed',
        message=f'Job completed: {rental.machine.name} for {rental.user.get_full_name()}. '
                f'Great work! Check your completed jobs for details.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/jobs/completed/'
    )


def notify_operator_machine_maintenance(operator, machine, maintenance_type):
    """Notify operator about machine maintenance"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_machine_maintenance',
        message=f'Machine maintenance: {machine.name} is scheduled for {maintenance_type}. '
                f'This may affect your upcoming jobs.',
        related_object_id=machine.id,
        action_url=f'/machines/operator/machines/'
    )


def notify_operator_urgent_job(operator, rental, urgency_reason):
    """Notify operator about urgent job requirements"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_urgent_job',
        message=f'URGENT: {rental.machine.name} job requires immediate attention. '
                f'Reason: {urgency_reason}. '
                f'Member: {rental.user.get_full_name()}.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/jobs/ongoing/'
    )


def notify_operator_schedule_change(operator, rental, change_details):
    """Notify operator about schedule changes"""
    if not operator or not operator.is_staff:
        return
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_schedule_change',
        message=f'Schedule change: {rental.machine.name} - {change_details}. '
                f'Member: {rental.user.get_full_name()}. '
                f'Please check updated details.',
        related_object_id=rental.id,
        action_url=f'/machines/operator/jobs/ongoing/'
    )


def notify_operator_payment_processed(operator, rental):
    """Notify operator when payment is processed for their job"""
    if not operator or not operator.is_staff:
        return
    
    if rental.payment_type == 'in_kind':
        message = f'In-kind payment processed: {rental.machine.name} - ' \
                 f'{rental.harvest_total} sacks delivered to BUFIA.'
        action_url = f'/machines/operator/payments/in-kind/'
    else:
        message = f'Cash payment processed: {rental.machine.name} - ' \
                 f'₱{rental.total_cost} received from {rental.user.get_full_name()}.'
        action_url = f'/machines/operator/jobs/completed/'
    
    UserNotification.objects.create(
        user=operator,
        notification_type='operator_payment_processed',
        message=message,
        related_object_id=rental.id,
        action_url=action_url
    )


def notify_operator_daily_summary(operator):
    """Send daily summary to operator about their jobs"""
    if not operator or not operator.is_staff:
        return
    
    from machines.models import Rental
    
    # Get today's jobs
    today = timezone.now().date()
    today_jobs = Rental.objects.filter(
        assigned_operator=operator,
        start_date=today
    ).exclude(status__in=['completed', 'cancelled', 'rejected'])
    
    if today_jobs.exists():
        job_list = ', '.join([f'{job.machine.name}' for job in today_jobs])
        UserNotification.objects.create(
            user=operator,
            notification_type='operator_daily_summary',
            message=f'Daily Summary: You have {today_jobs.count()} job(s) scheduled for today: {job_list}. '
                    f'Check your ongoing jobs for details.',
            action_url=f'/machines/operator/jobs/ongoing/'
        )


def notify_operator_weekly_summary(operator):
    """Send weekly summary to operator"""
    if not operator or not operator.is_staff:
        return
    
    from machines.models import Rental
    from datetime import timedelta
    
    # Get this week's stats
    week_start = timezone.now().date() - timedelta(days=7)
    week_jobs = Rental.objects.filter(
        assigned_operator=operator,
        created_at__date__gte=week_start
    )
    
    completed_count = week_jobs.filter(status='completed').count()
    total_count = week_jobs.count()
    
    if total_count > 0:
        UserNotification.objects.create(
            user=operator,
            notification_type='operator_weekly_summary',
            message=f'Weekly Summary: You completed {completed_count} out of {total_count} jobs this week. '
                    f'Great work! Check your dashboard for details.',
            action_url=f'/machines/operator/dashboard/'
        )


def notify_all_operators_announcement(message, announcement_type='general'):
    """Send announcement to all active operators"""
    operators = User.objects.filter(is_staff=True, is_active=True)
    
    notifications = []
    for operator in operators:
        notifications.append(
            UserNotification(
                user=operator,
                notification_type=f'operator_announcement_{announcement_type}',
                message=f'Announcement: {message}',
                action_url=f'/machines/operator/dashboard/'
            )
        )
    
    if notifications:
        UserNotification.objects.bulk_create(notifications)


def get_operator_notification_count(operator):
    """Get unread notification count for operator"""
    if not operator or not operator.is_staff:
        return 0
    
    return UserNotification.objects.filter(
        user=operator,
        is_read=False
    ).count()


def mark_operator_notifications_read(operator, notification_ids=None):
    """Mark operator notifications as read"""
    if not operator or not operator.is_staff:
        return
    
    notifications = UserNotification.objects.filter(user=operator, is_read=False)
    
    if notification_ids:
        notifications = notifications.filter(id__in=notification_ids)
    
    notifications.update(is_read=True)


def get_operator_recent_notifications(operator, limit=10):
    """Get recent notifications for operator"""
    if not operator or not operator.is_staff:
        return UserNotification.objects.none()
    
    return UserNotification.objects.filter(
        user=operator
    ).order_by('-timestamp')[:limit]